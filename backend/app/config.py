from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: Literal["development", "production", "test"] = "development"
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
    HF_TOKEN: str = ""

    # Two-stage matching: LLM deep evaluation only for top-K preliminary candidates
    MATCH_LLM_TOP_K: int = 10
    MATCH_SIGNAL_CONCURRENCY: int = 8
    MATCH_RESPONSE_CACHE_TTL_SECONDS: int = 120

    # Hybrid scoring v3 — deterministic-first (normalized at runtime)
    SCORING_VERSION: str = "3.0.0"
    SCORE_WEIGHT_EMBEDDING_SIMILARITY: float = 0.10
    SCORE_WEIGHT_PREREQUISITE_OVERLAP: float = 0.15
    SCORE_WEIGHT_RESUME_EXPERIENCE: float = 0.10
    SCORE_WEIGHT_GITHUB: float = 0.30
    SCORE_WEIGHT_CODING_PROFILES: float = 0.20
    SCORE_WEIGHT_ACHIEVEMENTS: float = 0.10
    SCORE_WEIGHT_LLM_FIT: float = 0.05

    # GitHub API token for authenticated repo scanning (avoids rate-limits)
    GITHUB_TOKEN: str = ""
    # GitLab API token for authenticated enterprise repository cloning
    GITLAB_TOKEN: str = ""

    # External browser/code agent orchestration
    AGY_COMMAND: str = "agy"
    AGY_MODEL: str = "Gemini 3.5 Flash (Low)"
    AGY_PRINT_TIMEOUT: str = "30m0s"
    AGY_CALLBACK_BASE_URL: str | None = None

    # Timeout in seconds when verifying live project links
    LIVE_LINK_TIMEOUT: int = 5

    FRONTEND_PORT: int = 5173
    BACKEND_PORT: int = 8000

    @computed_field
    @property
    def frontend_origin(self) -> str:
        return f"http://localhost:{self.FRONTEND_PORT}"

    @computed_field
    @property
    def backend_base_url(self) -> str:
        return f"http://localhost:{self.BACKEND_PORT}"

    @computed_field
    @property
    def agy_callback_base_url(self) -> str:
        if self.AGY_CALLBACK_BASE_URL and self.AGY_CALLBACK_BASE_URL.strip():
            return self.AGY_CALLBACK_BASE_URL.strip().rstrip("/")
        return self.backend_base_url

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
