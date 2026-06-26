from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.dependencies import get_db
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def mock_db():
    """Fixture providing an AsyncMock representing the database session."""
    return AsyncMock()


@pytest.fixture
async def client(mock_db) -> AsyncGenerator[AsyncClient, None]:
    """Fixture providing a test client with overridden database dependency."""
    app.dependency_overrides[get_db] = lambda: mock_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
