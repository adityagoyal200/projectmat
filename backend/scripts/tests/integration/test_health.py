from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_health_endpoint_success(client: AsyncClient, mock_db: AsyncMock):
    """Verify health check returns 200 ok when database queries succeed."""
    mock_db.execute.return_value = None

    response = await client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "X-Request-ID" in response.headers


@pytest.mark.anyio
async def test_health_endpoint_database_offline(
    client: AsyncClient, mock_db: AsyncMock
):
    """Verify health check returns 503 error when database is unreachable."""
    mock_db.execute.side_effect = Exception("Database connection failure")

    response = await client.get("/api/health")
    assert response.status_code == 503

    data = response.json()
    assert data["status"] == "error"
    assert data["database"] == "disconnected"
    assert "X-Request-ID" in response.headers
