from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.candidates.models import Candidate, CandidateDocument
from app.features.imports.models import ImportBatch, ImportFile
from app.features.imports.service import WorkbookImportService
from app.features.mentors.models import Mentor


@pytest.mark.anyio
async def test_service_creates_batch(mock_db):
    service = WorkbookImportService(mock_db)

    def assign_id(instance):
        if isinstance(instance, ImportBatch):
            instance.id = 1

    mock_db.add.side_effect = assign_id

    result = await service.create_batch()

    assert result.id == 1
    assert result.status == "created"
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called
    assert mock_db.refresh.called


@pytest.mark.anyio
async def test_ingest_resumes_extracts_missing_profiles_from_resume_text():
    service = WorkbookImportService(AsyncMock())

    candidate = Candidate(
        id=7,
        registration_number="ABC123456",
        name="Alex Dev",
        github_username=None,
        leetcode_username=None,
        codeforces_username=None,
        kaggle_username=None,
        scholar_id=None,
        github_repositories=[],
        live_project_links=[],
        achievements=None,
    )
    resume_doc = CandidateDocument(
        candidate_id=7,
        document_type="resume",
        parse_status="pending",
    )

    candidate_lookup = {
        "candidate": candidate,
        "document": resume_doc,
    }

    call_counter = {"n": 0}

    def execute_side_effect(*_args, **_kwargs):
        call_counter["n"] += 1
        result = MagicMock()
        scalar_result = MagicMock()
        if call_counter["n"] == 1:
            # Batch candidate list for filename matching
            scalar_result.all.return_value = [candidate_lookup["candidate"]]
            scalar_result.first.return_value = None
        elif call_counter["n"] == 2:
            # CandidateDocument lookup
            scalar_result.first.return_value = candidate_lookup["document"]
            scalar_result.all.return_value = []
        else:
            # Skill select / CandidateSkill lookups
            scalar_result.first.return_value = None
            scalar_result.all.return_value = []
        result.scalars.return_value = scalar_result
        return result

    fake_db = AsyncMock()
    fake_db.execute.side_effect = execute_side_effect
    fake_db.add = MagicMock()
    fake_db.flush = AsyncMock()
    fake_db.commit = AsyncMock()

    session_factory = MagicMock()
    session_factory.__aenter__ = AsyncMock(return_value=fake_db)
    session_factory.__aexit__ = AsyncMock(return_value=None)

    resume_text = """
    GitHub: https://github.com/alex-dev/vision-demo
    LeetCode: https://leetcode.com/u/alex_dev/
    Codeforces: https://codeforces.com/profile/alex.dev
    Kaggle: https://kaggle.com/alexdata
    Scholar: https://scholar.google.com/citations?user=abcDEF12
    Live app: https://vision-demo.vercel.app
    Winner, university AI hackathon 2025.
    """

    with (
        patch("app.database.async_session", return_value=session_factory),
        patch(
            "app.features.imports.drive_downloader.download_resumes_from_drive",
            return_value={"ABC123456_resume.pdf": b"pdf"},
        ),
        patch(
            "app.features.imports.drive_downloader.parse_pdf_bytes",
            return_value=resume_text,
        ),
    ):
        await service.ingest_resumes_background_task(
            batch_id=1,
            resumes_url="https://drive.google.com/mock",
        )

    assert candidate.github_username == "alex-dev"
    assert candidate.leetcode_username == "alex_dev"
    assert candidate.codeforces_username == "alex.dev"
    assert candidate.kaggle_username == "alexdata"
    assert candidate.scholar_id == "abcDEF12"
    assert candidate.github_repositories == ["https://github.com/alex-dev/vision-demo"]
    assert candidate.live_project_links == ["https://vision-demo.vercel.app"]
    assert candidate.achievements == ["Winner, university AI hackathon 2025."]


@pytest.mark.anyio
@patch("app.features.imports.service.asyncio.create_task")
async def test_service_parses_workbook_and_persists_issues(_mock_create_task, mock_db):
    service = WorkbookImportService(mock_db)
    batch = ImportBatch(
        id=1, status="created", total_candidates=0, completed_candidates=0
    )
    mock_db.get.return_value = batch

    from pathlib import Path

    with Path("tests/fixtures/valid_workbook.xlsx").open("rb") as f:
        file_content = f.read()

    def assign_id(instance):
        if isinstance(instance, ImportFile):
            instance.id = 2

    mock_db.add.side_effect = assign_id

    result = await service.import_workbook(1, "valid.xlsx", file_content)

    assert result.id == 1
    assert result.status == "validated"
    assert result.can_proceed is True
    assert result.sheet_summaries["Students Info"].total_rows == 3
    assert result.sheet_summaries["Mentors info"].total_rows == 1
    mentor_records = [
        call.args[0]
        for call in mock_db.add.call_args_list
        if call.args and isinstance(call.args[0], Mentor)
    ]

    assert batch.total_candidates == 3
    assert batch.completed_candidates == 3
    assert mentor_records
    assert all(mentor.import_batch_id == batch.id for mentor in mentor_records)
    assert mock_db.get.called
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called
    assert mock_db.refresh.called


@pytest.mark.anyio
@patch("app.features.matching.llm_client.generate_chat_completion")
async def test_extract_identity_from_resume(mock_chat_completion):
    from app.features.imports.service import _extract_identity_from_resume

    # Mock LLM being skipped/unavailable
    mock_result = MagicMock()
    mock_result.skipped = True
    mock_chat_completion.return_value = mock_result

    # 1. Reg number match and fallback name matching
    text = "MDS202505\nJohn Doe"
    name, reg = await _extract_identity_from_resume(text, "john_doe.pdf")
    assert reg == "MDS202505"
    assert name == "John Doe"

    # 2. No reg number in text -> synthetic RES-<uuid> should be generated
    text = "Jane Smith\nPython Developer"
    name, reg = await _extract_identity_from_resume(text, "jane_smith.pdf")
    assert reg.startswith("RES-")
    assert name == "Jane Smith"
