import json

import pytest

from app.features.matching.exceptions import LlmEvaluationError
from app.features.matching.llm_client import LLMCompletionResult
from app.features.matching.match_explanation import (
    _normalize_score,
    _parse_llm_evaluation,
    _parse_llm_json,
)


def _sample_llm_payload() -> dict:
    return {
        "technical_readiness": "Ready",
        "growth_potential": "High learnability",
        "interest_alignment": "Strong",
        "explanation": "Good fit",
        "readiness_score": 0.7,
        "growth_potential_score": 0.9,
        "interest_score": 0.65,
        "semantic_fit_score": 0.8,
        "scoring_rationale": "Strong Python base compensates for missing PyTorch",
        "missing_prerequisites": ["PyTorch"],
        "compensating_skills": ["Python", "TensorFlow"],
    }


def test_parse_llm_json_valid():
    result = LLMCompletionResult(
        content=json.dumps(_sample_llm_payload()),
        provider="test",
    )
    data = _parse_llm_json(result)
    assert data["growth_potential_score"] == 0.9


def test_parse_llm_json_rejects_skipped():
    result = LLMCompletionResult(
        content="", provider="test", skipped=True, skip_reason="disabled"
    )
    with pytest.raises(LlmEvaluationError, match="disabled"):
        _parse_llm_json(result)


def test_normalize_score_accepts_percentage():
    assert _normalize_score(85, "test_score") == 0.85


def test_parse_llm_evaluation_keeps_narrative_and_numeric_growth_separate():
    result = LLMCompletionResult(
        content=json.dumps(_sample_llm_payload()),
        provider="openai",
        model="gpt-4o-mini",
    )
    parsed = _parse_llm_evaluation(result)
    assert parsed["growth_potential"] == "High learnability"
    assert parsed["growth_potential_score"] == 0.9
    assert isinstance(parsed["growth_potential"], str)
    assert isinstance(parsed["growth_potential_score"], float)
