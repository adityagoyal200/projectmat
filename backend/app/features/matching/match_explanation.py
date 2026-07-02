import json
import re

from app.features.matching.exceptions import LlmEvaluationError
from app.features.matching.llm_client import (
    LLMCompletionResult,
    generate_chat_completion,
)

_REQUIRED_LLM_FIELDS = (
    "technical_readiness",
    "growth_potential",
    "interest_alignment",
    "explanation",
    "readiness_score",
    "growth_potential_score",
    "interest_score",
    "semantic_fit_score",
    "scoring_rationale",
    "missing_prerequisites",
    "compensating_skills",
)


def _clean_llm_json(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def _parse_llm_json(response: LLMCompletionResult) -> dict:
    if response.skipped:
        raise LlmEvaluationError(
            response.skip_reason or "LLM evaluation was skipped.",
            raw_response=response.content or None,
        )
    if response.error is not None:
        raise LlmEvaluationError(
            f"LLM provider error: {response.error}",
            raw_response=response.content or None,
        )
    if not response.content.strip():
        raise LlmEvaluationError("LLM returned an empty response.", raw_response=None)

    cleaned = _clean_llm_json(response.content)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LlmEvaluationError(
            f"LLM response is not valid JSON: {exc}",
            raw_response=response.content,
        ) from exc

    if not isinstance(data, dict):
        raise LlmEvaluationError(
            "LLM response must be a JSON object.",
            raw_response=response.content,
        )

    missing = [field for field in _REQUIRED_LLM_FIELDS if field not in data]
    if missing:
        raise LlmEvaluationError(
            f"LLM response missing required fields: {', '.join(missing)}",
            raw_response=response.content,
        )

    return data


def _normalize_score(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise LlmEvaluationError(f"{field_name} must be a number, not a boolean.")
    if isinstance(value, int | float):
        score = float(value)
    elif isinstance(value, str):
        match = re.search(r"(\d+(?:\.\d+)?)", value)
        if not match:
            raise LlmEvaluationError(f"Cannot parse {field_name} from: {value!r}")
        score = float(match.group(1))
        if score > 1.0:
            score = score / 100.0
    else:
        raise LlmEvaluationError(f"Invalid {field_name} type: {type(value)}")

    if score > 1.0:
        score = score / 100.0
    if not 0.0 <= score <= 1.0:
        raise LlmEvaluationError(
            f"{field_name} must be between 0.0 and 1.0, got {score}"
        )
    return round(score, 4)


def _build_eval_prompt(
    *,
    perspective: str,
    candidate_name: str,
    candidate_skills: list[str],
    resume_text: str,
    project_title: str,
    project_abstract: str,
    prerequisites: list[str],
    preferences: list[str],
    preliminary_context: str,
) -> str:
    return f"""
Evaluate candidate {candidate_name} for the project "{project_title}" ({perspective}).

CANDIDATE:
- Skills: {", ".join(candidate_skills) or "none"}
- Resume (excerpt): {resume_text[:4000] or "none"}

PROJECT:
- Title: {project_title}
- Abstract: {project_abstract or "none"}
- Prerequisites: {", ".join(prerequisites) or "none"}
- Workbook preferences: {", ".join(preferences) or "none"}

PRELIMINARY SIGNALS (deterministic, already computed):
{preliminary_context}

SCORING RULES:
- readiness_score: ability to start immediately on prerequisites (0.0-1.0)
- growth_potential_score: WEIGHT HEAVILY — can candidate learn missing tools
  given adjacent/foundational skills? High when gaps exist but
  foundation is strong (0.0-1.0)
- interest_score: alignment with preferences, resume topics, project domain (0.0-1.0)
- semantic_fit_score: holistic conceptual alignment with abstract and goals (0.0-1.0)
- Score growth_potential_score HIGHER than readiness_score when missing
  prereqs are learnable from adjacent skills

GUIDELINES FOR GENERATING PARAGRAPHS:
- The "technical_readiness" paragraph MUST explicitly base its analysis on and cite the candidate's developer profile metrics (such as github_score, repository_quality_score, live_app_score, and any specific repository findings) provided in the PRELIMINARY SIGNALS.
- The "growth_potential" paragraph MUST explicitly base its learnability/potential discussion on their coding_profiles_score (from competitive programming platforms like LeetCode/Codeforces) and achievements_score.
- The "interest_alignment" paragraph MUST reflect their actual project history, GitHub repositories, and preferences.

Respond ONLY with valid JSON (no markdown):
{{
  "technical_readiness": "paragraph citing specific skills and gaps",
  "growth_potential": "learnability paragraph (missing prereqs / why)",
  "interest_alignment": "paragraph on interest alignment with evidence",
  "explanation": "2-4 sentence summary for the {perspective}",
  "missing_prerequisites": ["list", "of", "gaps"],
  "compensating_skills": ["adjacent", "skills", "that", "offset", "gaps"],
  "readiness_score": 0.65,
  "growth_potential_score": 0.85,
  "interest_score": 0.70,
  "semantic_fit_score": 0.75,
  "scoring_rationale": "step-by-step numeric justification for all four scores"
}}
"""


def _parse_llm_evaluation(response: LLMCompletionResult) -> dict:
    data = _parse_llm_json(response)
    return {
        "technical_readiness": str(data["technical_readiness"]),
        "growth_potential": str(data["growth_potential"]),
        "interest_alignment": str(data["interest_alignment"]),
        "explanation": str(data["explanation"]),
        "scoring_rationale": str(data["scoring_rationale"]),
        "missing_prerequisites": data.get("missing_prerequisites", []),
        "compensating_skills": data.get("compensating_skills", []),
        "readiness": _normalize_score(data["readiness_score"], "readiness_score"),
        "growth_potential_score": _normalize_score(
            data["growth_potential_score"], "growth_potential_score"
        ),
        "interest": _normalize_score(data["interest_score"], "interest_score"),
        "semantic_fit": _normalize_score(
            data["semantic_fit_score"], "semantic_fit_score"
        ),
        "llm_provider": response.provider,
        "llm_model": response.model,
    }


async def generate_project_match_for_student(
    candidate_name: str,
    candidate_skills: list[str],
    resume_text: str,
    project_title: str,
    project_abstract: str,
    prerequisites: list[str],
    preferences: list[str],
    preliminary_context: str = "",
) -> dict:
    prompt = _build_eval_prompt(
        perspective="student",
        candidate_name=candidate_name,
        candidate_skills=candidate_skills,
        resume_text=resume_text,
        project_title=project_title,
        project_abstract=project_abstract,
        prerequisites=prerequisites,
        preferences=preferences,
        preliminary_context=preliminary_context,
    )
    response = await generate_chat_completion(
        prompt,
        "You are an academic advisor. Reward growth potential when "
        "foundational skills compensate for missing prerequisites. "
        "All scores must be decimals 0.0-1.0.",
    )
    return _parse_llm_evaluation(response)


async def generate_candidate_match_for_mentor(
    candidate_name: str,
    candidate_skills: list[str],
    resume_text: str,
    project_title: str,
    project_abstract: str,
    prerequisites: list[str],
    preferences: list[str],
    preliminary_context: str = "",
) -> dict:
    prompt = _build_eval_prompt(
        perspective="mentor",
        candidate_name=candidate_name,
        candidate_skills=candidate_skills,
        resume_text=resume_text,
        project_title=project_title,
        project_abstract=project_abstract,
        prerequisites=prerequisites,
        preferences=preferences,
        preliminary_context=preliminary_context,
    )
    response = await generate_chat_completion(
        prompt,
        "You are a technical program coordinator. Reward growth potential "
        "when foundational skills compensate for missing prerequisites. "
        "All scores must be decimals 0.0-1.0.",
    )
    return _parse_llm_evaluation(response)
