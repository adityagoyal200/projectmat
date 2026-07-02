import asyncio
import re
from dataclasses import dataclass
from typing import cast

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.features.candidates.models import Candidate, CandidateSkill
from app.features.imports.drive_downloader import parse_pdf_bytes
from app.features.matching.embeddings import (
    build_candidate_profile_text,
    build_project_profile_text,
    embedding_similarity,
)
from app.features.matching.exceptions import MatchingUnavailableError
from app.features.matching.match_explanation import (
    generate_candidate_match_for_mentor,
    generate_project_match_for_student,
)
from app.features.matching.models import BatchPairScore
from app.features.matching.schemas import (
    BatchProjectSummary,
    BatchScoreMatrixResponse,
    BatchStudentSummary,
    PairScore,
    ProjectMatchRecommendation,
    ProjectRecommendationsResponse,
    ScoreBreakdown,
    ScoreComponents,
    StudentMatchRecommendation,
    StudentRecommendationsResponse,
)
from app.features.matching.scoring import (
    LlmScoreComponents,
    PreferenceSignalResult,
    PrerequisiteOverlapResult,
    ResumeExperienceResult,
    compute_hybrid_final_score,
    compute_preference_signal,
    compute_preliminary_score,
    compute_prerequisite_overlap,
    compute_resume_experience,
)
from app.features.projects.models import Project, ProjectPrerequisite
from app.features.shared.models import Skill

