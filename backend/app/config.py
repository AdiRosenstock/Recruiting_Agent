"""Application configuration.

Single source of truth for anything that comes from the environment. Everything else in the
app should import `get_settings()` rather than reading `os.environ` directly, so behavior stays
testable and swappable (e.g. tests override `DATABASE_URL_TEST`, `LLM_PROVIDER=stub`).
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ -- the directory this file's package root lives in. Used to resolve
# RESUME_STORAGE_DIR relative to the backend project rather than the process cwd.
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    database_url: str = (
        "postgresql+psycopg://recruiting_agent:recruiting_agent@localhost:5433/recruiting_agent"
    )
    database_url_test: str = (
        "postgresql+psycopg://recruiting_agent:recruiting_agent@localhost:5433/"
        "recruiting_agent_test"
    )

    resume_storage_dir: str = "data/resumes"

    llm_provider: Literal["openai", "anthropic", "stub"] = "stub"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def resume_storage_path(self) -> Path:
        path = Path(self.resume_storage_dir)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
