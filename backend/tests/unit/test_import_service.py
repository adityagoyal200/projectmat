from unittest.mock import patch

import pytest

from app.features.imports.models import ImportBatch, ImportFile
from app.features.imports.service import WorkbookImportService


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
@patch("app.features.imports.service.asyncio.create_task")
async def test_service_parses_workbook_and_persists_issues(_mock_create_task, mock_db):
    service = WorkbookImportService(mock_db)
    batch = ImportBatch(id=1, status="created")
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
    assert mock_db.get.called
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called
    assert mock_db.refresh.called
