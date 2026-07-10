import asyncio
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.features.candidates.models import Candidate, CandidateDocument, CandidateSkill
from app.features.evaluations.codeforces_client import fetch_codeforces_metrics
from app.features.evaluations.github_client import fetch_github_user_metrics
from app.features.evaluations.kaggle_client import fetch_kaggle_metrics
from app.features.evaluations.leetcode_client import fetch_leetcode_metrics
from app.features.evaluations.scholar_client import fetch_scholar_metrics
from app.features.imports.drive_downloader import parse_pdf_bytes
from app.features.imports.profile_parser import extract_profiles, parse_username
from app.features.matching.embeddings import (
    build_candidate_profile_text,
    build_project_profile_text,
    embedding_similarity,
    precompute_embeddings,
)
from app.features.matching.exceptions import MatchingUnavailableError
from app.features.matching.match_explanation import (
    generate_candidate_match_for_mentor,
    generate_project_match_for_student,
)
from app.features.matching.models import BatchPairScore, MatchRecommendationCache
from app.features.matching.report import (
    _analysis_skeleton,
    build_batch_report_html,
    build_deterministic_why,
    build_report_html,
    generate_improvement_analysis,
    render_html_to_pdf,
)
from app.features.matching.schemas import (
    BatchProjectSummary,
    BatchScoreMatrixResponse,
    BatchStudentSummary,
    PairScore,
    ProjectMatchRecommendation,
    ProjectRecommendationsResponse,
    RepositoryEvaluationSummary,
    ScoreBreakdown,
    ScoreComponents,
    StudentMatchRecommendation,
    StudentRecommendationsResponse,
)
from app.features.matching.scoring import (
    DeveloperProfileScoreResult,
    LlmScoreComponents,
    PreferenceSignalResult,
    PrerequisiteOverlapResult,
    ResumeExperienceResult,
    compute_developer_profile_score,
    compute_hybrid_final_score,
    compute_preference_signal,
    compute_preliminary_score,
    compute_prerequisite_overlap,
    compute_resume_experience,
)
from app.features.projects.models import (
    Project,
    ProjectPreference,
    ProjectPrerequisite,
)
from app.features.shared.models import Skill

logger = structlog.get_logger()

# Max candidates whose developer-metric backfill runs concurrently. Bounds the
# burst of external API calls (github/leetcode/codeforces/kaggle/scholar) on a
# cold batch so we speed up the sequential loop without tripping rate limits.
_METRICS_BACKFILL_CONCURRENCY = 8

# Single-flight guard for batch score computation. A cold compute takes minutes
# (CPU embeddings), and a user reloading the page mid-run used to start a
# second full compute that raced the first — thrashing the CPU and
# double-writing cache rows. Requests for the same batch now wait for the
# in-flight run and then serve its freshly cached result.
_batch_score_locks: dict[int, asyncio.Lock] = {}


def _get_batch_score_lock(batch_id: int) -> asyncio.Lock:
    lock = _batch_score_locks.get(batch_id)
    if lock is None:
        lock = _batch_score_locks.setdefault(batch_id, asyncio.Lock())
    return lock


async def _safe_fetch_profile_metrics(fetcher, identifier: str | None) -> dict | None:
    if not identifier:
        return None
    normalized = identifier.strip().strip("`").strip()
    if not normalized:
        return None
    try:
        return await fetcher(normalized)
    except Exception as exc:
        logger.warning(
            "matching.profile_fetch_failed",
            fetcher=getattr(fetcher, "__name__", "unknown"),
            identifier=normalized,
            error=str(exc),
        )
        return {"fetch_error": str(type(exc).__name__)}


