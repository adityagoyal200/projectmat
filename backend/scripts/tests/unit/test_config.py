import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_load():
    """Verify that settings can load and store parameters correctly."""
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://test_user:test_pass@test_host:5432/test_db",
        LLM_PROVIDER="ollama",
    )
    assert (
        settings.DATABASE_URL
        == "postgresql+asyncpg://test_user:test_pass@test_host:5432/test_db"
    )
    assert settings.LLM_PROVIDER == "ollama"


def test_settings_invalid_provider():
    """Verify that invalid literals raise Pydantic validation errors."""
    with pytest.raises(ValidationError):
        Settings(LLM_PROVIDER="unsupported_provider")  # type: ignore
