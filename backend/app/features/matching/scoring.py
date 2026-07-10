"""Hybrid scoring engine.

Combines tiered prerequisites, experience-based resume signals,
LLM sub-scores, and embeddings.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.features.matching.skill_aliases import prereq_match_credit

logger = logging.getLogger(__name__)

EXPERIENCE_SECTION_PATTERN = re.compile(
    r"(experience|projects?|research|internship|work history|employment|publications?)",
    re.IGNORECASE,
)
PROJECT_INDICATORS = re.compile(
    r"\b(built|developed|designed|implemented|led|created|deployed|published)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PrereqMatchDetail:
    prerequisite: str
    credit: float
    tier: str
    matched_skill: str | None


@dataclass(frozen=True)
class PrerequisiteOverlapResult:
    score: float
    matched_details: list[PrereqMatchDetail]
    total_prerequisites: int
    detail: str


@dataclass(frozen=True)
class ResumeExperienceResult:
    score: float
    experience_sections_found: int
    project_mentions: int
    domain_keyword_hits: list[str]
    detail: str


@dataclass(frozen=True)
class PreferenceSignalResult:
    score: float
    matched_preference: str | None
    detail: str


@dataclass(frozen=True)
class DeveloperProfileScoreResult:
    github_score: float
    coding_profiles_score: float
    achievements_score: float
    repository_quality_score: float
    live_app_score: float
    detail: str
    github_detail: str = ""
    coding_profiles_detail: str = ""
    achievements_detail: str = ""
    # Per-repository review summaries (from the agy/repository-evaluation
    # pipeline), surfaced so the UI can show whether repos were actually cloned
    # and reviewed. Empty when that pipeline was never run for the candidate.
    repository_evaluations: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class LlmScoreComponents:
    readiness: float
    growth_potential: float
    interest: float
    semantic_fit: float


@dataclass(frozen=True)
class HybridScoreResult:
    final_score: float
    embedding_similarity: float
    readiness: float
    growth_potential: float
    interest: float
    github_score: float
    coding_profiles_score: float
    achievements_score: float
    repository_quality_score: float
    live_app_score: float
    llm_fit_score: float
    prerequisite_overlap: float
    resume_experience: float
    preference_signal: float
    weights: dict[str, float]
    weighted_contributions: dict[str, float]
    formula: str
    prerequisite_detail: str
    resume_experience_detail: str
    developer_profile_detail: str
    github_detail: str
    coding_profiles_detail: str
    achievements_detail: str
    preference_detail: str
    embedding_detail: str
    scoring_version: str
    llm_evaluated: bool


def compute_prerequisite_overlap(
    candidate_skills: list[str],
    prerequisites: list[str],
) -> PrerequisiteOverlapResult:
    # Defensive: strip whitespace from inputs to handle dirty data
    candidate_skills = [s.strip() for s in candidate_skills if s.strip()]
    prerequisites = [p.strip() for p in prerequisites if p.strip()]

    if not prerequisites:
        return PrerequisiteOverlapResult(
            score=0.0,
            matched_details=[],
            total_prerequisites=0,
            detail="No prerequisites listed; overlap score is 0.0.",
        )

    details: list[PrereqMatchDetail] = []
    total_credit = 0.0
    for prereq in prerequisites:
        credit, tier, matched = prereq_match_credit(candidate_skills, prereq)
        total_credit += credit
        details.append(
            PrereqMatchDetail(
                prerequisite=prereq,
                credit=credit,
                tier=tier,
                matched_skill=matched,
            )
        )

    score = total_credit / len(prerequisites)
    exact = [d for d in details if d.tier in ("exact", "alias")]
    family = [d for d in details if d.tier == "family"]
    missing = [d for d in details if d.tier == "missing"]

    matched_str = (
        ", ".join(
            f"{d.prerequisite}←{d.matched_skill}({d.tier})"
            for d in details
            if d.credit > 0
        )
        or "none"
    )
    detail = (
        f"Tiered prerequisite overlap: {score:.4f} "
        f"({len(exact)} exact/alias @1.0, "
        f"{len(family)} adjacent @0.5, "
        f"{len(missing)} missing @0.0). "
        f"Matched: [{matched_str}]. "
        f"Gaps: [{', '.join(d.prerequisite for d in missing) or 'none'}]."
    )
    return PrerequisiteOverlapResult(
        score=round(score, 4),
        matched_details=details,
        total_prerequisites=len(prerequisites),
        detail=detail,
    )


def compute_resume_experience(
    resume_text: str,
    project_abstract: str,
    prerequisites: list[str],
) -> ResumeExperienceResult:
    """Score relevant experience depth — not duplicate prereq keyword matching."""
    text = resume_text.strip()
    if not text:
        return ResumeExperienceResult(
            score=0.0,
            experience_sections_found=0,
            project_mentions=0,
            domain_keyword_hits=[],
            detail="No resume text; experience score is 0.0.",
        )

    sections = len(EXPERIENCE_SECTION_PATTERN.findall(text))
    project_mentions = len(PROJECT_INDICATORS.findall(text))

    domain_keywords: list[str] = []
    abstract_tokens = set(re.findall(r"[a-zA-Z]{3,}", (project_abstract or "").lower()))
    prereq_lower_set = {p.lower() for p in prerequisites}

    # Collect abstract tokens (excluding prereqs) that appear in the resume
    for token in list(abstract_tokens)[:15]:
        if len(token) < 4:
            continue
        if (
            re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE)
            and token not in prereq_lower_set
        ):
            domain_keywords.append(token)

    # Also credit prereqs that appear in both the project abstract and the resume
    for prereq in prerequisites:
        if prereq.lower() in abstract_tokens and re.search(
            rf"\b{re.escape(prereq)}\b", text, re.IGNORECASE
        ):
            domain_keywords.append(prereq)

    domain_keywords = list(dict.fromkeys(domain_keywords))[:8]

    section_score = min(sections / 3.0, 1.0) * 0.35
    project_score = min(project_mentions / 5.0, 1.0) * 0.35
    domain_score = min(len(domain_keywords) / 4.0, 1.0) * 0.30
    score = round(min(section_score + project_score + domain_score, 1.0), 4)

    detail = (
        f"Resume experience score: {score:.4f}. "
        f"Experience sections: {sections}, action verbs: {project_mentions}, "
        "domain keywords from project context: "
        f"[{', '.join(domain_keywords) or 'none'}]."
    )
    return ResumeExperienceResult(
        score=score,
        experience_sections_found=sections,
        project_mentions=project_mentions,
        domain_keyword_hits=domain_keywords,
        detail=detail,
    )


def compute_preference_signal(
    registration_number: str,
    preferences: list[tuple[str, str]],
) -> PreferenceSignalResult:
    reg = registration_number.upper()
    rank_scores = {
        "preference_1": 1.0,
        "preference_2": 0.67,
        "preference_3": 0.33,
        "selected_students": 1.0,
    }

    best_score = 0.0
    best_match: str | None = None
    for pref_type, pref_value in preferences:
        if pref_value.upper() == reg:
            signal = rank_scores.get(pref_type, 0.5)
            if signal > best_score:
                best_score = signal
                best_match = pref_type

    if best_match:
        detail = (
            f"Workbook signal '{best_match}' (={best_score:.2f}); "
            "informational only, not in final_score."
        )
    else:
        detail = (
            "No preference/selection signal for this pairing " "(informational only)."
        )

    return PreferenceSignalResult(
        score=round(best_score, 4),
        matched_preference=best_match,
        detail=detail,
    )


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric(source: Any, key: str, default: float = 0.0) -> float:
    if isinstance(source, dict):
        return _as_float(source.get(key), default)
    return _as_float(getattr(source, key, default), default)


def _bounded(value: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return min(max(value / target, 0.0), 1.0)


def _average_scores(rows: list[Any] | None) -> float:
    if not rows:
        return 0.0
    scores = [_metric(row, "score") for row in rows]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def _attr(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _summarize_repository_evaluations(rows: list[Any] | None) -> list[dict]:
    """Compact, serializable summaries of each repository review so the UI can
    show whether repos were actually cloned and reviewed. Handles both ORM rows
    and plain dicts."""
    if not rows:
        return []
    summaries: list[dict] = []
    for row in rows:
        logic = _attr(row, "github_logic_score")
        findings = _attr(row, "findings") or []
        summaries.append(
            {
                "repository_name": _attr(row, "repository_name"),
                "repository_url": _attr(row, "repository_url") or "",
                "status": _attr(row, "status") or "unknown",
                "score": round(_metric(row, "score"), 4),
                "logic_score": round(float(logic), 4) if logic is not None else None,
                "findings_count": len(findings) if isinstance(findings, list) else 0,
                "source": _attr(row, "source"),
            }
        )
    return summaries


def _achievement_count(achievements: dict | list | str | None) -> int:
    if not achievements:
        return 0
    if isinstance(achievements, list):
        return len(achievements)
    if isinstance(achievements, str):
        return 1 if achievements.strip() else 0
    if isinstance(achievements, dict):
        if "items" in achievements and isinstance(achievements["items"], list):
            return len(achievements["items"])
        if "count" in achievements:
            return int(_as_float(achievements["count"]))
        return sum(1 for value in achievements.values() if value)
    return 0


def _calculate_achievement_heuristics(achievements: dict | list | str | None) -> float:
    if not achievements:
        return 0.0
    text = ""
    if isinstance(achievements, str):
        text = achievements.lower()
    elif isinstance(achievements, list):
        text = " ".join([str(x) for x in achievements]).lower()
    elif isinstance(achievements, dict):
        text = json.dumps(achievements).lower()

    bonus = 0.0
    # Tier 1 keywords (High impact: ICPC, finalist, winner, gold medal)
    t1_keywords = [
        "icpc",
        "acm-icpc",
        "finalist",
        "winner",
        "gold medal",
        "first place",
        "scholar",
    ]
    for kw in t1_keywords:
        if kw in text:
            bonus += 0.25

    # Tier 2 keywords (hackathon, runner up, rank)
    t2_keywords = ["hackathon", "runner up", "second place", "third place", "rank"]
    for kw in t2_keywords:
        if kw in text:
            bonus += 0.10

    return min(bonus, 0.5)


def compute_developer_profile_score(
    *,
    github_username: str | None = None,
    github_metrics: dict | None = None,
    github_repositories: list[str] | None = None,
    leetcode_metrics: dict | None = None,
    codeforces_metrics: dict | None = None,
    kaggle_metrics: dict | None = None,
    scholar_metrics: dict | None = None,
    achievements: dict | list | str | None = None,
    repository_evaluations: list[Any] | None = None,
    live_app_evaluations: list[Any] | None = None,
) -> DeveloperProfileScoreResult:
    """Score deterministic Phase 6 profile signals on a 0.0-1.0 scale."""
    github_metrics = github_metrics or {}
    github_repositories = github_repositories or []
    leetcode_metrics = leetcode_metrics or {}
    codeforces_metrics = codeforces_metrics or {}
    kaggle_metrics = kaggle_metrics or {}
    scholar_metrics = scholar_metrics or {}

    repository_quality = _average_scores(repository_evaluations)
    live_app = _average_scores(live_app_evaluations)

    # Average logical code review quality (Agent 2)
    logic_scores = []
    if repository_evaluations:
        for row in repository_evaluations:
            l_score = _metric(row, "github_logic_score")
            if l_score is not None:
                logic_scores.append(l_score)
    repository_logic = (
        round(sum(logic_scores) / len(logic_scores), 4) if logic_scores else 0.0
    )

    public_repos = max(
        _metric(github_metrics, "public_repos"),
        _metric(github_metrics, "repo_count"),
    )
    total_stars = max(
        _metric(github_metrics, "total_stars"),
        _metric(github_metrics, "stars"),
    )
    followers = _metric(github_metrics, "followers")
    recent_activity = max(
        _metric(github_metrics, "recent_activity_count"),
        _metric(github_metrics, "recent_commits"),
        _metric(github_metrics, "contributions"),
    )

    github_base = (
        0.10 * _bounded(public_repos, 12)
        + 0.10 * _bounded(total_stars, 50)
        + 0.05 * _bounded(followers, 25)
        + 0.10 * _bounded(recent_activity, 30)
        + 0.10 * _bounded(len(github_repositories), 3)
        + 0.15 * repository_quality
        + 0.15 * repository_logic
        + 0.05 * live_app
        + 0.10 * _bounded(github_metrics.get("pr_total_count") or 0, 10)
        + 0.10 * _bounded(github_metrics.get("os_contribution_count") or 0, 3)
    )
    github_score = round(min(github_base, 1.0), 4)

    leetcode_solved = max(
        _metric(leetcode_metrics, "total_solved"),
        _metric(leetcode_metrics, "solved_total"),
        _metric(leetcode_metrics, "problems_solved"),
    )
    # Solve quality (difficulty levels multiplier)
    easy = _metric(leetcode_metrics, "easy_solved")
    medium = _metric(leetcode_metrics, "medium_solved")
    hard = _metric(leetcode_metrics, "hard_solved")
    if easy > 0 or medium > 0 or hard > 0:
        leetcode_difficulty = easy * 1.0 + medium * 2.0 + hard * 3.0
        leetcode_solved_metric = _bounded(leetcode_difficulty, 450.0)
    else:
        leetcode_solved_metric = _bounded(leetcode_solved, 300.0)

    leetcode_contests = max(
        _metric(leetcode_metrics, "contest_count"),
        _metric(leetcode_metrics, "contests"),
    )
    codeforces_rating = max(
        _metric(codeforces_metrics, "max_rating"),
        _metric(codeforces_metrics, "rating"),
    )
    codeforces_solved = max(
        _metric(codeforces_metrics, "problems_solved"),
        _metric(codeforces_metrics, "solved_total"),
    )
    kaggle_medals = max(
        _metric(kaggle_metrics, "medals"),
        _metric(kaggle_metrics, "competition_medals"),
    )
    coding_score = round(
        min(
            0.35 * leetcode_solved_metric
            + 0.10 * _bounded(leetcode_contests, 20)
            + 0.30 * _bounded(codeforces_rating, 1800)
            + 0.15 * _bounded(codeforces_solved, 250)
            + 0.10 * _bounded(kaggle_medals, 5),
            1.0,
        ),
        4,
    )

    achievement_items = _achievement_count(achievements)
    achievement_bonus = _calculate_achievement_heuristics(achievements)
    citations = _metric(scholar_metrics, "citations")
    publications = max(
        _metric(scholar_metrics, "publications"),
        _metric(scholar_metrics, "publication_count"),
    )
    h_index = _metric(scholar_metrics, "h_index")

    achievements_score = round(
        min(
            0.35 * _bounded(achievement_items, 5)
            + achievement_bonus
            + 0.20 * _bounded(citations, 100)
            + 0.15 * _bounded(publications, 5)
            + 0.15 * _bounded(h_index, 10),
            1.0,
        ),
        4,
    )

    detail = (
        "Phase 6 deterministic profile scores: "
        f"github={github_score:.4f} "
        f"(repos={public_repos:.0f}, stars={total_stars:.0f}, "
        f"repository_quality={repository_quality:.4f}, live_app={live_app:.4f}); "
        f"coding_profiles={coding_score:.4f} "
        f"(leetcode_solved={leetcode_solved:.0f}, "
        f"codeforces_rating={codeforces_rating:.0f}); "
        f"achievements={achievements_score:.4f} "
        f"(items={achievement_items}, citations={citations:.0f})."
    )

    if github_score > 0:
        # A score was earned from repos, metrics, or repository evaluations —
        # describe it even when the profile username itself was never captured.
        github_detail = f"Score derived from public repos ({public_repos:.0f}), stars ({total_stars:.0f}), repository quality ({repository_quality:.4f}), and live app ({live_app:.4f})."
    elif not github_username and not github_repositories:
        github_detail = "GitHub link was not provided."
    else:
        github_detail = "GitHub link provided, but no public repositories, stars, or recent activity found."

    if coding_score == 0:
        coding_detail = "No LeetCode, Codeforces, or Kaggle activity found."
    else:
        coding_detail = f"Score derived from LeetCode solved ({leetcode_solved:.0f}), Codeforces rating ({codeforces_rating:.0f}), and Kaggle medals ({kaggle_medals:.0f})."

    if achievements_score == 0:
        achievements_detail = (
            "No notable achievements, citations, or publications found."
        )
    else:
        achievements_detail = f"Score derived from achievements ({achievement_items}), citations ({citations:.0f}), and publications ({publications:.0f})."

    logger.debug(
        f"\n--- [SCORING ENGINE] Calculating Developer Profile Score for Candidate ---\n"
        f"  GitHub Username: {github_username or 'None'}\n"
        f"  GitHub Profile metrics: repos={public_repos:.0f}, stars={total_stars:.0f}, followers={followers:.0f}\n"
        f"  Git Clone & Static Code Review Score: {repository_quality:.4f}\n"
        f"  Logic Code Quality Score: {repository_logic:.4f}\n"
        f"  Live App Crawl Heuristic Score: {live_app:.4f}\n"
        f"  GitHub PR count: {github_metrics.get('pr_total_count') or 0}, OS Contributions: {github_metrics.get('os_contribution_count') or 0}\n"
        f"  --> Final github_score: {github_score:.4f}\n"
        f"  LeetCode solved: {leetcode_solved:.0f}, Contests: {leetcode_contests:.0f}\n"
        f"  Codeforces rating: {codeforces_rating:.0f}, Solved: {codeforces_solved:.0f}\n"
        f"  Kaggle medals: {kaggle_medals:.0f}\n"
        f"  --> Final coding_score: {coding_score:.4f}\n"
        f"  Achievements items: {achievement_items}, citations={citations:.0f}, publications={publications:.0f}\n"
        f"  --> Final achievements_score: {achievements_score:.4f}\n"
        f"---------------------------------------------------------------------------"
    )

    return DeveloperProfileScoreResult(
        github_score=github_score,
        coding_profiles_score=coding_score,
        achievements_score=achievements_score,
        repository_quality_score=repository_quality,
        live_app_score=live_app,
        detail=detail,
        github_detail=github_detail,
        coding_profiles_detail=coding_detail,
        achievements_detail=achievements_detail,
        repository_evaluations=_summarize_repository_evaluations(
            repository_evaluations
        ),
    )


def compute_preliminary_score(
    *,
    embedding_similarity: float,
    prerequisite_overlap: PrerequisiteOverlapResult,
    resume_experience: ResumeExperienceResult,
    developer_profile: DeveloperProfileScoreResult | None = None,
) -> float:
    """Stage-1 ranker: deterministic signals only (no LLM)."""
    profile = developer_profile or compute_developer_profile_score()
    w_emb = settings.SCORE_WEIGHT_EMBEDDING_SIMILARITY
    w_prereq = settings.SCORE_WEIGHT_PREREQUISITE_OVERLAP
    w_resume = settings.SCORE_WEIGHT_RESUME_EXPERIENCE
    w_github = settings.SCORE_WEIGHT_GITHUB
    w_coding = settings.SCORE_WEIGHT_CODING_PROFILES
    w_achievements = settings.SCORE_WEIGHT_ACHIEVEMENTS
    total = w_emb + w_prereq + w_resume + w_github + w_coding + w_achievements
    if total <= 0:
        return 0.0
    score = (
        (w_emb / total) * embedding_similarity
        + (w_prereq / total) * prerequisite_overlap.score
        + (w_resume / total) * resume_experience.score
        + (w_github / total) * profile.github_score
        + (w_coding / total) * profile.coding_profiles_score
        + (w_achievements / total) * profile.achievements_score
    )
    return round(min(max(score, 0.0), 1.0), 4)


def compute_hybrid_final_score(
    *,
    embedding_similarity: float,
    embedding_detail: str,
    prerequisite_overlap: PrerequisiteOverlapResult,
    resume_experience: ResumeExperienceResult,
    developer_profile: DeveloperProfileScoreResult | None = None,
    preference_signal: PreferenceSignalResult,
    llm_scores: LlmScoreComponents | None,
) -> HybridScoreResult:
    profile = developer_profile or compute_developer_profile_score()
    weights = {
        "embedding_similarity": settings.SCORE_WEIGHT_EMBEDDING_SIMILARITY,
        "prerequisite_overlap": settings.SCORE_WEIGHT_PREREQUISITE_OVERLAP,
        "resume_experience": settings.SCORE_WEIGHT_RESUME_EXPERIENCE,
        "github": settings.SCORE_WEIGHT_GITHUB,
        "coding_profiles": settings.SCORE_WEIGHT_CODING_PROFILES,
        "achievements": settings.SCORE_WEIGHT_ACHIEVEMENTS,
        "llm_fit": settings.SCORE_WEIGHT_LLM_FIT,
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Scoring weights must sum to a positive value.")

    normalized = {k: v / total_weight for k, v in weights.items()}
    llm_evaluated = llm_scores is not None

    readiness = llm_scores.readiness if llm_scores else 0.0
    growth = llm_scores.growth_potential if llm_scores else 0.0
    interest = llm_scores.interest if llm_scores else 0.0
    semantic_fit = llm_scores.semantic_fit if llm_scores else 0.0
    llm_fit_score = round(
        (readiness + growth + interest + semantic_fit) / 4.0 if llm_scores else 0.0,
        4,
    )

    contributions = {
        "embedding_similarity": round(
            normalized["embedding_similarity"] * embedding_similarity, 4
        ),
        "prerequisite_overlap": round(
            normalized["prerequisite_overlap"] * prerequisite_overlap.score, 4
        ),
        "resume_experience": round(
            normalized["resume_experience"] * resume_experience.score, 4
        ),
        "github": round(normalized["github"] * profile.github_score, 4),
        "coding_profiles": round(
            normalized["coding_profiles"] * profile.coding_profiles_score, 4
        ),
        "achievements": round(
            normalized["achievements"] * profile.achievements_score, 4
        ),
        "llm_fit": round(normalized["llm_fit"] * llm_fit_score, 4),
    }
    final_score = round(sum(contributions.values()), 4)
    final_score = min(max(final_score, 0.0), 1.0)

    llm_note = (
        "full LLM evaluation" if llm_evaluated else "preliminary only (outside top-K)"
    )
    w = normalized
    emb_sim = embedding_similarity
    pr_sc = prerequisite_overlap.score
    res_sc = resume_experience.score
    pref_sc = preference_signal.score
    formula = (
        f"final_score={final_score:.4f} [{llm_note}]. "
        f"embedding({w['embedding_similarity']:.2f}*{emb_sim:.4f}) + "
        f"prereq({w['prerequisite_overlap']:.2f}*{pr_sc:.4f}) + "
        f"resume_exp({w['resume_experience']:.2f}*{res_sc:.4f}). "
        f"github({w['github']:.2f}*{profile.github_score:.4f}) + "
        f"coding({w['coding_profiles']:.2f}*"
        f"{profile.coding_profiles_score:.4f}) + "
        f"achievements({w['achievements']:.2f}*"
        f"{profile.achievements_score:.4f}) + "
        f"llm_fit({w['llm_fit']:.2f}*{llm_fit_score:.4f}). "
        f"preference_signal={pref_sc:.4f} excluded. "
        f"v{settings.SCORING_VERSION}"
    )

    return HybridScoreResult(
        final_score=final_score,
        embedding_similarity=round(embedding_similarity, 4),
        readiness=round(readiness, 4),
        growth_potential=round(growth, 4),
        interest=round(interest, 4),
        github_score=profile.github_score,
        coding_profiles_score=profile.coding_profiles_score,
        achievements_score=profile.achievements_score,
        repository_quality_score=profile.repository_quality_score,
        live_app_score=profile.live_app_score,
        llm_fit_score=llm_fit_score,
        prerequisite_overlap=prerequisite_overlap.score,
        resume_experience=resume_experience.score,
        preference_signal=preference_signal.score,
        weights=normalized,
        weighted_contributions=contributions,
        formula=formula,
        prerequisite_detail=prerequisite_overlap.detail,
        resume_experience_detail=resume_experience.detail,
        developer_profile_detail=profile.detail,
        github_detail=profile.github_detail,
        coding_profiles_detail=profile.coding_profiles_detail,
        achievements_detail=profile.achievements_detail,
        preference_detail=preference_signal.detail,
        embedding_detail=embedding_detail,
        scoring_version=settings.SCORING_VERSION,
        llm_evaluated=llm_evaluated,
    )