def _normalize_name(value: str | None) -> str:
    """Casefold and collapse whitespace so mentor-typed names compare equal
    regardless of spacing/case (e.g. '  Arnab   Chakraborti ' → 'arnab chakraborti')."""
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def _resolve_selected_names(
    tokens: list[str], name_to_reg: dict[str, str]
) -> list[tuple[str | None, str]]:
    """Resolve mentor-entered 'Selected students' name tokens to registration
    numbers using a name→reg map built from the batch's candidates.

    Mentors fill this column with names, not registration numbers, and the
    import splits it on commas — so a name containing a stray comma
    (e.g. 'Arnab,Chakraborti') arrives as two tokens. When a single token does
    not resolve, this re-joins it with the following token and retries before
    giving up. Returns (registration_number | None, display_text) pairs in the
    original order; an unresolved token yields (None, token) so it can still be
    shown as an un-matched selection.
    """
    resolved: list[tuple[str | None, str]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        reg = name_to_reg.get(_normalize_name(token))
        if reg is None and i + 1 < len(tokens):
            joined = f"{token} {tokens[i + 1]}"
            joined_reg = name_to_reg.get(_normalize_name(joined))
            if joined_reg is not None:
                resolved.append((joined_reg, joined))
                i += 2
                continue
        resolved.append((reg, token))
        i += 1
    return resolved


@dataclass
class _PairSignals:
    embedding_sim: float
    embedding_detail: str
    prereq_overlap: PrerequisiteOverlapResult
    resume_experience: ResumeExperienceResult
    preference_signal: PreferenceSignalResult
    preliminary_score: float


class MatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _ensure_llm_ready(self) -> None:
        if not settings.LLM_ENABLED:
            raise MatchingUnavailableError(
                "LLM_ENABLED is false. Enable LLM_ENABLED=true in .env for matching."
            )
        if not settings.llm_is_configured():
            raise MatchingUnavailableError(
                f"LLM provider '{settings.LLM_PROVIDER}' is not configured."
            )

    async def _load_cached_recommendation(
        self, batch_id: int | None, cache_type: str, entity_key: str
    ) -> dict | None:
        """Return a cached recommendation payload, or None on miss.

        A hit is only honored when the stored scoring version matches the current
        one, so a scoring change transparently forces a recompute.
        """
        if batch_id is None:
            return None
        stmt = select(MatchRecommendationCache).where(
            MatchRecommendationCache.batch_id == batch_id,
            MatchRecommendationCache.cache_type == cache_type,
            MatchRecommendationCache.entity_key == entity_key,
        )
        row = (await self.db.execute(stmt)).scalars().first()
        if row is None or row.scoring_version != settings.SCORING_VERSION:
            return None
        return dict(row.payload)

    async def _store_cached_recommendation(
        self, batch_id: int | None, cache_type: str, entity_key: str, payload: dict
    ) -> None:
        """Upsert a recommendation payload for (batch, type, entity).

        Uses an atomic INSERT ... ON CONFLICT DO UPDATE keyed on the
        uq_match_rec_cache unique constraint. A read-then-insert would race
        when two matches for the same entity run concurrently (both read a
        miss, both insert) — the loser hit a duplicate-key IntegrityError that
        crashed the whole request after minutes of work.
        """
        if batch_id is None:
            return
        stmt = pg_insert(MatchRecommendationCache).values(
            batch_id=batch_id,
            cache_type=cache_type,
            entity_key=entity_key,
            scoring_version=settings.SCORING_VERSION,
            payload=payload,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_match_rec_cache",
            set_={
                "scoring_version": settings.SCORING_VERSION,
                "payload": payload,
                "computed_at": func.now(),
            },
        )
        await self.db.execute(stmt)
        await self.db.commit()

    def _build_preference_pairs(self, project) -> list[tuple[str, str]]:
        return [(p.preference_type, p.preference_value) for p in project.preferences]

    def _extract_skills_from_resume(
        self, text: str, known_skills: list[str]
    ) -> list[str]:
        if not text:
            return []
        found = []
        for kw in known_skills:
            pattern = rf"(?i)(?:^|[^\w]){re.escape(kw)}(?:[^\w]|$)"
            if re.search(pattern, text):
                found.append(kw)
        return found

    def _merge_skills(
        self, workbook_skills: list[str], resume_skills: list[str]
    ) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for skill in workbook_skills + resume_skills:
            key = skill.lower()
            if key not in seen:
                seen.add(key)
                merged.append(skill)
        return merged

    async def _compute_pair_signals(
        self,
        *,
        candidate_name: str,
        candidate_skills: list[str],
        resume_text: str,
        registration_number: str,
        project,
        developer_profile: DeveloperProfileScoreResult | None = None,
        embedding_override: tuple[float, str] | None = None,
    ) -> _PairSignals:
        prereqs = [p.skill.name for p in project.prerequisites if p.skill]
        project_abstract = cast(str, project.abstract or "")

        if embedding_override is not None:
            # Reuse an already-computed similarity (e.g. from the persisted
            # batch score matrix) instead of re-encoding — a ~10s CPU encode
            # per fresh text — and stay consistent with what the dashboard
            # shows for this pair.
            emb_sim, emb_detail = embedding_override
        else:
            cand_profile = build_candidate_profile_text(
                candidate_name, candidate_skills, resume_text
            )
            proj_profile = build_project_profile_text(
                cast(str, project.title), project_abstract, prereqs
            )
            emb_sim, emb_detail = await embedding_similarity(cand_profile, proj_profile)

        prereq_overlap = compute_prerequisite_overlap(candidate_skills, prereqs)
        resume_experience = compute_resume_experience(
            resume_text, project_abstract, prereqs
        )
        preference_signal = compute_preference_signal(
            registration_number,
            self._build_preference_pairs(project),
        )
        preliminary = compute_preliminary_score(
            embedding_similarity=emb_sim,
            prerequisite_overlap=prereq_overlap,
            resume_experience=resume_experience,
            developer_profile=developer_profile,
        )

        return _PairSignals(
            embedding_sim=emb_sim,
            embedding_detail=emb_detail,
            prereq_overlap=prereq_overlap,
            resume_experience=resume_experience,
            preference_signal=preference_signal,
            preliminary_score=preliminary,
        )

    def _preliminary_context(self, signals: _PairSignals) -> str:
        return (
            f"embedding_similarity={signals.embedding_sim:.4f}; "
            f"prerequisite_overlap={signals.prereq_overlap.score:.4f}; "
            f"resume_experience={signals.resume_experience.score:.4f}; "
            f"preliminary_score={signals.preliminary_score:.4f}"
        )

    def _build_project_recommendation(
        self,
        *,
        rank: int,
        project,
        signals: _PairSignals,
        eval_res: dict | None,
        developer_profile: DeveloperProfileScoreResult | None = None,
        achievements: list[str] | None = None,
    ) -> ProjectMatchRecommendation:
        llm_scores = None
        if eval_res and not eval_res.get("llm_error"):
            llm_scores = LlmScoreComponents(
                readiness=eval_res["readiness"],
                growth_potential=eval_res["growth_potential_score"],
                interest=eval_res["interest"],
                semantic_fit=eval_res["semantic_fit"],
            )

        hybrid = compute_hybrid_final_score(
            embedding_similarity=signals.embedding_sim,
            embedding_detail=signals.embedding_detail,
            prerequisite_overlap=signals.prereq_overlap,
            resume_experience=signals.resume_experience,
            developer_profile=developer_profile,
            preference_signal=signals.preference_signal,
            llm_scores=llm_scores,
        )

        if eval_res:
            explanation = eval_res["explanation"]
            technical_readiness = eval_res["technical_readiness"]
            growth_potential = eval_res["growth_potential"]
            interest_alignment = eval_res["interest_alignment"]
            rationale = eval_res["scoring_rationale"]
            llm_provider = eval_res.get("llm_provider")
            llm_model = eval_res.get("llm_model")
        else:
            explanation = (
                "Preliminary ranking from embedding similarity, "
                "tiered prerequisite overlap, and resume experience. "
                "Full LLM evaluation was not run "
                "(outside top-K finalists)."
            )
            technical_readiness = "Not LLM-evaluated (preliminary rank only)."
            growth_potential = "Not LLM-evaluated (preliminary rank only)."
            interest_alignment = "Not LLM-evaluated (preliminary rank only)."
            rationale = "N/A — preliminary signals only."
            llm_provider = None
            llm_model = None

        return ProjectMatchRecommendation(
            rank=rank,
            project_id=cast(int, project.id),
            project_title=cast(str, project.title),
            achievements=list(achievements or []),
            mentor_name=project.mentor.name if project.mentor else "Unknown",
            mentor_email=project.mentor.email if project.mentor else None,
            mentor_phone=project.mentor.phone if project.mentor else None,
            final_score=hybrid.final_score,
            score_components=ScoreComponents(
                embedding_similarity=hybrid.embedding_similarity,
                readiness=hybrid.readiness,
                growth_potential=hybrid.growth_potential,
                interest=hybrid.interest,
                github_score=hybrid.github_score,
                coding_profiles_score=hybrid.coding_profiles_score,
                achievements_score=hybrid.achievements_score,
                repository_quality_score=hybrid.repository_quality_score,
                live_app_score=hybrid.live_app_score,
                llm_fit_score=hybrid.llm_fit_score,
                prerequisite_overlap=hybrid.prerequisite_overlap,
                resume_experience=hybrid.resume_experience,
                preference_signal=hybrid.preference_signal,
                preliminary_score=signals.preliminary_score,
                llm_evaluated=hybrid.llm_evaluated,
            ),
            score_breakdown=ScoreBreakdown(
                scoring_version=hybrid.scoring_version,
                formula=hybrid.formula,
                weights=hybrid.weights,
                weighted_contributions=hybrid.weighted_contributions,
                prerequisite_detail=hybrid.prerequisite_detail,
                resume_experience_detail=hybrid.resume_experience_detail,
                developer_profile_detail=hybrid.developer_profile_detail,
                github_detail=hybrid.github_detail,
                coding_profiles_detail=hybrid.coding_profiles_detail,
                achievements_detail=hybrid.achievements_detail,
                repository_evaluations=(
                    [
                        RepositoryEvaluationSummary(**entry)
                        for entry in developer_profile.repository_evaluations
                    ]
                    if developer_profile
                    else []
                ),
                preference_detail=hybrid.preference_detail,
                embedding_detail=hybrid.embedding_detail,
                llm_scoring_rationale=rationale,
                llm_provider=llm_provider,
                llm_model=llm_model,
            ),
            explanation=explanation,
            technical_readiness=technical_readiness,
            growth_potential=growth_potential,
            interest_alignment=interest_alignment,
        )

    def _build_student_recommendation(
        self,
        *,
        rank: int,
        candidate,
        _project,
        signals: _PairSignals,
        eval_res: dict | None,
    ) -> StudentMatchRecommendation:
        llm_scores = None
        if eval_res and not eval_res.get("llm_error"):
            llm_scores = LlmScoreComponents(
                readiness=eval_res["readiness"],
                growth_potential=eval_res["growth_potential_score"],
                interest=eval_res["interest"],
                semantic_fit=eval_res["semantic_fit"],
            )

        developer_profile = compute_developer_profile_score(
            github_username=candidate.github_username,
            github_metrics=candidate.github_metrics,
            github_repositories=candidate.github_repositories,
            leetcode_metrics=candidate.leetcode_metrics,
            codeforces_metrics=candidate.codeforces_metrics,
            kaggle_metrics=candidate.kaggle_metrics,
            scholar_metrics=candidate.scholar_metrics,
            achievements=candidate.achievements,
            repository_evaluations=candidate.repository_evaluations,
            live_app_evaluations=candidate.live_app_evaluations,
        )

        hybrid = compute_hybrid_final_score(
            embedding_similarity=signals.embedding_sim,
            embedding_detail=signals.embedding_detail,
            prerequisite_overlap=signals.prereq_overlap,
            resume_experience=signals.resume_experience,
            developer_profile=developer_profile,
            preference_signal=signals.preference_signal,
            llm_scores=llm_scores,
        )

        if eval_res:
            explanation = eval_res["explanation"]
            technical_readiness = eval_res["technical_readiness"]
            growth_potential = eval_res["growth_potential"]
            interest_alignment = eval_res["interest_alignment"]
            rationale = eval_res["scoring_rationale"]
            llm_provider = eval_res.get("llm_provider")
            llm_model = eval_res.get("llm_model")
        else:
            explanation = (
                "Preliminary ranking from embedding similarity, "
                "tiered prerequisite overlap, and resume experience. "
                "Full LLM evaluation was not run "
                "(outside top-K finalists)."
            )
            technical_readiness = "Not LLM-evaluated (preliminary rank only)."
            growth_potential = "Not LLM-evaluated (preliminary rank only)."
            interest_alignment = "Not LLM-evaluated (preliminary rank only)."
            rationale = "N/A — preliminary signals only."
            llm_provider = None
            llm_model = None

        return StudentMatchRecommendation(
            rank=rank,
            candidate_id=cast(int, candidate.id),
            candidate_name=cast(str, candidate.name),
            registration_number=cast(str, candidate.registration_number),
            achievements=list(candidate.achievements or []),
            final_score=hybrid.final_score,
            score_components=ScoreComponents(
                embedding_similarity=hybrid.embedding_similarity,
                readiness=hybrid.readiness,
                growth_potential=hybrid.growth_potential,
                interest=hybrid.interest,
                github_score=hybrid.github_score,
                coding_profiles_score=hybrid.coding_profiles_score,
                achievements_score=hybrid.achievements_score,
                repository_quality_score=hybrid.repository_quality_score,
                live_app_score=hybrid.live_app_score,
                llm_fit_score=hybrid.llm_fit_score,
                prerequisite_overlap=hybrid.prerequisite_overlap,
                resume_experience=hybrid.resume_experience,
                preference_signal=hybrid.preference_signal,
                preliminary_score=signals.preliminary_score,
                llm_evaluated=hybrid.llm_evaluated,
            ),
            score_breakdown=ScoreBreakdown(
                scoring_version=hybrid.scoring_version,
                formula=hybrid.formula,
                weights=hybrid.weights,
                weighted_contributions=hybrid.weighted_contributions,
                prerequisite_detail=hybrid.prerequisite_detail,
                resume_experience_detail=hybrid.resume_experience_detail,
                developer_profile_detail=hybrid.developer_profile_detail,
                github_detail=hybrid.github_detail,
                coding_profiles_detail=hybrid.coding_profiles_detail,
                achievements_detail=hybrid.achievements_detail,
                repository_evaluations=(
                    [
                        RepositoryEvaluationSummary(**entry)
                        for entry in developer_profile.repository_evaluations
                    ]
                    if developer_profile
                    else []
                ),
                preference_detail=hybrid.preference_detail,
                embedding_detail=hybrid.embedding_detail,
                llm_scoring_rationale=rationale,
                llm_provider=llm_provider,
                llm_model=llm_model,
            ),
            explanation=explanation,
            technical_readiness=technical_readiness,
            growth_potential=growth_potential,
            interest_alignment=interest_alignment,
        )

    async def _load_known_skill_names(self) -> list[str]:
        res = await self.db.execute(select(Skill))
        return [cast(str, s.name) for s in res.scalars().all()]

    async def build_match_report(
        self, *, registration_number: str, project_id: int
    ) -> tuple[str, bytes]:
        """Build a downloadable PDF fit report for one candidate-project pair.

        Reuses the full scoring path to obtain the factor breakdown, adds an LLM
        strengths/gaps/improvement analysis, and prints it to PDF.
        """
        self._ensure_llm_ready()

        cand_stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
                selectinload(Candidate.repository_evaluations),
                selectinload(Candidate.live_app_evaluations),
            )
            .where(Candidate.registration_number == registration_number)
        )
        candidate = (await self.db.execute(cand_stmt)).scalars().first()
        if not candidate:
            raise ValueError(
                f"Candidate with registration number {registration_number} not found."
            )

        proj_stmt = (
            select(Project)
            .options(
                selectinload(Project.mentor),
                selectinload(Project.prerequisites).selectinload(
                    ProjectPrerequisite.skill
                ),
                selectinload(Project.preferences),
            )
            .where(Project.id == project_id)
        )
        project = (await self.db.execute(proj_stmt)).scalars().first()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        t_start = time.perf_counter()
        workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
        doc = next(
            (d for d in candidate.documents if d.document_type == "resume"), None
        )
        resume_text = doc.parsed_text if doc and doc.parsed_text else ""
        known_skills = await self._load_known_skill_names()
        resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
        candidate_skills = self._merge_skills(workbook_skills, resume_skills)

        if await self._ensure_candidate_metrics(candidate):
            await self.db.commit()
        t_metrics = time.perf_counter()

        developer_profile = compute_developer_profile_score(
            github_username=candidate.github_username,
            github_metrics=candidate.github_metrics,
            github_repositories=candidate.github_repositories,
            leetcode_metrics=candidate.leetcode_metrics,
            codeforces_metrics=candidate.codeforces_metrics,
            kaggle_metrics=candidate.kaggle_metrics,
            scholar_metrics=candidate.scholar_metrics,
            achievements=candidate.achievements,
            repository_evaluations=candidate.repository_evaluations,
            live_app_evaluations=candidate.live_app_evaluations,
        )

        # Reuse the persisted batch-matrix embedding similarity when this pair
        # was already scored (the normal flow: operator computes the batch
        # matrix, then downloads reports). Skips a ~10s CPU encode per report
        # and keeps the report's topic-match score identical to the dashboard.
        embedding_override: tuple[float, str] | None = None
        if candidate.import_batch_id is not None:
            cached_pair = (
                await self.db.execute(
                    select(BatchPairScore.embedding_similarity).where(
                        BatchPairScore.batch_id == candidate.import_batch_id,
                        BatchPairScore.candidate_id == candidate.id,
                        BatchPairScore.project_id == project.id,
                    )
                )
            ).scalar_one_or_none()
            if cached_pair is not None:
                embedding_override = (
                    cached_pair,
                    f"Embedding similarity = {cached_pair:.4f} "
                    "(reused from the batch score matrix).",
                )

        signals = await self._compute_pair_signals(
            candidate_name=cast(str, candidate.name),
            candidate_skills=candidate_skills,
            resume_text=resume_text,
            registration_number=registration_number,
            project=project,
            developer_profile=developer_profile,
            embedding_override=embedding_override,
        )
        t_signals = time.perf_counter()

        prereqs = [p.skill.name for p in project.prerequisites if p.skill]

        # The factor scores are fully deterministic (independent of the LLM
        # match evaluation), and the improvement analysis only needs those
        # factor scores — so build the factor summary up front and run both LLM
        # calls concurrently instead of back to back. This roughly halves the
        # report's LLM wait, which dominates its latency.
        prelim_factors = self._report_factors(
            self._build_project_recommendation(
                rank=1,
                project=project,
                signals=signals,
                eval_res=None,
                developer_profile=developer_profile,
            )
        )
        factor_summary = "\n".join(
            f"- {f['label']}: {round(f['score'] * 100)}%" for f in prelim_factors
        )

        eval_res, analysis = await asyncio.gather(
            generate_project_match_for_student(
                candidate_name=cast(str, candidate.name),
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                project_title=cast(str, project.title),
                project_abstract=cast(str, project.abstract or ""),
                prerequisites=prereqs,
                preferences=[p.preference_value for p in project.preferences],
                preliminary_context=self._preliminary_context(signals),
            ),
            generate_improvement_analysis(
                candidate_name=cast(str, candidate.name),
                resume_text=resume_text,
                project_title=cast(str, project.title),
                project_abstract=cast(str, project.abstract or ""),
                prerequisites=prereqs,
                factor_summary=factor_summary,
            ),
            return_exceptions=True,
        )

        t_llm = time.perf_counter()

        if isinstance(eval_res, BaseException):
            logger.warning("report.match_eval_failed", error=str(eval_res))
            eval_res = None
        if isinstance(analysis, BaseException):
            logger.warning("report.analysis_failed", error=str(analysis))
            analysis = _analysis_skeleton()

        rec = self._build_project_recommendation(
            rank=1,
            project=project,
            signals=signals,
            eval_res=eval_res,
            developer_profile=developer_profile,
        )

        factors = self._report_factors(rec)

        html_str = build_report_html(
            {
                "candidate_name": candidate.name,
                "project_title": project.title,
                "final_score": rec.final_score,
                "factors": factors,
                "analysis": analysis,
                "scoring_version": rec.score_breakdown.scoring_version,
            }
        )
        pdf = await render_html_to_pdf(html_str)
        # One timing line per report so slow generations are diagnosable from
        # logs: which phase ate the time (metrics fetch, embeddings, LLM, PDF).
        logger.info(
            "report.timings",
            registration_number=registration_number,
            project_id=project_id,
            metrics_s=round(t_metrics - t_start, 2),
            signals_s=round(t_signals - t_metrics, 2),
            llm_s=round(t_llm - t_signals, 2),
            render_s=round(time.perf_counter() - t_llm, 2),
            total_s=round(time.perf_counter() - t_start, 2),
        )
        filename = f"fit-report-{registration_number}-{project_id}.pdf"
        return filename, pdf

    @staticmethod
    def _report_factors(rec: ProjectMatchRecommendation) -> list[dict]:
        c, b = rec.score_components, rec.score_breakdown
        specs = [
            (
                "Topic match",
                "How closely their background aligns with the project topic",
                c.embedding_similarity,
                b.embedding_detail,
            ),
            (
                "Required skills",
                "Which of the project's must-have skills they already have",
                c.prerequisite_overlap,
                b.prerequisite_detail,
            ),
            (
                "Relevant experience",
                "Depth of related projects and experience in their resume",
                c.resume_experience,
                b.resume_experience_detail,
            ),
            (
                "GitHub profile",
                "Public code, repositories, and live apps",
                c.github_score,
                b.github_detail,
            ),
            (
                "Coding profiles",
                "Competitive-programming activity",
                c.coding_profiles_score,
                b.coding_profiles_detail,
            ),
            (
                "Achievements",
                "Awards, hackathons, and publications",
                c.achievements_score,
                b.achievements_detail,
            ),
        ]
        return [
            {
                "label": label,
                "meaning": meaning,
                "score": score or 0.0,
                "detail": detail or "",
            }
            for label, meaning, score, detail in specs
        ]

    async def build_batch_report(self, batch_id: int) -> tuple[str, bytes]:
        """Build a whole-batch PDF: each student's top-2 projects (by the
        deterministic composite score) with a factor breakdown and plain-language
        rationale, compared against the mentor-selected students recorded in the
        workbook's "Selected students" column.

        Deterministic and LLM-free so it can cover an entire batch at once and
        reuses the cached batch score matrix.
        """
        matrix = await self.compute_batch_scores(batch_id)
        if not matrix.students or not matrix.projects:
            raise ValueError(f"Batch {batch_id} has no students or projects to report.")

        # ── Mentor-recorded selections ──────────────────────────────────────────
        # Mentors fill the "Selected students" column with names, not reg numbers,
        # and the import splits it on commas. Resolve each name back to a batch
        # candidate's reg before matching (ordering by id preserves the original
        # column order so stray-comma name splits can be re-joined).
        sel_stmt = (
            select(ProjectPreference.project_id, ProjectPreference.preference_value)
            .join(Project, Project.id == ProjectPreference.project_id)
            .where(
                Project.import_batch_id == batch_id,
                ProjectPreference.preference_type == "selected_students",
            )
            .order_by(ProjectPreference.id)
        )
        sel_rows = (await self.db.execute(sel_stmt)).all()

        name_to_reg: dict[str, str] = {}
        for s in matrix.students:
            name_to_reg[_normalize_name(cast(str, s.candidate_name))] = (
                s.registration_number.strip().upper()
            )

        tokens_by_project: dict[int, list[str]] = {}
        for project_id, value in sel_rows:
            token = (value or "").strip()
            if token:
                tokens_by_project.setdefault(project_id, []).append(token)

        # reg (upper) → set of project ids the mentor selected the student for.
        selected_by_reg: dict[str, set[int]] = {}
        # project id → resolved selections as (reg | None, display name) in order.
        selected_by_project: dict[int, list[tuple[str | None, str]]] = {}
        for project_id, tokens in tokens_by_project.items():
            for reg, display in _resolve_selected_names(tokens, name_to_reg):
                selected_by_project.setdefault(project_id, []).append((reg, display))
                if reg:
                    selected_by_reg.setdefault(reg, set()).add(project_id)

        # reg (upper) → the batch student, so selections can show names + real regs
        student_by_reg = {
            s.registration_number.strip().upper(): s for s in matrix.students
        }

        # ── Group pair scores by candidate ──────────────────────────────────────
        scores_by_candidate: dict[int, list[PairScore]] = {}
        for ps in matrix.scores:
            scores_by_candidate.setdefault(ps.candidate_id, []).append(ps)

        def _factors(ps: PairScore) -> list[dict]:
            return [
                {"label": label, "score": getattr(ps, attr) or 0.0}
                for attr, label in (
                    ("embedding_similarity", "Topic match"),
                    ("prerequisite_overlap", "Required skills"),
                    ("resume_experience", "Relevant experience"),
                    ("github_score", "GitHub profile"),
                    ("coding_profiles_score", "Coding profiles"),
                    ("achievements_score", "Achievements"),
                )
            ]

        with_selection = 0

        # Calculate number of workbook selections
        for student in matrix.students:
            reg = student.registration_number.strip().upper()
            if bool(selected_by_reg.get(reg)):
                with_selection += 1

        # ── Group pair scores by project ──
        scores_by_project: dict[int, list[PairScore]] = {}
        for ps in matrix.scores:
            scores_by_project.setdefault(ps.project_id, []).append(ps)

        projects_ctx: list[dict] = []
        student_by_id = {s.candidate_id: s for s in matrix.students}

        for project in matrix.projects:
            # 1. Workbook-selected students for this project
            entries = selected_by_project.get(project.project_id) or []
            selected_students = []
            seen: set[str] = set()
            for reg, display in entries:
                key = reg or f"?{_normalize_name(display)}"
                if key in seen:
                    continue
                seen.add(key)
                stu = student_by_reg.get(reg) if reg else None
                selected_students.append(
                    {
                        "name": stu.candidate_name if stu else display,
                        "registration_number": (
                            stu.registration_number if stu else "(not in this batch)"
                        ),
                    }
                )

            # 2. Recommended candidates — as many as the mentor selected (min 3)
            #    so the two lists compare one-to-one.
            n_recs = max(len(selected_students), 3)
            pairs = scores_by_project.get(project.project_id, [])
            pairs = sorted(pairs, key=lambda p: p.preliminary_score, reverse=True)
            top = pairs[:n_recs]

            recommended_students = []
            for rank, ps in enumerate(top, start=1):
                student_summary = student_by_id.get(ps.candidate_id)
                if not student_summary:
                    continue
                reg = student_summary.registration_number.strip().upper()
                is_selected = False
                if entries:
                    is_selected = any(e_reg == reg for e_reg, _ in entries if e_reg)

                factors = _factors(ps)
                recommended_students.append(
                    {
                        "rank": rank,
                        "student_name": student_summary.candidate_name,
                        "registration_number": student_summary.registration_number,
                        "score": ps.preliminary_score,
                        "is_selected": is_selected,
                        "factors": factors,
                        "why": build_deterministic_why(factors),
                    }
                )

            projects_ctx.append(
                {
                    "project_id": project.project_id,
                    "project_title": project.project_title,
                    "mentor_name": project.mentor_name,
                    "mentor_email": project.mentor_email,
                    "selected_students": selected_students,
                    "recommended_students": recommended_students,
                }
            )

        projects_ctx.sort(key=lambda p: p["project_title"].lower())

        html_str = build_batch_report_html(
            {
                "batch_id": batch_id,
                "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
                "scoring_version": settings.SCORING_VERSION,
                "summary": {
                    "total_students": len(matrix.students),
                    "total_projects": len(matrix.projects),
                    "with_selection": with_selection,
                },
                "projects": projects_ctx,
            }
        )
        pdf = await render_html_to_pdf(html_str)
        return f"batch-{batch_id}-selection-report.pdf", pdf

    def _recover_handles_from_resume(self, candidate: Candidate) -> bool:
        """Backfill developer handles and signals from the parsed resume text.

        Recovers the same set the import flow persists — handles, repos,
        achievements, and live links — so every matching flow sees identical
        signals regardless of entry point. Only fills fields that are currently
        empty, so workbook / user-entered values always win. Returns True if it
        changed anything; no-op when the resume hasn't been parsed yet.
        """
        resume_text = next(
            (
                doc.parsed_text
                for doc in (candidate.documents or [])
                if getattr(doc, "document_type", None) == "resume" and doc.parsed_text
            ),
            None,
        )
        if not resume_text:
            return False

        profiles = extract_profiles(resume_text)
        changed = False

        if profiles.github_username and not candidate.github_username:
            candidate.github_username = profiles.github_username
            changed = True
            logger.info(
                "matching.github_username_recovered_from_resume",
                candidate_id=candidate.id,
                username=profiles.github_username,
            )
        if profiles.github_repositories and not candidate.github_repositories:
            candidate.github_repositories = list(profiles.github_repositories)
            changed = True
        if profiles.leetcode_username and not candidate.leetcode_username:
            candidate.leetcode_username = profiles.leetcode_username
            changed = True
        if profiles.codeforces_username and not candidate.codeforces_username:
            candidate.codeforces_username = profiles.codeforces_username
            changed = True
        if profiles.kaggle_username and not candidate.kaggle_username:
            candidate.kaggle_username = profiles.kaggle_username
            changed = True
        if profiles.scholar_id and not candidate.scholar_id:
            candidate.scholar_id = profiles.scholar_id
            changed = True
        if profiles.achievements and not candidate.achievements:
            candidate.achievements = list(profiles.achievements)
            changed = True
        if profiles.live_links and not candidate.live_project_links:
            candidate.live_project_links = list(profiles.live_links)
            changed = True

        return changed

    async def _ensure_candidate_metrics(self, candidate: Candidate) -> bool:
        """Fetch and persist developer profile metrics missing on a candidate.

        Import extracts usernames (from the workbook and resume PDFs) but does
        not call the external APIs. This backfills github/leetcode/codeforces/
        kaggle/scholar metrics so DB-based matching sees the same signals as
        the live resume-upload flow. Returns True if anything was fetched.
        """
        # Self-heal missing handles from the already-parsed resume. Import-time
        # extraction can lag a match run (or miss if the resume was attached
        # later), which would otherwise leave github_username empty and skip the
        # GitHub fetch entirely. Re-deriving here makes matching independent of
        # that ordering.
        recovered = self._recover_handles_from_resume(candidate)

        # Backfill repos from GitHub metrics that were fetched on an earlier run
        # (nobody links individual repos on a resume), so the repo-count signal
        # isn't left permanently zero once metrics are present.
        repos_backfilled = False
        if (
            candidate.github_username
            and not candidate.github_repositories
            and isinstance(candidate.github_metrics, dict)
            and candidate.github_metrics.get("repository_urls")
        ):
            candidate.github_repositories = list(
                candidate.github_metrics["repository_urls"]
            )
            repos_backfilled = True

        # Heal usernames truncated by PDF line wraps: the repository URLs
        # carry the complete owner name even when the profile URL was cut.
        if candidate.github_username and candidate.github_repositories:
            m = re.match(
                r"https?://github\.com/([^/]+)/", candidate.github_repositories[0]
            )
            if m:
                owner = m.group(1)
                current = candidate.github_username.lower()
                if owner.lower() != current and owner.lower().startswith(current):
                    logger.info(
                        "matching.github_username_healed",
                        candidate_id=candidate.id,
                        old=candidate.github_username,
                        new=owner,
                    )
                    candidate.github_username = owner

        fetch_plan = [
            ("github_metrics", fetch_github_user_metrics, candidate.github_username),
            ("leetcode_metrics", fetch_leetcode_metrics, candidate.leetcode_username),
            (
                "codeforces_metrics",
                fetch_codeforces_metrics,
                candidate.codeforces_username,
            ),
            ("kaggle_metrics", fetch_kaggle_metrics, candidate.kaggle_username),
            ("scholar_metrics", fetch_scholar_metrics, candidate.scholar_id),
        ]
        to_fetch = [
            (attr, fetcher, identifier)
            for attr, fetcher, identifier in fetch_plan
            if identifier and not getattr(candidate, attr)
        ]
        if not to_fetch:
            # Nothing to fetch, but persist any resume-recovered handles or
            # backfilled repos so they aren't re-derived on every request.
            return recovered or repos_backfilled

        results = await asyncio.gather(
            *(
                _safe_fetch_profile_metrics(fetcher, identifier)
                for _, fetcher, identifier in to_fetch
            )
        )

        updated = False
        for (attr, _, _), metrics in zip(to_fetch, results, strict=True):
            # Never persist error placeholders — leave NULL so we retry later
            if isinstance(metrics, dict) and metrics and "fetch_error" not in metrics:
                setattr(candidate, attr, metrics)
                updated = True
                if (
                    attr == "github_metrics"
                    and not candidate.github_repositories
                    and metrics.get("repository_urls")
                ):
                    candidate.github_repositories = metrics["repository_urls"]
        if updated:
            logger.info(
                "matching.candidate_metrics_backfilled",
                candidate_id=candidate.id,
                fetched=[attr for attr, _, _ in to_fetch],
            )
        return updated or recovered or repos_backfilled

    async def _ensure_candidate_evaluations(self, candidate: Candidate) -> bool:
        """Trigger repo clone/review and live-app evaluation when the candidate
        has links but no evaluation rows yet.

        The upload-applicant path runs EvaluationService.refresh_candidate
        immediately, but the DB-candidate matching path historically skipped it.
        This backfills those evaluations so repository_quality_score and
        live_app_score are not left at zero.

        Returns True if evaluations were triggered (caller should reload
        the candidate's evaluation relationships).
        """
        has_links = bool(candidate.github_repositories or candidate.live_project_links)
        already_evaluated = bool(
            candidate.repository_evaluations or candidate.live_app_evaluations
        )
        if not has_links or already_evaluated:
            return False

        from app.features.evaluations.service import EvaluationService

        logger.info(
            "matching.triggering_candidate_evaluations",
            candidate_id=candidate.id,
            repos=len(candidate.github_repositories or []),
            live_links=len(candidate.live_project_links or []),
        )
        evaluator = EvaluationService(self.db)
        await evaluator.refresh_candidate(
            cast(int, candidate.id),
            fetch_remote_profiles=False,
            evaluate_links=True,
            clone_remote_repositories=settings.UPLOAD_APPLICANT_CLONE_REPOS,
            run_repository_tests=False,
        )
        # Reload the evaluation relationships created by refresh_candidate
        # so the scoring engine sees them.
        await self.db.refresh(
            candidate,
            attribute_names=["repository_evaluations", "live_app_evaluations"],
        )
        return True

    async def _is_drive_batch(self, batch_id: int | None) -> bool:
        """Whether a batch was imported from a Drive resumes link (no workbook).

        Drive-sourced batches have no workbook file and carry a ``resumes_url``.
        Their candidates are matched against dummy (batch-less) projects rather
        than batch-scoped projects. Mirrors the ``source`` derivation in the
        candidates API.
        """
        if batch_id is None:
            return False
        from app.features.imports.models import ImportBatch

        res = await self.db.execute(
            select(ImportBatch)
            .options(selectinload(ImportBatch.files))
            .where(ImportBatch.id == batch_id)
        )
        batch = res.scalars().first()
        if not batch:
            return False
        has_workbook = any(f.file_type == "workbook" for f in batch.files)
        return not has_workbook and bool(batch.resumes_url)

    async def recommend_projects_for_db_candidate(
        self, registration_number: str, force: bool = False
    ) -> StudentRecommendationsResponse:
        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
                selectinload(Candidate.repository_evaluations),
                selectinload(Candidate.live_app_evaluations),
            )
            .where(Candidate.registration_number == registration_number)
        )
        res = await self.db.execute(stmt)
        candidate = res.scalars().first()
        if not candidate:
            raise ValueError(
                f"Candidate with registration number {registration_number} not found."
            )

        batch_id = cast("int | None", candidate.import_batch_id)
        if not force:
            cached = await self._load_cached_recommendation(
                batch_id, "student", registration_number
            )
            if cached is not None:
                response = StudentRecommendationsResponse.model_validate(cached)
                response.cached = True
                return response

        self._ensure_llm_ready()

        workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
        doc = next(
            (d for d in candidate.documents if d.document_type == "resume"), None
        )
        resume_text = doc.parsed_text if doc and doc.parsed_text else ""
        known_skills = await self._load_known_skill_names()
        resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
        candidate_skills = self._merge_skills(workbook_skills, resume_skills)

        if await self._ensure_candidate_metrics(candidate):
            await self.db.commit()

        await self._ensure_candidate_evaluations(candidate)

        developer_profile = compute_developer_profile_score(
            github_username=candidate.github_username,
            github_metrics=candidate.github_metrics,
            github_repositories=candidate.github_repositories,
            leetcode_metrics=candidate.leetcode_metrics,
            codeforces_metrics=candidate.codeforces_metrics,
            kaggle_metrics=candidate.kaggle_metrics,
            scholar_metrics=candidate.scholar_metrics,
            achievements=candidate.achievements,
            repository_evaluations=candidate.repository_evaluations,
            live_app_evaluations=candidate.live_app_evaluations,
        )

        # Drive-link candidates (batch has no workbook, only a resumes_url) are
        # matched ONLY against dummy projects (batch-less, import_batch_id NULL).
        # Workbook candidates are matched against their own batch's projects,
        # which naturally excludes dummy projects.
        is_drive_candidate = await self._is_drive_batch(candidate.import_batch_id)

        project_where = (
            Project.import_batch_id.is_(None)
            if is_drive_candidate
            else Project.import_batch_id == candidate.import_batch_id
        )
        stmt = (
            select(Project)
            .options(
                selectinload(Project.mentor),
                selectinload(Project.prerequisites).selectinload(
                    ProjectPrerequisite.skill
                ),
                selectinload(Project.preferences),
            )
            .where(project_where)
        )

        res = await self.db.execute(stmt)
        projects = list(res.scalars().all())

        # Stage 1: deterministic signals for all pairs
        staged: list[tuple[Project, _PairSignals]] = []
        for project in projects:
            signals = await self._compute_pair_signals(
                candidate_name=cast(str, candidate.name),
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number=registration_number,
                project=project,
                developer_profile=developer_profile,
            )
            staged.append((project, signals))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, p.id) for p, _ in staged[:top_k]}

        # Stage 2: LLM only for top-K
        sem = asyncio.Semaphore(settings.MATCH_SIGNAL_CONCURRENCY)

        async def eval_project(project, signals) -> ProjectMatchRecommendation:
            eval_res = None
            if cast(int, project.id) in finalist_ids:
                prereqs = [p.skill.name for p in project.prerequisites if p.skill]
                async with sem:
                    try:
                        eval_res = await generate_project_match_for_student(
                            candidate_name=cast(str, candidate.name),
                            candidate_skills=candidate_skills,
                            resume_text=resume_text,
                            project_title=cast(str, project.title),
                            project_abstract=cast(str, project.abstract or ""),
                            prerequisites=prereqs,
                            preferences=[
                                p.preference_value for p in project.preferences
                            ],
                            preliminary_context=self._preliminary_context(signals),
                        )
                    except Exception as e:
                        logger.warning(
                            "LLM evaluation failed for project, falling back to preliminary score",
                            project_id=project.id,
                            error=str(e),
                        )
                        eval_res = {
                            "llm_error": True,
                            "technical_readiness": "LLM evaluation failed.",
                            "growth_potential": "LLM evaluation failed.",
                            "interest_alignment": "LLM evaluation failed.",
                            "explanation": f"LLM evaluation failed due to provider error: {e}. Preliminary ranking used.",
                            "readiness": 0.0,
                            "growth_potential_score": 0.0,
                            "interest": 0.0,
                            "semantic_fit": 0.0,
                            "scoring_rationale": f"LLM evaluation failed with error: {e}",
                            "missing_prerequisites": [],
                            "compensating_skills": [],
                            "llm_provider": settings.LLM_PROVIDER,
                            "llm_model": {
                                "ollama": settings.OLLAMA_MODEL,
                                "openai": settings.OPENAI_MODEL,
                                "groq": settings.GROQ_MODEL,
                            }.get(settings.LLM_PROVIDER),
                        }
            return self._build_project_recommendation(
                rank=0,
                project=project,
                signals=signals,
                eval_res=eval_res,
                developer_profile=developer_profile,
                achievements=list(candidate.achievements or []),
            )

        tasks = [eval_project(p, s) for p, s in staged]
        recommendations = list(await asyncio.gather(*tasks))

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        response = StudentRecommendationsResponse(
            candidate_name=cast(str, candidate.name),
            registration_number=registration_number,
            achievements=list(candidate.achievements or []),
            recommendations=recommendations,
            cached=False,
        )
        await self._store_cached_recommendation(
            batch_id, "student", registration_number, response.model_dump(mode="json")
        )
        return response

    async def _materialize_and_evaluate_applicant(
        self,
        *,
        resume_text: str,
        github_user: str | None,
        leetcode_user: str | None,
        codeforces_user: str | None,
        kaggle_user: str | None,
        scholar_user: str | None,
        github_url: str | None,
        live_app_url: str | None,
        achievements: list[str] | None,
        resume_repos: list[str] | None,
        live_links: list[str] | None,
    ) -> Candidate | None:
        """Persist an uploaded applicant and run the full evaluation pipeline.

        Creates a Candidate (batch-less, with a generated registration number),
        fetches remote metrics + top-N GitHub repos, then runs the same
        deterministic clone/static review + agy agent DB candidates use. Returns
        the reloaded candidate with its evaluations, ready for scoring. The agy
        logic/live-app scores land later via callback (eventual consistency),
        exactly as for DB candidates.
        """
        from app.features.evaluations.service import EvaluationService

        seed_repos: list[str] = []
        if github_url and "/github.com/" in github_url.lower():
            parts = github_url.rstrip("/").split("github.com/")
            if len(parts) > 1 and len(parts[1].split("/")) >= 2:
                seed_repos.append(github_url)
        seed_repos.extend(resume_repos or [])

        seed_live: list[str] = []
        if live_app_url and live_app_url.strip():
            seed_live.append(live_app_url.strip())
        seed_live.extend(live_links or [])

        candidate = Candidate(
            registration_number=f"UPLOAD-{uuid.uuid4().hex[:12].upper()}",
            name="Applicant",
            github_username=github_user,
            leetcode_username=leetcode_user,
            codeforces_username=codeforces_user,
            kaggle_username=kaggle_user,
            scholar_id=scholar_user,
            github_repositories=list(dict.fromkeys(seed_repos)) or None,
            live_project_links=list(dict.fromkeys(seed_live)) or None,
            achievements=list(achievements) if achievements else None,
            evaluation_status="Pending",
        )
        candidate.documents.append(
            CandidateDocument(
                document_type="resume",
                parse_status="parsed",
                parsed_text=resume_text,
            )
        )
        self.db.add(candidate)
        await self.db.commit()
        candidate_id = cast(int, candidate.id)

        # Reload with documents so metric recovery/backfill can run.
        candidate = (
            (
                await self.db.execute(
                    select(Candidate)
                    .options(selectinload(Candidate.documents))
                    .where(Candidate.id == candidate_id)
                )
            )
            .scalars()
            .first()
        )
        assert (
            candidate is not None
        ), f"Candidate {candidate_id} disappeared after commit"

        # Fetch remote metrics + top-N repos via the shared path, then cap how
        # many repos we clone to keep upload latency bounded.
        if await self._ensure_candidate_metrics(candidate):
            await self.db.commit()
        max_repos = settings.UPLOAD_APPLICANT_MAX_REPOS
        if (
            candidate.github_repositories
            and len(candidate.github_repositories) > max_repos
        ):
            candidate.github_repositories = candidate.github_repositories[:max_repos]
            await self.db.commit()

        evaluator = EvaluationService(self.db)
        await evaluator.refresh_candidate(
            candidate_id,
            fetch_remote_profiles=False,
            evaluate_links=True,
            clone_remote_repositories=settings.UPLOAD_APPLICANT_CLONE_REPOS,
            run_repository_tests=False,
        )

        await self.db.refresh(
            candidate,
            attribute_names=["repository_evaluations", "live_app_evaluations"],
        )
        return candidate

    async def recommend_projects_for_student(
        self,
        resume_bytes: bytes,
        preferred_topics: list[str],
        github_url: str | None = None,
        leetcode_url: str | None = None,
        codeforces_url: str | None = None,
        kaggle_url: str | None = None,
        scholar_url: str | None = None,
        live_app_url: str | None = None,
    ) -> StudentRecommendationsResponse:
        self._ensure_llm_ready()

        loop = asyncio.get_running_loop()
        resume_text = await loop.run_in_executor(None, parse_pdf_bytes, resume_bytes)
        known_skills = await self._load_known_skill_names()
        candidate_skills = self._extract_skills_from_resume(resume_text, known_skills)
        for topic in preferred_topics:
            if topic and topic not in candidate_skills:
                candidate_skills.append(topic)

        github_user = parse_username(github_url, "github.com") if github_url else None
        leetcode_user = (
            parse_username(leetcode_url, "leetcode.com") if leetcode_url else None
        )
        codeforces_user = (
            parse_username(codeforces_url, "codeforces.com") if codeforces_url else None
        )
        kaggle_user = parse_username(kaggle_url, "kaggle.com") if kaggle_url else None
        scholar_user = None
        if scholar_url:
            match = re.search(
                r"user=([A-Za-z0-9_\-]{8,20})", scholar_url, re.IGNORECASE
            )
            if match:
                scholar_user = match.group(1)
            # No loose fallback: parse_username on a Scholar URL returns the
            # path segment ("citations"), not a real ID. The resume fallback
            # below fills a valid scholar_id if the form value is unusable.

        # Fall back to the uploaded resume for any handle the applicant did not
        # supply via the form, so this flow derives the same signals as the
        # DB / import flows (which self-heal via _recover_handles_from_resume).
        resume_profiles = extract_profiles(resume_text)
        github_user = github_user or resume_profiles.github_username
        leetcode_user = leetcode_user or resume_profiles.leetcode_username
        codeforces_user = codeforces_user or resume_profiles.codeforces_username
        kaggle_user = kaggle_user or resume_profiles.kaggle_username
        scholar_user = scholar_user or resume_profiles.scholar_id

        # True parity: persist the applicant as a Candidate and run the same
        # evaluation pipeline DB candidates use (metrics + deterministic repo /
        # live-app review + agy agent), so github_score isn't structurally
        # capped for uploads. Falls back to a metrics-only profile if disabled
        # or if the pipeline errors, so a match is always returned.
        applicant: Candidate | None = None
        if settings.UPLOAD_APPLICANT_FULL_EVAL:
            try:
                applicant = await self._materialize_and_evaluate_applicant(
                    resume_text=resume_text,
                    github_user=github_user,
                    leetcode_user=leetcode_user,
                    codeforces_user=codeforces_user,
                    kaggle_user=kaggle_user,
                    scholar_user=scholar_user,
                    github_url=github_url,
                    live_app_url=live_app_url,
                    achievements=resume_profiles.achievements,
                    resume_repos=resume_profiles.github_repositories,
                    live_links=resume_profiles.live_links,
                )
            except Exception as exc:
                # Never fail the match because evaluation errored; fall back.
                await self.db.rollback()
                logger.warning("matching.upload_full_evaluation_failed", error=str(exc))
                applicant = None

        if applicant is not None:
            developer_profile = compute_developer_profile_score(
                github_username=applicant.github_username,
                github_metrics=applicant.github_metrics,
                github_repositories=applicant.github_repositories,
                leetcode_metrics=applicant.leetcode_metrics,
                codeforces_metrics=applicant.codeforces_metrics,
                kaggle_metrics=applicant.kaggle_metrics,
                scholar_metrics=applicant.scholar_metrics,
                achievements=applicant.achievements,
                repository_evaluations=applicant.repository_evaluations,
                live_app_evaluations=applicant.live_app_evaluations,
            )
        else:
            github_metrics = (
                await _safe_fetch_profile_metrics(
                    fetch_github_user_metrics, github_user
                )
                if github_user
                else None
            )
            leetcode_metrics = (
                await _safe_fetch_profile_metrics(fetch_leetcode_metrics, leetcode_user)
                if leetcode_user
                else None
            )
            codeforces_metrics = (
                await _safe_fetch_profile_metrics(
                    fetch_codeforces_metrics, codeforces_user
                )
                if codeforces_user
                else None
            )
            kaggle_metrics = (
                await _safe_fetch_profile_metrics(fetch_kaggle_metrics, kaggle_user)
                if kaggle_user
                else None
            )
            scholar_metrics = (
                await _safe_fetch_profile_metrics(fetch_scholar_metrics, scholar_user)
                if scholar_user
                else None
            )

            # Repo URLs, in priority order: an explicit repo link the applicant
            # pasted, then repo links in the resume, then the GitHub API top-10.
            github_repos: list[str] = []
            if github_url and "/github.com/" in github_url.lower():
                parts = github_url.rstrip("/").split("github.com/")
                if len(parts) > 1 and len(parts[1].split("/")) >= 2:
                    github_repos.append(github_url)
            if not github_repos and resume_profiles.github_repositories:
                github_repos = list(resume_profiles.github_repositories)
            if (
                not github_repos
                and isinstance(github_metrics, dict)
                and github_metrics.get("repository_urls")
            ):
                github_repos = list(github_metrics["repository_urls"])

            developer_profile = compute_developer_profile_score(
                github_username=github_user,
                github_metrics=github_metrics,
                github_repositories=github_repos,
                leetcode_metrics=leetcode_metrics,
                codeforces_metrics=codeforces_metrics,
                kaggle_metrics=kaggle_metrics,
                scholar_metrics=scholar_metrics,
                achievements=resume_profiles.achievements,
                repository_evaluations=[],
                live_app_evaluations=[],
            )

        stmt = select(Project).options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        res = await self.db.execute(stmt)
        projects = res.scalars().all()

        applicant_achievements = list(
            (applicant.achievements if applicant is not None else None)
            or resume_profiles.achievements
            or []
        )

        staged: list[tuple[Project, _PairSignals]] = []
        for project in projects:
            signals = await self._compute_pair_signals(
                candidate_name="Applicant",
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number="",
                project=project,
                developer_profile=developer_profile,
            )
            staged.append((project, signals))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, p.id) for p, _ in staged[:top_k]}

        # Stage 2: LLM only for top-K
        sem = asyncio.Semaphore(settings.MATCH_SIGNAL_CONCURRENCY)

        async def eval_project(project, signals) -> ProjectMatchRecommendation:
            eval_res = None
            if cast(int, project.id) in finalist_ids:
                prereqs = [p.skill.name for p in project.prerequisites if p.skill]
                async with sem:
                    try:
                        eval_res = await generate_project_match_for_student(
                            candidate_name="Applicant",
                            candidate_skills=candidate_skills,
                            resume_text=resume_text,
                            project_title=cast(str, project.title),
                            project_abstract=cast(str, project.abstract or ""),
                            prerequisites=prereqs,
                            preferences=[],
                            preliminary_context=self._preliminary_context(signals),
                        )
                    except Exception as e:
                        logger.warning(
                            "LLM evaluation failed for project, falling back to preliminary score",
                            project_id=project.id,
                            error=str(e),
                        )
                        eval_res = {
                            "llm_error": True,
                            "technical_readiness": "LLM evaluation failed.",
                            "growth_potential": "LLM evaluation failed.",
                            "interest_alignment": "LLM evaluation failed.",
                            "explanation": f"LLM evaluation failed due to provider error: {e}. Preliminary ranking used.",
                            "readiness": 0.0,
                            "growth_potential_score": 0.0,
                            "interest": 0.0,
                            "semantic_fit": 0.0,
                            "scoring_rationale": f"LLM evaluation failed with error: {e}",
                            "missing_prerequisites": [],
                            "compensating_skills": [],
                            "llm_provider": settings.LLM_PROVIDER,
                            "llm_model": {
                                "ollama": settings.OLLAMA_MODEL,
                                "openai": settings.OPENAI_MODEL,
                                "groq": settings.GROQ_MODEL,
                            }.get(settings.LLM_PROVIDER),
                        }
            return self._build_project_recommendation(
                rank=0,
                project=project,
                signals=signals,
                eval_res=eval_res,
                developer_profile=developer_profile,
                achievements=applicant_achievements,
            )

        tasks = [eval_project(p, s) for p, s in staged]
        recommendations = list(await asyncio.gather(*tasks))

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        return StudentRecommendationsResponse(
            candidate_name="Applicant",
            # Surface the persisted applicant's generated reg number so the
            # frontend can request a downloadable report for the upload flow.
            registration_number=(
                applicant.registration_number if applicant is not None else ""
            ),
            achievements=applicant_achievements,
            recommendations=recommendations,
        )

    async def recommend_candidates_for_project(
        self, project_id: int, force: bool = False
    ) -> ProjectRecommendationsResponse:
        stmt = (
            select(Project)
            .options(
                selectinload(Project.mentor),
                selectinload(Project.prerequisites).selectinload(
                    ProjectPrerequisite.skill
                ),
                selectinload(Project.preferences),
            )
            .where(Project.id == project_id)
        )
        res = await self.db.execute(stmt)
        project = res.scalars().first()
        if not project:
            raise ValueError(f"Project with ID {project_id} not found.")

        batch_id = cast("int | None", project.import_batch_id)
        if not force:
            cached = await self._load_cached_recommendation(
                batch_id, "project", str(project_id)
            )
            if cached is not None:
                response = ProjectRecommendationsResponse.model_validate(cached)
                response.cached = True
                return response

        self._ensure_llm_ready()

        known_skills = await self._load_known_skill_names()

        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
                selectinload(Candidate.repository_evaluations),
                selectinload(Candidate.live_app_evaluations),
            )
            .where(Candidate.import_batch_id == project.import_batch_id)
        )
        res = await self.db.execute(stmt)
        candidates = res.scalars().all()

        metrics_updated = False
        for candidate in candidates:
            if await self._ensure_candidate_metrics(candidate):
                metrics_updated = True
        if metrics_updated:
            await self.db.commit()

        for candidate in candidates:
            await self._ensure_candidate_evaluations(candidate)

        staged: list[tuple[Candidate, _PairSignals, list[str], str]] = []
        for candidate in candidates:
            workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
            doc = next(
                (d for d in candidate.documents if d.document_type == "resume"), None
            )
            resume_text = doc.parsed_text if doc and doc.parsed_text else ""
            resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
            candidate_skills = self._merge_skills(workbook_skills, resume_skills)

            developer_profile = compute_developer_profile_score(
                github_username=candidate.github_username,
                github_metrics=candidate.github_metrics,
                github_repositories=candidate.github_repositories,
                leetcode_metrics=candidate.leetcode_metrics,
                codeforces_metrics=candidate.codeforces_metrics,
                kaggle_metrics=candidate.kaggle_metrics,
                scholar_metrics=candidate.scholar_metrics,
                achievements=candidate.achievements,
                repository_evaluations=candidate.repository_evaluations,
                live_app_evaluations=candidate.live_app_evaluations,
            )

            signals = await self._compute_pair_signals(
                candidate_name=cast(str, candidate.name),
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number=cast(str, candidate.registration_number),
                project=project,
                developer_profile=developer_profile,
            )
            staged.append((candidate, signals, candidate_skills, resume_text))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, c.id) for c, _, _, _ in staged[:top_k]}

        prereqs = [p.skill.name for p in project.prerequisites if p.skill]
        sem = asyncio.Semaphore(settings.MATCH_SIGNAL_CONCURRENCY)

        async def eval_candidate(
            candidate, signals, candidate_skills, resume_text
        ) -> StudentMatchRecommendation:
            eval_res = None
            if cast(int, candidate.id) in finalist_ids:
                async with sem:
                    try:
                        eval_res = await generate_candidate_match_for_mentor(
                            candidate_name=cast(str, candidate.name),
                            candidate_skills=candidate_skills,
                            resume_text=resume_text,
                            project_title=cast(str, project.title),
                            project_abstract=cast(str, project.abstract or ""),
                            prerequisites=prereqs,
                            preferences=[
                                p.preference_value for p in project.preferences
                            ],
                            preliminary_context=self._preliminary_context(signals),
                        )
                    except Exception as e:
                        logger.warning(
                            "LLM evaluation failed for candidate, falling back to preliminary score",
                            candidate_id=candidate.id,
                            error=str(e),
                        )
                        eval_res = {
                            "llm_error": True,
                            "technical_readiness": "LLM evaluation failed.",
                            "growth_potential": "LLM evaluation failed.",
                            "interest_alignment": "LLM evaluation failed.",
                            "explanation": f"LLM evaluation failed due to provider error: {e}. Preliminary ranking used.",
                            "readiness": 0.0,
                            "growth_potential_score": 0.0,
                            "interest": 0.0,
                            "semantic_fit": 0.0,
                            "scoring_rationale": f"LLM evaluation failed with error: {e}",
                            "missing_prerequisites": [],
                            "compensating_skills": [],
                            "llm_provider": settings.LLM_PROVIDER,
                            "llm_model": {
                                "ollama": settings.OLLAMA_MODEL,
                                "openai": settings.OPENAI_MODEL,
                                "groq": settings.GROQ_MODEL,
                            }.get(settings.LLM_PROVIDER),
                        }
            return self._build_student_recommendation(
                rank=0,
                candidate=candidate,
                _project=project,
                signals=signals,
                eval_res=eval_res,
            )

        tasks = [eval_candidate(c, s, cs, r) for c, s, cs, r in staged]
        recommendations = list(await asyncio.gather(*tasks))

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        response = ProjectRecommendationsResponse(
            project_id=cast(int, project.id),
            project_title=cast(str, project.title),
            recommendations=recommendations,
            cached=False,
        )
        await self._store_cached_recommendation(
            batch_id, "project", str(project_id), response.model_dump(mode="json")
        )
        return response

    async def compute_batch_scores(
        self, batch_id: int, force: bool = False
    ) -> BatchScoreMatrixResponse:
        """
        Return deterministic (no-LLM) scores for every student-project pair in a batch.

        On the first call the scores are computed and persisted to `batch_pair_scores`.
        On subsequent calls the cached rows are returned instantly.
        Pass force=True to delete existing cache and recompute from scratch.

        Single-flight per batch: a cold compute takes minutes, so concurrent
        requests (e.g. the user reloading mid-run) wait for the in-flight
        computation and then serve its freshly written cache instead of racing
        it with a second full compute.
        """
        async with _get_batch_score_lock(batch_id):
            return await self._compute_batch_scores_inner(batch_id, force=force)

    async def _compute_batch_scores_inner(
        self, batch_id: int, *, force: bool
    ) -> BatchScoreMatrixResponse:
        # ── 1. Load candidates and projects for this batch ────────────────────
        cand_stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
                selectinload(Candidate.repository_evaluations),
                selectinload(Candidate.live_app_evaluations),
            )
            .where(Candidate.import_batch_id == batch_id)
        )
        cand_res = await self.db.execute(cand_stmt)
        candidates = list(cand_res.scalars().all())

        # Drive-link batches have no projects of their own; score their students
        # against the dummy (batch-less) projects instead — same rule as the
        # single-student matcher.
        is_drive = await self._is_drive_batch(batch_id)
        proj_where = (
            Project.import_batch_id.is_(None)
            if is_drive
            else Project.import_batch_id == batch_id
        )
        proj_stmt = (
            select(Project)
            .options(
                selectinload(Project.mentor),
                selectinload(Project.prerequisites).selectinload(
                    ProjectPrerequisite.skill
                ),
                selectinload(Project.preferences),
            )
            .where(proj_where)
        )
        proj_res = await self.db.execute(proj_stmt)
        projects = list(proj_res.scalars().all())

        if not candidates or not projects:
            return BatchScoreMatrixResponse(
                batch_id=batch_id,
                students=[],
                projects=[],
                scores=[],
                cached=False,
            )

        # ── 2. Backfill missing developer metrics from public APIs ────────────
        # Usernames come from the workbook/resumes at import time, but metrics
        # are only fetched here (or via the evaluations refresh). If any were
        # missing and are now fetched, the cached score matrix is stale.
        # Backfill every candidate concurrently (bounded) instead of one after
        # another. The per-candidate fetch does no DB I/O — it only reads
        # already-loaded attributes and awaits independent external clients — so
        # this is safe to run against the shared session and turns N sequential
        # rounds of network calls into a few concurrent waves.
        backfill_sem = asyncio.Semaphore(_METRICS_BACKFILL_CONCURRENCY)

        async def _backfill(candidate: Candidate) -> bool:
            async with backfill_sem:
                return await self._ensure_candidate_metrics(candidate)

        metrics_results = await asyncio.gather(
            *(_backfill(candidate) for candidate in candidates)
        )
        if any(metrics_results):
            await self.db.commit()
            force = True

        # ── 3. Build lookup structures ─────────────────────────────────────────
        candidate_map = {cast(int, c.id): c for c in candidates}
        project_map = {cast(int, p.id): p for p in projects}

        student_summaries = [
            BatchStudentSummary(
                candidate_id=cast(int, c.id),
                candidate_name=cast(str, c.name),
                registration_number=cast(str, c.registration_number),
            )
            for c in candidates
        ]
        project_summaries = [
            BatchProjectSummary(
                project_id=cast(int, p.id),
                project_title=cast(str, p.title),
                mentor_name=p.mentor.name if p.mentor else "Unknown",
                mentor_email=p.mentor.email if p.mentor else None,
            )
            for p in projects
        ]

        # ── 3. Check for cached rows ───────────────────────────────────────────
        if force:
            # Delete existing cached rows for this batch so we recompute fresh
            from sqlalchemy import (
                delete as sa_delete,  # local import to avoid shadowing
            )

            await self.db.execute(
                sa_delete(BatchPairScore).where(BatchPairScore.batch_id == batch_id)
            )
            await self.db.flush()
            cached_rows: list[BatchPairScore] = []
        else:
            cached_stmt = select(BatchPairScore).where(
                BatchPairScore.batch_id == batch_id
            )
            cached_res = await self.db.execute(cached_stmt)
            cached_rows = list(cached_res.scalars().all())

        if cached_rows:
            # ── Serve from cache ──────────────────────────────────────────────
            # Dedupe by pair: past concurrent computes (before the single-flight
            # lock) could double-insert rows, which would e.g. show the same
            # project twice in a student's top-2.
            unique_rows: dict[tuple[int, int], BatchPairScore] = {}
            for row in cached_rows:
                unique_rows.setdefault((row.candidate_id, row.project_id), row)
            cached_rows = list(unique_rows.values())
            pair_scores = [
                PairScore(
                    candidate_id=row.candidate_id,
                    project_id=row.project_id,
                    embedding_similarity=row.embedding_similarity,
                    prerequisite_overlap=row.prerequisite_overlap,
                    resume_experience=row.resume_experience,
                    preference_signal=row.preference_signal,
                    github_score=row.github_score,
                    coding_profiles_score=row.coding_profiles_score,
                    achievements_score=row.achievements_score,
                    repository_quality_score=row.repository_quality_score,
                    live_app_score=row.live_app_score,
                    preliminary_score=row.preliminary_score,
                )
                for row in cached_rows
                # Filter to only pairs whose candidate and project are in this batch
                if row.candidate_id in candidate_map and row.project_id in project_map
            ]
            first_computed = min(row.computed_at for row in cached_rows)
            return BatchScoreMatrixResponse(
                batch_id=batch_id,
                students=student_summaries,
                projects=project_summaries,
                scores=pair_scores,
                cached=True,
                computed_at=first_computed.isoformat(),
            )

        # ── 4. Compute fresh and persist ──────────────────────────────────────
        known_skills = await self._load_known_skill_names()
        pair_scores = []
        db_rows: list[BatchPairScore] = []

        # Pre-pass: build each candidate's merged skills/resume once, then
        # batch-encode every unique profile text in one model call. Without
        # this, the pair loop encodes each text individually (~10s each on
        # CPU), which is what made a cold batch run take minutes.
        candidate_inputs: list[tuple[Candidate, list[str], str]] = []
        profile_texts: list[str] = []
        for candidate in candidates:
            workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
            doc = next(
                (d for d in candidate.documents if d.document_type == "resume"), None
            )
            resume_text = doc.parsed_text if doc and doc.parsed_text else ""
            resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
            candidate_skills = self._merge_skills(workbook_skills, resume_skills)
            candidate_inputs.append((candidate, candidate_skills, resume_text))
            profile_texts.append(
                build_candidate_profile_text(
                    cast(str, candidate.name), candidate_skills, resume_text
                ).strip()
            )
        for project in projects:
            profile_texts.append(
                build_project_profile_text(
                    cast(str, project.title),
                    cast(str, project.abstract or ""),
                    [p.skill.name for p in project.prerequisites if p.skill],
                ).strip()
            )
        embed_start = time.perf_counter()
        await precompute_embeddings(profile_texts)
        logger.info(
            "matching.batch_embeddings_precomputed",
            batch_id=batch_id,
            texts=len(profile_texts),
            duration_s=round(time.perf_counter() - embed_start, 2),
        )

        for candidate, candidate_skills, resume_text in candidate_inputs:
            developer_profile = compute_developer_profile_score(
                github_username=candidate.github_username,
                github_metrics=candidate.github_metrics,
                github_repositories=candidate.github_repositories,
                leetcode_metrics=candidate.leetcode_metrics,
                codeforces_metrics=candidate.codeforces_metrics,
                kaggle_metrics=candidate.kaggle_metrics,
                scholar_metrics=candidate.scholar_metrics,
                achievements=candidate.achievements,
                repository_evaluations=candidate.repository_evaluations,
                live_app_evaluations=candidate.live_app_evaluations,
            )

            for project in projects:
                signals = await self._compute_pair_signals(
                    candidate_name=cast(str, candidate.name),
                    candidate_skills=candidate_skills,
                    resume_text=resume_text,
                    registration_number=cast(str, candidate.registration_number),
                    project=project,
                    developer_profile=developer_profile,
                )
                score = PairScore(
                    candidate_id=cast(int, candidate.id),
                    project_id=cast(int, project.id),
                    embedding_similarity=round(signals.embedding_sim, 4),
                    prerequisite_overlap=round(signals.prereq_overlap.score, 4),
                    resume_experience=round(signals.resume_experience.score, 4),
                    preference_signal=round(signals.preference_signal.score, 4),
                    github_score=round(developer_profile.github_score, 4),
                    coding_profiles_score=round(
                        developer_profile.coding_profiles_score, 4
                    ),
                    achievements_score=round(developer_profile.achievements_score, 4),
                    repository_quality_score=round(
                        developer_profile.repository_quality_score, 4
                    ),
                    live_app_score=round(developer_profile.live_app_score, 4),
                    preliminary_score=round(signals.preliminary_score, 4),
                )
                pair_scores.append(score)
                db_rows.append(
                    BatchPairScore(
                        batch_id=batch_id,
                        candidate_id=score.candidate_id,
                        project_id=score.project_id,
                        embedding_similarity=score.embedding_similarity,
                        prerequisite_overlap=score.prerequisite_overlap,
                        resume_experience=score.resume_experience,
                        preference_signal=score.preference_signal,
                        github_score=score.github_score,
                        coding_profiles_score=score.coding_profiles_score,
                        achievements_score=score.achievements_score,
                        repository_quality_score=score.repository_quality_score,
                        live_app_score=score.live_app_score,
                        preliminary_score=score.preliminary_score,
                    )
                )

        # Persist all rows in one flush
        self.db.add_all(db_rows)
        await self.db.commit()

        return BatchScoreMatrixResponse(
            batch_id=batch_id,
            students=student_summaries,
            projects=project_summaries,
            scores=pair_scores,
            cached=False,
        )
