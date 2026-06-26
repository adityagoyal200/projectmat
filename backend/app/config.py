from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/projectmatchai"
    )

    # AI Service Configuration
    LLM_PROVIDER: Literal["groq", "ollama"] = "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"

    # Embeddings Configuration
    BGE_MODEL_NAME: str = "BAAI/bge-m3"

    # Application Settings
    ENV: Literal["development", "production", "test"] = "development"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
