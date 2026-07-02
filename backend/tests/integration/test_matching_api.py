from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.features.matching.llm_client import LLMCompletionResult


@pytest.mark.anyio
async def test_get_student_recommendations_not_found(client: AsyncClient):
    response = await client.get("/api/matching/student-recommendations/NONEXISTENT")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_project_recommendations_not_found(client: AsyncClient):
    response = await client.get("/api/matching/project-recommendations/999")
    assert response.status_code == 404


@pytest.mark.anyio
@patch(
    "app.features.matching.match_explanation.generate_chat_completion",
    new_callable=AsyncMock,
)
@patch("app.features.matching.service.parse_pdf_bytes")
async def test_recommend_projects_for_new_student(
    mock_parse, mock_gen, client: AsyncClient, mock_db
):
    from unittest.mock import MagicMock

    from app.features.candidates.models import Candidate

    # Create a dummy candidate to be returned by database queries
    test_cand = Candidate(
        id=1,
        name="Applicant",
        registration_number="temp-12345",
        evaluation_status="Pending",
        repository_evaluations=[],
        live_app_evaluations=[],
    )

    async def fake_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_result = MagicMock()
        if "candidates" in stmt_str:
            mock_result.scalars.return_value.first.return_value = test_cand
            mock_result.scalars.return_value.all.return_value = [test_cand]
        elif "projects" in stmt_str:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = fake_execute

    # Mock db.refresh to set Completed status and avoid 60 second sleep loop
    def fake_refresh(instance, *args, **kwargs):
        instance.evaluation_status = "Completed"
        instance.repository_evaluations = []
        instance.live_app_evaluations = []

    mock_db.refresh.side_effect = fake_refresh

    mock_parse.return_value = "Python machine learning resume text"
    mock_gen.return_value = LLMCompletionResult(
        content=(
            '{"technical_readiness": "High", "growth_potential": "High", '
            '"interest_alignment": "High", "explanation": "Looks great", '
            '"readiness_score": 0.8, "growth_potential_score": 0.9, '
            '"interest_score": 0.7, "semantic_fit_score": 0.85, '
            '"scoring_rationale": "Strong overlap", '
            '"missing_prerequisites": [], "compensating_skills": ["Python"]}'
        ),
        provider="groq",
        model="test-model",
    )

    pdf_content = b"%PDF-1.4 dummy pdf content"
    files = {"file": ("resume.pdf", pdf_content, "application/pdf")}

    response = await client.post(
        "/api/matching/student-recommendations",
        files=files,
        data={"preferred_topics": "AI, ML"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_name"] == "Applicant"
    assert body["recommendations"] == []
