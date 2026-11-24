"""
DealForge Backend — Database Session Management.

Supports:
- SQLite + aiosqlite (local development, zero config)
- PostgreSQL + asyncpg (production)

The active driver is selected automatically from DATABASE_URL.
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger("db.session")

_settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
_engine_kwargs: dict = {
    "echo": _settings.is_development,  # Log SQL in dev
    "future": True,
}

if _settings.is_sqlite:
    # SQLite requires check_same_thread=False for async use
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL — connection pool tuning
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(_settings.async_database_url, **_engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session per request.

    Usage:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_all_tables() -> None:
    """Create all database tables from SQLAlchemy models. Used on startup."""
    from app.models import Base  # noqa: F401 — imports all model metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created", url=_settings.database_url.split("@")[-1])
