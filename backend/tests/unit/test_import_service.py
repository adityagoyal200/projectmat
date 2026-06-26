import pytest

from app.features.imports.models import ImportBatch, ImportFile
from app.features.imports.service import WorkbookImportService


@pytest.mark.asyncio
async def test_service_creates_batch_and_persists_issues(mock_db):
    # Setup mock behavior
    service = WorkbookImportService(mock_db)

    # We will use the valid workbook fixture content
    with open("tests/fixtures/valid_workbook.xlsx", "rb") as f:
        file_content = f.read()

    # The mock flush will not populate batch.id automatically, so we simulate it
    def side_effect_add(instance):
        if isinstance(instance, ImportBatch) or isinstance(instance, ImportFile):
            setattr(instance, "id", 1)

    mock_db.add.side_effect = side_effect_add

    # Execute
    result = await service.import_workbook("valid.xlsx", file_content)

    # Asserts
    assert result.status == "validated"
    assert result.sheet_summaries["Students Info"].total_rows == 3
    assert result.sheet_summaries["Mentors info"].total_rows == 1

    # Check that db methods were called
    assert mock_db.add.called
    assert mock_db.flush.called
    assert mock_db.commit.called
    assert mock_db.refresh.called
