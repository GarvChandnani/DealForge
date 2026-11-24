"""
DealForge Backend — FastAPI Dependencies.

Re-usable DI providers injected via Depends().
"""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.db.session import get_db
from app.config import Settings, get_settings

__all__ = [
    "get_session",
    "get_app_settings",
    "get_current_user",
    "require_roles",
]


async def get_session(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    """Alias for get_db — cleaner name in route signatures."""
    yield db


def get_app_settings() -> Settings:
    """Inject application settings into routes."""
    return get_settings()
