"""
DealForge Backend — Health Check Endpoint.

GET /api/v1/health

Returns the operational status of the API and its dependencies.
Used by load balancers, monitoring tools, and the frontend dashboard.
"""

from __future__ import annotations

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.config import Settings
from app.dependencies import get_app_settings

router = APIRouter(tags=["Health"])

_start_time = time.time()


@router.get(
    "/health",
    summary="Health check",
    description="Returns API status, database connectivity, and uptime.",
    response_description="Health status object",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, Any]:
    """
    Comprehensive health check.

    Checks:
    - API is reachable
    - Database connection is live
    """
    db_status = "ok"
    db_error: str | None = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_error = str(exc)

    uptime_seconds = round(time.time() - _start_time, 1)

    overall = "ok" if db_status == "ok" else "degraded"

    response: Dict[str, Any] = {
        "status": overall,
        "version": settings.app_version,
        "environment": settings.app_env,
        "uptime_seconds": uptime_seconds,
        "dependencies": {
            "database": {
                "status": db_status,
                "driver": settings.database_url.split(":")[0],
            }
        },
    }

    if db_error:
        response["dependencies"]["database"]["error"] = db_error

    return response
