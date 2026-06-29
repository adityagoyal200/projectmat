from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/projectmatchai"
    )

    # AI Service Configuration
    LLM_PROVIDER: Literal["groq", "ollama", "gemini", "openai"] = "ollama"
    # When false, matching uses skill-based scoring only — no paid API calls.
    LLM_ENABLED: bool = True
    # Log full LLM prompts and responses to the server console.
    LLM_LOG_RESPONSES: bool = True
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Embeddings Configuration
    BGE_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDINGS_ENABLED: bool = True

    # Two-stage matching: LLM deep evaluation only for top-K preliminary candidates
    MATCH_LLM_TOP_K: int = 10

    # Hybrid scoring v2 — growth-potential weighted (normalized at runtime)
    SCORING_VERSION: str = "2.0.0"
    SCORE_WEIGHT_EMBEDDING_SIMILARITY: float = 0.15
    SCORE_WEIGHT_READINESS: float = 0.20
    SCORE_WEIGHT_GROWTH_POTENTIAL: float = 0.30
    SCORE_WEIGHT_INTEREST: float = 0.10
    SCORE_WEIGHT_PREREQUISITE_OVERLAP: float = 0.15
    SCORE_WEIGHT_RESUME_EXPERIENCE: float = 0.10

    # Application Settings
    ENV: Literal["development", "production", "test"] = "development"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    def llm_is_configured(self) -> bool:
        if self.LLM_PROVIDER == "groq":
            return bool(self.GROQ_API_KEY.strip())
        if self.LLM_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY.strip())
        if self.LLM_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY.strip())
        return bool(self.OLLAMA_BASE_URL.strip())


settings = Settings()
