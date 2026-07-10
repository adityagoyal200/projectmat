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
async def test_download_match_report_candidate_not_found(client: AsyncClient):
    # Patch the LLM-readiness gate so the result is independent of the test env's
    # provider config; the candidate lookup should then be what yields the 404.
    with patch(
        "app.features.matching.service.MatchService._ensure_llm_ready",
        return_value=None,
    ):
        response = await client.get(
            "/api/matching/report",
            params={"registration_number": "NONEXISTENT", "project_id": 1},
        )
    assert response.status_code == 404


@pytest.mark.anyio
async def test_download_match_report_requires_llm(client: AsyncClient):
    from app.features.matching.exceptions import MatchingUnavailableError

    with patch(
        "app.features.matching.service.MatchService._ensure_llm_ready",
        side_effect=MatchingUnavailableError("LLM_ENABLED is false."),
    ):
        response = await client.get(
            "/api/matching/report",
            params={"registration_number": "MDS202519", "project_id": 1},
        )
    assert response.status_code == 503


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


@pytest.mark.anyio
@patch(
    "app.features.matching.match_explanation.generate_chat_completion",
    new_callable=AsyncMock,
)
async def test_get_student_recommendations_with_llm_failure(
    mock_gen, client: AsyncClient, mock_db
):
    from unittest.mock import MagicMock

    from app.features.candidates.models import Candidate
    from app.features.projects.models import Project

    # Create dummy candidate & project
    test_cand = Candidate(
        id=1,
        name="John Doe",
        registration_number="MDS202519",
        evaluation_status="Completed",
        repository_evaluations=[],
        live_app_evaluations=[],
        skills=[],
        documents=[],
    )
    test_project = Project(
        id=42,
        title="AI Automation",
        abstract="Use AI for automation tasks",
        prerequisites=[],
        preferences=[],
    )

    async def fake_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_result = MagicMock()
        if "candidate" in stmt_str:
            mock_result.scalars.return_value.first.return_value = test_cand
            mock_result.scalars.return_value.all.return_value = [test_cand]
        elif "project" in stmt_str:
            mock_result.scalars.return_value.first.return_value = test_project
            mock_result.scalars.return_value.all.return_value = [test_project]
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = fake_execute

    # Set generate_chat_completion to raise Exception
    mock_gen.side_effect = Exception("ReadTimeout error from LLM provider")

    response = await client.get("/api/matching/student-recommendations/MDS202519")
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_name"] == "John Doe"
    assert len(body["recommendations"]) == 1

    rec = body["recommendations"][0]
    assert rec["project_title"] == "AI Automation"
    # Verify that LLM evaluated flag is false and it fell back to preliminary score
    assert rec["score_components"]["llm_evaluated"] is False
    assert "LLM evaluation failed due to provider error" in rec["explanation"]


@pytest.mark.anyio
@patch(
    "app.features.matching.match_explanation.generate_chat_completion",
    new_callable=AsyncMock,
)
async def test_recommend_projects_with_fallback_matching(
    mock_gen, client: AsyncClient, mock_db
):
    from unittest.mock import MagicMock

    from app.features.candidates.models import Candidate
    from app.features.imports.models import ImportBatch
    from app.features.projects.models import Project

    # Candidate has import_batch_id = 99 (which has no projects)
    test_cand = Candidate(
        id=1,
        name="Fallback Candidate",
        registration_number="RES-FALLBACK",
        import_batch_id=99,
        evaluation_status="Completed",
        repository_evaluations=[],
        live_app_evaluations=[],
        skills=[],
        documents=[],
    )
    # ImportBatch with resumes_url and no workbook files
    test_batch = ImportBatch(
        id=99,
        resumes_url="https://drive.google.com/drive/folders/1pPADQHbZsoTAgyJbBTGb5T-sIGhUxXCr",
        files=[],
    )
    # Project in system (has import_batch_id = None for dummy project matching)
    test_project = Project(
        id=42,
        title="Global Project",
        abstract="A project that exists in another batch",
        import_batch_id=None,
        prerequisites=[],
        preferences=[],
    )

    async def fake_execute(stmt, *args, **kwargs):
        stmt_str = str(stmt).lower()
        mock_result = MagicMock()
        if "from candidates" in stmt_str or "candidates." in stmt_str:
            mock_result.scalars.return_value.first.return_value = test_cand
            mock_result.scalars.return_value.all.return_value = [test_cand]
        elif "from import_batches" in stmt_str or "import_batches." in stmt_str:
            mock_result.scalars.return_value.first.return_value = test_batch
            mock_result.scalars.return_value.all.return_value = [test_batch]
        elif "project" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [test_project]
        else:
            mock_result.scalars.return_value.first.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    mock_db.execute.side_effect = fake_execute

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

    # Make the GET request to recommendations
    response = await client.get("/api/matching/student-recommendations/RES-FALLBACK")
    assert response.status_code == 200
    body = response.json()
    assert body["candidate_name"] == "Fallback Candidate"
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["project_title"] == "Global Project"
