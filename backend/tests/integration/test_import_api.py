import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_workbook_api(client: AsyncClient):
    with open("tests/fixtures/valid_workbook.xlsx", "rb") as f:
        file_content = f.read()

    # Create the multipart form data payload
    files = {
        "file": (
            "valid_workbook.xlsx",
            file_content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }

    response = await client.post("/api/imports/workbook", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "validated"
    assert "Students Info" in data["sheet_summaries"]
    assert data["sheet_summaries"]["Students Info"]["total_rows"] == 3


@pytest.mark.asyncio
async def test_upload_invalid_file(client: AsyncClient):
    files = {"file": ("test.txt", b"not a workbook", "text/plain")}

    response = await client.post("/api/imports/workbook", files=files)

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
