# ruff: noqa: E402
import os

# Use lightweight token similarity in tests (no BGE model download).
os.environ.setdefault("EMBEDDINGS_ENABLED", "false")

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.models  # type: ignore # noqa: F401
from app.dependencies import get_db
from app.main import app as fastapi_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_db():
    """Fixture providing an AsyncMock representing the database session."""
    db = AsyncMock()

    def fake_add(instance):
        if hasattr(instance, "id") and instance.id is None:
            instance.id = 1

    db.add = MagicMock(side_effect=fake_add)

    # Mock execute results
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    db.execute.return_value = mock_result

    return db


@pytest.fixture
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing a test client with overridden database dependency."""
    fastapi_app.dependency_overrides[get_db] = lambda: mock_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
