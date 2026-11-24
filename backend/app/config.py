"""
DealForge Backend — Application Configuration.

Uses Pydantic Settings to load config from environment variables / .env file.
No secrets are hardcoded — all sensitive values must be provided via env.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Central application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "DealForge API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_secret_key: str = ""
    dealforge_demo_password: str = "demo123"
    jwt_access_token_expire_minutes: int = Field(default=30, gt=0, le=1440)

    # ── Server ───────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:4173,"
        "http://127.0.0.1:5173,http://127.0.0.1:4173"
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # ── Database ─────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./dealforge.db"
    # Document uploads — ephemeral on Render free tier; use /tmp as fallback.
    document_storage_dir: Path = Path("/tmp/dealforge-uploads")

    @property
    def _normalised_database_url(self) -> str:
        """Normalise Render's postgres:// to the correct SQLAlchemy scheme."""
        url = self.database_url
        # Render provides bare postgres:// — rewrite for asyncpg async driver
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        return url

    @property
    def async_database_url(self) -> str:
        """Async URL used by SQLAlchemy engine."""
        url = self._normalised_database_url
        # Ensure asyncpg driver for postgres
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def sync_database_url(self) -> str:
        """Synchronous DB URL for Alembic migrations (psycopg2 / sqlite)."""
        url = self._normalised_database_url
        return (
            url
            .replace("sqlite+aiosqlite", "sqlite")
            .replace("postgresql+asyncpg", "postgresql+psycopg2")
            .replace("postgresql://", "postgresql+psycopg2://")
        )

    # ── Logging ───────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "console"  # console | json

    # ── LLM / AI ─────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    litellm_default_model: str = "gpt-4o-mini"
    ai_mock_mode: bool = False

    # ── Derived ───────────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton — avoids re-parsing .env on every call."""
    return Settings()
