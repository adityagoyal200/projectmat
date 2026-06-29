import pytest
from httpx import AsyncClient

from app.features.imports.models import ImportBatch, ImportFile


@pytest.mark.anyio
async def test_create_import_batch(client: AsyncClient, mock_db):
    def assign_id(instance):
        if isinstance(instance, ImportBatch):
            instance.id = 1

    mock_db.add.side_effect = assign_id

    response = await client.post("/api/import-batches")

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["status"] == "created"


@pytest.mark.anyio
async def test_upload_workbook_api(client: AsyncClient, mock_db):
    batch = ImportBatch(id=1, status="created")
    mock_db.get.return_value = batch

    def assign_id(instance):
        if isinstance(instance, ImportFile):
            instance.id = 2

    mock_db.add.side_effect = assign_id

    from pathlib import Path

    with Path("tests/fixtures/valid_workbook.xlsx").open("rb") as f:
        file_content = f.read()

    files = {
        "file": (
            "valid_workbook.xlsx",
            file_content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = await client.post("/api/import-batches/1/files", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "validated"
    assert data["can_proceed"] is True
    assert "Students Info" in data["sheet_summaries"]
    assert data["sheet_summaries"]["Students Info"]["total_rows"] == 3


@pytest.mark.anyio
async def test_upload_invalid_file(client: AsyncClient):
    files = {"file": ("test.txt", b"not a workbook", "text/plain")}

    response = await client.post("/api/import-batches/1/files", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