logger = structlog.get_logger()


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

    def _build_preference_pairs(self, project) -> list[tuple[str, str]]:
        return [(p.preference_type, p.preference_value) for p in project.preferences]

    def _extract_skills_from_resume(
        self, resume_text: str, known_skills: list[str]
    ) -> list[str]:
        found: list[str] = []
        for skill_name in known_skills:
            if re.search(rf"\b{re.escape(skill_name)}\b", resume_text, re.IGNORECASE):
                found.append(skill_name)
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
    ) -> _PairSignals:
        prereqs = [p.skill.name for p in project.prerequisites if p.skill]
        project_abstract = cast(str, project.abstract or "")

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
    ) -> ProjectMatchRecommendation:
        llm_scores = None
        if eval_res:
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
            rationale = "N/A ΓÇö preliminary signals only."
            llm_provider = None
            llm_model = None

        return ProjectMatchRecommendation(
            rank=rank,
            project_id=cast(int, project.id),
            project_title=cast(str, project.title),
            mentor_name=project.mentor.name if project.mentor else "Unknown",
            mentor_email=project.mentor.email if project.mentor else None,
            mentor_phone=project.mentor.phone if project.mentor else None,
            final_score=hybrid.final_score,
            score_components=ScoreComponents(
                embedding_similarity=hybrid.embedding_similarity,
                readiness=hybrid.readiness,
                growth_potential=hybrid.growth_potential,
                interest=hybrid.interest,
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
        if eval_res:
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
            rationale = "N/A ΓÇö preliminary signals only."
            llm_provider = None
            llm_model = None

        return StudentMatchRecommendation(
            rank=rank,
            candidate_id=cast(int, candidate.id),
            candidate_name=cast(str, candidate.name),
            registration_number=cast(str, candidate.registration_number),
            final_score=hybrid.final_score,
            score_components=ScoreComponents(
                embedding_similarity=hybrid.embedding_similarity,
                readiness=hybrid.readiness,
                growth_potential=hybrid.growth_potential,
                interest=hybrid.interest,
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

    async def recommend_projects_for_db_candidate(
        self, registration_number: str
    ) -> StudentRecommendationsResponse:
        self._ensure_llm_ready()

        stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
            )
            .where(Candidate.registration_number == registration_number)
        )
        res = await self.db.execute(stmt)
        candidate = res.scalars().first()
        if not candidate:
            raise ValueError(
                f"Candidate with registration number {registration_number} not found."
            )

        workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
        doc = next(
            (d for d in candidate.documents if d.document_type == "resume"), None
        )
        resume_text = doc.parsed_text if doc and doc.parsed_text else ""
        known_skills = await self._load_known_skill_names()
        resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
        candidate_skills = self._merge_skills(workbook_skills, resume_skills)

        stmt = select(Project).options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        res = await self.db.execute(stmt)
        projects = res.scalars().all()

        # Stage 1: deterministic signals for all pairs
        staged: list[tuple[Project, _PairSignals]] = []
        for project in projects:
            signals = await self._compute_pair_signals(
                candidate_name=cast(str, candidate.name),
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number=registration_number,
                project=project,
            )
            staged.append((project, signals))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, p.id) for p, _ in staged[:top_k]}

        # Stage 2: LLM only for top-K
        recommendations: list[ProjectMatchRecommendation] = []
        for project, signals in staged:
            eval_res = None
            if cast(int, project.id) in finalist_ids:
                prereqs = [p.skill.name for p in project.prerequisites if p.skill]
                eval_res = await generate_project_match_for_student(
                    candidate_name=cast(str, candidate.name),
                    candidate_skills=candidate_skills,
                    resume_text=resume_text,
                    project_title=cast(str, project.title),
                    project_abstract=cast(str, project.abstract or ""),
                    prerequisites=prereqs,
                    preferences=[p.preference_value for p in project.preferences],
                    preliminary_context=self._preliminary_context(signals),
                )
            recommendations.append(
                self._build_project_recommendation(
                    rank=0,
                    project=project,
                    signals=signals,
                    eval_res=eval_res,
                )
            )

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        return StudentRecommendationsResponse(
            candidate_name=cast(str, candidate.name),
            registration_number=registration_number,
            recommendations=recommendations,
        )

    async def recommend_projects_for_student(
        self, resume_bytes: bytes, preferred_topics: list[str]
    ) -> StudentRecommendationsResponse:
        self._ensure_llm_ready()

        loop = asyncio.get_running_loop()
        resume_text = await loop.run_in_executor(None, parse_pdf_bytes, resume_bytes)
        known_skills = await self._load_known_skill_names()
        candidate_skills = self._extract_skills_from_resume(resume_text, known_skills)
        for topic in preferred_topics:
            if topic and topic not in candidate_skills:
                candidate_skills.append(topic)

        stmt = select(Project).options(
            selectinload(Project.mentor),
            selectinload(Project.prerequisites).selectinload(ProjectPrerequisite.skill),
            selectinload(Project.preferences),
        )
        res = await self.db.execute(stmt)
        projects = res.scalars().all()

        staged: list[tuple[Project, _PairSignals]] = []
        for project in projects:
            signals = await self._compute_pair_signals(
                candidate_name="Applicant",
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number="",
                project=project,
            )
            staged.append((project, signals))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, p.id) for p, _ in staged[:top_k]}

        recommendations: list[ProjectMatchRecommendation] = []
        for project, signals in staged:
            eval_res = None
            if cast(int, project.id) in finalist_ids:
                prereqs = [p.skill.name for p in project.prerequisites if p.skill]
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
            recommendations.append(
                self._build_project_recommendation(
                    rank=0,
                    project=project,
                    signals=signals,
                    eval_res=eval_res,
                )
            )

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        return StudentRecommendationsResponse(
            candidate_name="Applicant",
            registration_number="",
            recommendations=recommendations,
        )

    async def recommend_candidates_for_project(
        self, project_id: int
    ) -> ProjectRecommendationsResponse:
        self._ensure_llm_ready()

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

        known_skills = await self._load_known_skill_names()

        stmt = select(Candidate).options(
            selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
            selectinload(Candidate.documents),
        )
        res = await self.db.execute(stmt)
        candidates = res.scalars().all()

        staged: list[tuple[Candidate, _PairSignals, list[str], str]] = []
        for candidate in candidates:
            workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
            doc = next(
                (d for d in candidate.documents if d.document_type == "resume"), None
            )
            resume_text = doc.parsed_text if doc and doc.parsed_text else ""
            resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
            candidate_skills = self._merge_skills(workbook_skills, resume_skills)

            signals = await self._compute_pair_signals(
                candidate_name=cast(str, candidate.name),
                candidate_skills=candidate_skills,
                resume_text=resume_text,
                registration_number=cast(str, candidate.registration_number),
                project=project,
            )
            staged.append((candidate, signals, candidate_skills, resume_text))

        staged.sort(key=lambda x: x[1].preliminary_score, reverse=True)
        top_k = settings.MATCH_LLM_TOP_K
        finalist_ids = {cast(int, c.id) for c, _, _, _ in staged[:top_k]}

        prereqs = [p.skill.name for p in project.prerequisites if p.skill]
        recommendations: list[StudentMatchRecommendation] = []
        for candidate, signals, candidate_skills, resume_text in staged:
            eval_res = None
            if cast(int, candidate.id) in finalist_ids:
                eval_res = await generate_candidate_match_for_mentor(
                    candidate_name=cast(str, candidate.name),
                    candidate_skills=candidate_skills,
                    resume_text=resume_text,
                    project_title=cast(str, project.title),
                    project_abstract=cast(str, project.abstract or ""),
                    prerequisites=prereqs,
                    preferences=[p.preference_value for p in project.preferences],
                    preliminary_context=self._preliminary_context(signals),
                )
            recommendations.append(
                self._build_student_recommendation(
                    rank=0,
                    candidate=candidate,
                    _project=project,
                    signals=signals,
                    eval_res=eval_res,
                )
            )

        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for idx, rec in enumerate(recommendations, start=1):
            recommendations[idx - 1] = rec.model_copy(update={"rank": idx})

        return ProjectRecommendationsResponse(
            project_id=cast(int, project.id),
            project_title=cast(str, project.title),
            recommendations=recommendations,
        )

    async def compute_batch_scores(
        self, batch_id: int, force: bool = False
    ) -> BatchScoreMatrixResponse:
        """
        Return deterministic (no-LLM) scores for every student-project pair in a batch.

        On the first call the scores are computed and persisted to `batch_pair_scores`.
        On subsequent calls the cached rows are returned instantly.
        Pass force=True to delete existing cache and recompute from scratch.
        """
        # ΓöÇΓöÇ 1. Load candidates and projects for this batch ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        cand_stmt = (
            select(Candidate)
            .options(
                selectinload(Candidate.skills).selectinload(CandidateSkill.skill),
                selectinload(Candidate.documents),
            )
            .where(Candidate.import_batch_id == batch_id)
        )
        cand_res = await self.db.execute(cand_stmt)
        candidates = list(cand_res.scalars().all())

        proj_stmt = (
            select(Project)
            .options(
                selectinload(Project.mentor),
                selectinload(Project.prerequisites).selectinload(
                    ProjectPrerequisite.skill
                ),
                selectinload(Project.preferences),
            )
            .where(Project.import_batch_id == batch_id)
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

        # ΓöÇΓöÇ 2. Build lookup structures ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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

        # ΓöÇΓöÇ 3. Check for cached rows ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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
            # ΓöÇΓöÇ Serve from cache ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
            pair_scores = [
                PairScore(
                    candidate_id=row.candidate_id,
                    project_id=row.project_id,
                    embedding_similarity=row.embedding_similarity,
                    prerequisite_overlap=row.prerequisite_overlap,
                    resume_experience=row.resume_experience,
                    preference_signal=row.preference_signal,
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

        # ΓöÇΓöÇ 4. Compute fresh and persist ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
        known_skills = await self._load_known_skill_names()
        pair_scores = []
        db_rows: list[BatchPairScore] = []

        for candidate in candidates:
            workbook_skills = [cs.skill.name for cs in candidate.skills if cs.skill]
            doc = next(
                (d for d in candidate.documents if d.document_type == "resume"), None
            )
            resume_text = doc.parsed_text if doc and doc.parsed_text else ""
            resume_skills = self._extract_skills_from_resume(resume_text, known_skills)
            candidate_skills = self._merge_skills(workbook_skills, resume_skills)

            for project in projects:
                signals = await self._compute_pair_signals(
                    candidate_name=cast(str, candidate.name),
                    candidate_skills=candidate_skills,
                    resume_text=resume_text,
                    registration_number=cast(str, candidate.registration_number),
                    project=project,
                )
                score = PairScore(
                    candidate_id=cast(int, candidate.id),
                    project_id=cast(int, project.id),
                    embedding_similarity=round(signals.embedding_sim, 4),
                    prerequisite_overlap=round(signals.prereq_overlap.score, 4),
                    resume_experience=round(signals.resume_experience.score, 4),
                    preference_signal=round(signals.preference_signal.score, 4),
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
