"""Hybrid scoring engine.

Combines tiered prerequisites, experience-based resume signals,
LLM sub-scores, and embeddings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings
from app.features.matching.skill_aliases import prereq_match_credit

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
    prerequisite_overlap: float
    resume_experience: float
    preference_signal: float
    weights: dict[str, float]
    weighted_contributions: dict[str, float]
    formula: str
    prerequisite_detail: str
    resume_experience_detail: str
    preference_detail: str
    embedding_detail: str
    scoring_version: str
    llm_evaluated: bool


def compute_prerequisite_overlap(
    candidate_skills: list[str],
    prerequisites: list[str],
) -> PrerequisiteOverlapResult:
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
    for prereq in prerequisites:
        if re.search(rf"\b{re.escape(prereq)}\b", text, re.IGNORECASE):
            continue  # skip prereq tokens — overlap handles those
        if prereq.lower() in abstract_tokens and re.search(
            rf"\b{re.escape(prereq)}\b", text, re.IGNORECASE
        ):
            domain_keywords.append(prereq)

    for token in list(abstract_tokens)[:15]:
        if len(token) < 4:
            continue
        if (
            re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE)
            and token not in prereq_lower_set
        ):
            domain_keywords.append(token)

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


def compute_preliminary_score(
    *,
    embedding_similarity: float,
    prerequisite_overlap: PrerequisiteOverlapResult,
    resume_experience: ResumeExperienceResult,
) -> float:
    """Stage-1 ranker: deterministic signals only (no LLM)."""
    w_emb = settings.SCORE_WEIGHT_EMBEDDING_SIMILARITY
    w_prereq = settings.SCORE_WEIGHT_PREREQUISITE_OVERLAP
    w_resume = settings.SCORE_WEIGHT_RESUME_EXPERIENCE
    total = w_emb + w_prereq + w_resume
    if total <= 0:
        return 0.0
    score = (
        (w_emb / total) * embedding_similarity
        + (w_prereq / total) * prerequisite_overlap.score
        + (w_resume / total) * resume_experience.score
    )
    return round(min(max(score, 0.0), 1.0), 4)


def compute_hybrid_final_score(
    *,
    embedding_similarity: float,
    embedding_detail: str,
    prerequisite_overlap: PrerequisiteOverlapResult,
    resume_experience: ResumeExperienceResult,
    preference_signal: PreferenceSignalResult,
    llm_scores: LlmScoreComponents | None,
) -> HybridScoreResult:
    weights = {
        "embedding_similarity": settings.SCORE_WEIGHT_EMBEDDING_SIMILARITY,
        "readiness": settings.SCORE_WEIGHT_READINESS,
        "growth_potential": settings.SCORE_WEIGHT_GROWTH_POTENTIAL,
        "interest": settings.SCORE_WEIGHT_INTEREST,
        "prerequisite_overlap": settings.SCORE_WEIGHT_PREREQUISITE_OVERLAP,
        "resume_experience": settings.SCORE_WEIGHT_RESUME_EXPERIENCE,
    }
    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Scoring weights must sum to a positive value.")

    normalized = {k: v / total_weight for k, v in weights.items()}
    llm_evaluated = llm_scores is not None

    readiness = llm_scores.readiness if llm_scores else 0.0
    growth = llm_scores.growth_potential if llm_scores else 0.0
    interest = llm_scores.interest if llm_scores else 0.0

    # Blend LLM semantic_fit into embedding (60% embed, 40% LLM) when LLM ran
    if llm_scores:
        blended_embedding = round(
            0.6 * embedding_similarity + 0.4 * llm_scores.semantic_fit, 4
        )
    else:
        blended_embedding = embedding_similarity

    contributions = {
        "embedding_similarity": round(
            normalized["embedding_similarity"] * blended_embedding, 4
        ),
        "readiness": round(normalized["readiness"] * readiness, 4),
        "growth_potential": round(normalized["growth_potential"] * growth, 4),
        "interest": round(normalized["interest"] * interest, 4),
        "prerequisite_overlap": round(
            normalized["prerequisite_overlap"] * prerequisite_overlap.score, 4
        ),
        "resume_experience": round(
            normalized["resume_experience"] * resume_experience.score, 4
        ),
    }
    final_score = round(sum(contributions.values()), 4)
    final_score = min(max(final_score, 0.0), 1.0)

    llm_note = (
        "full LLM evaluation" if llm_evaluated else "preliminary only (outside top-K)"
    )
    w = normalized
    emb_sim = blended_embedding
    pr_sc = prerequisite_overlap.score
    res_sc = resume_experience.score
    pref_sc = preference_signal.score
    formula = (
        f"final_score={final_score:.4f} [{llm_note}]. "
        f"embedding({w['embedding_similarity']:.2f}*{emb_sim:.4f}) + "
        f"readiness({w['readiness']:.2f}*{readiness:.4f}) + "
        f"growth({w['growth_potential']:.2f}*{growth:.4f}) + "
        f"interest({w['interest']:.2f}*{interest:.4f}) + "
        f"prereq({w['prerequisite_overlap']:.2f}*{pr_sc:.4f}) + "
        f"resume_exp({w['resume_experience']:.2f}*{res_sc:.4f}). "
        f"preference_signal={pref_sc:.4f} excluded. "
        f"v{settings.SCORING_VERSION}"
    )

    return HybridScoreResult(
        final_score=final_score,
        embedding_similarity=round(blended_embedding, 4),
        readiness=round(readiness, 4),
        growth_potential=round(growth, 4),
        interest=round(interest, 4),
        prerequisite_overlap=prerequisite_overlap.score,
        resume_experience=resume_experience.score,
        preference_signal=preference_signal.score,
        weights=normalized,
        weighted_contributions=contributions,
        formula=formula,
        prerequisite_detail=prerequisite_overlap.detail,
        resume_experience_detail=resume_experience.detail,
        preference_detail=preference_signal.detail,
        embedding_detail=embedding_detail,
        scoring_version=settings.SCORING_VERSION,
        llm_evaluated=llm_evaluated,
    )
