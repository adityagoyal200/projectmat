import json
from unittest.mock import AsyncMock

import pytest

from app.features.matching import report
from app.features.matching.llm_client import LLMCompletionResult
from app.features.matching.report import (
    _analysis_skeleton,
    build_batch_report_html,
    build_deterministic_why,
    build_report_html,
)


def _sample_analysis() -> dict:
    return {
        "fit_summary": "Solid Python base, gaps in game design.",
        "detailed_assessment": "In-depth assessment prose.",
        "strengths": ["Strong Python"],
        "gaps": ["No game-dev experience"],
        "improvement_plan": ["Build a small game"],
        "learning_roadmap": ["Weeks 1-2: basics"],
        "recommended_resources": ["Godot docs"],
        "project_approach": ["Start with the input loop"],
        "risks": ["Time management"],
    }


def _sample_factors() -> list[dict]:
    return [
        {
            "label": "Topic match",
            "meaning": "How closely aligned",
            "score": 0.57,
            "detail": "cosine 0.57",
        },
        {
            "label": "Required skills",
            "meaning": "must-haves held",
            "score": 0.75,
            "detail": "",
        },
    ]


def _context(analysis: dict | None = None) -> dict:
    return {
        "candidate_name": "Sourit Mitra",
        "project_title": "Adaptive Games",
        "final_score": 0.46,
        "factors": _sample_factors(),
        "analysis": analysis or _sample_analysis(),
        "scoring_version": "3.1.0",
    }


# --- build_report_html -----------------------------------------------------


def test_build_report_html_contains_all_sections():
    html = build_report_html(_context())
    # Substrings chosen to avoid the escaped "&amp;" in some headings.
    for heading in [
        "In-depth assessment",
        "Strengths for this project",
        "Gaps",
        "How to improve",
        "Suggested learning roadmap",
        "Recommended resources",
        "How they could approach this project",
        "Risks",
        "Factor breakdown",
    ]:
        assert heading in html, f"missing section: {heading}"
    assert "Sourit Mitra" in html
    assert ">46<" in html  # rounded match percentage in the header


def test_build_report_html_escapes_user_text():
    analysis = _sample_analysis()
    analysis["strengths"] = ["<script>alert('x')</script>"]
    html = build_report_html(_context(analysis) | {"candidate_name": "A & B <hax>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "A &amp; B" in html
    assert "<hax>" not in html


# --- batch selection report ------------------------------------------------


def _batch_context() -> dict:
    factors_hi = [
        {"label": "Topic match", "score": 0.72},
        {"label": "Required skills", "score": 0.6},
        {"label": "Relevant experience", "score": 0.4},
        {"label": "GitHub profile", "score": 0.1},
        {"label": "Coding profiles", "score": 0.05},
        {"label": "Achievements", "score": 0.0},
    ]
    return {
        "batch_id": 7,
        "generated_at": "2026-07-07 10:00 UTC",
        "scoring_version": "3.1.0",
        "summary": {
            "total_students": 2,
            "total_projects": 1,
            "with_selection": 1,
        },
        "projects": [
            {
                "project_id": 1,
                "project_title": "Adaptive Games",
                "mentor_name": "Dr. Byte",
                "mentor_email": "byte@example.com",
                "selected_students": [
                    {"name": "Ada Lovelace", "registration_number": "MDS-1"}
                ],
                "recommended_students": [
                    {
                        "rank": 1,
                        "student_name": "Ada Lovelace",
                        "registration_number": "MDS-1",
                        "score": 0.66,
                        "is_selected": True,
                        "factors": factors_hi,
                        "why": build_deterministic_why(factors_hi),
                    },
                    {
                        "rank": 2,
                        "student_name": "Alan <Turing>",
                        "registration_number": "MDS-2",
                        "score": 0.35,
                        "is_selected": False,
                        "factors": factors_hi,
                        "why": build_deterministic_why(factors_hi),
                    },
                ],
            }
        ],
    }


def test_build_batch_report_html_has_summary_and_students():
    html = build_batch_report_html(_batch_context())
    assert "Batch #7" in html
    assert "Ada Lovelace" in html
    assert "MDS-1" in html
    assert "Adaptive Games" in html
    assert "◆ workbook selected" in html  # the selected-project marker
    assert "Workbook Selections:" in html


def test_build_batch_report_html_escapes_user_text():
    html = build_batch_report_html(_batch_context())
    assert "<Turing>" not in html
    assert "&lt;Turing&gt;" in html


def test_build_deterministic_why_names_strong_and_weak():
    why = build_deterministic_why(
        [
            {"label": "Topic match", "score": 0.72},
            {"label": "Required skills", "score": 0.6},
            {"label": "Achievements", "score": 0.0},
        ]
    )
    assert "topic match (72%)" in why
    assert "achievements (0%)" in why


# --- generate_improvement_analysis (retry semantics) -----------------------

_ANALYSIS_KWARGS = {
    "candidate_name": "Sourit",
    "resume_text": "Python developer.",
    "project_title": "Adaptive Games",
    "project_abstract": "Games vs the attention economy.",
    "prerequisites": ["Python"],
    "factor_summary": "- Topic match: 57%",
}


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch):
    """Make the backoff instantaneous so retry tests run fast."""
    monkeypatch.setattr(report, "_ANALYSIS_RETRY_BASE_DELAY", 0)


@pytest.mark.anyio
async def test_generate_improvement_analysis_success(monkeypatch):
    mock = AsyncMock(
        return_value=LLMCompletionResult(
            content=json.dumps(_sample_analysis()),
            provider="openai",
            model="gpt-4o-mini",
        )
    )
    monkeypatch.setattr(report, "generate_chat_completion", mock)

    out = await report.generate_improvement_analysis(**_ANALYSIS_KWARGS)

    assert out["fit_summary"].startswith("Solid Python")
    assert out["strengths"] == ["Strong Python"]
    assert mock.call_count == 1


@pytest.mark.anyio
async def test_generate_improvement_analysis_skips_without_retry_when_disabled(
    monkeypatch,
):
    mock = AsyncMock(
        return_value=LLMCompletionResult(
            content="", provider="openai", skipped=True, skip_reason="disabled"
        )
    )
    monkeypatch.setattr(report, "generate_chat_completion", mock)

    out = await report.generate_improvement_analysis(**_ANALYSIS_KWARGS)

    assert out == _analysis_skeleton()
    assert mock.call_count == 1  # a skipped (disabled) LLM is not retried


@pytest.mark.anyio
async def test_generate_improvement_analysis_retries_then_succeeds(monkeypatch):
    mock = AsyncMock(
        side_effect=[
            LLMCompletionResult(content="", provider="openai", error="429 rate limit"),
            LLMCompletionResult(
                content=json.dumps(_sample_analysis()),
                provider="openai",
                model="gpt-4o-mini",
            ),
        ]
    )
    monkeypatch.setattr(report, "generate_chat_completion", mock)

    out = await report.generate_improvement_analysis(**_ANALYSIS_KWARGS)

    assert out["fit_summary"].startswith("Solid Python")
    assert mock.call_count == 2


@pytest.mark.anyio
async def test_generate_improvement_analysis_falls_back_after_exhaustion(monkeypatch):
    mock = AsyncMock(
        return_value=LLMCompletionResult(content="not json at all", provider="openai")
    )
    monkeypatch.setattr(report, "generate_chat_completion", mock)

    out = await report.generate_improvement_analysis(**_ANALYSIS_KWARGS)

    assert out == _analysis_skeleton()
    assert mock.call_count == report._ANALYSIS_MAX_ATTEMPTS
