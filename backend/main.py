"""
DealForge Backend — Application Entry Point.

Run with:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Or via the helper script:
    python main.py
"""

from __future__ import annotations

import sys
import os

# Allow importing the shared module from the monorepo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.config import get_settings
from app.logging_config import configure_logging, get_logger
from app.middleware import register_middleware
from app.errors import register_error_handlers
from app.api.router import api_router
from app.api.v1.health import router as health_router
from app.db.session import create_all_tables

settings = get_settings()

# ── Bootstrap logging before anything else ───────────────────────────────────
configure_logging(log_level=settings.log_level, log_format=settings.log_format)
logger = get_logger("main")


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler — runs startup and shutdown tasks."""
    logger.info(
        "dealforge_starting",
        env=settings.app_env,
        version=settings.app_version,
        db=settings.database_url.split("@")[-1],  # Hide credentials in log
    )

    # Create DB tables (idempotent — safe to call on every startup)
    await create_all_tables()

    # Ensure the document storage directory exists (uses /tmp on Render)
    settings.document_storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info("startup_complete")

    yield  # ← Application runs here

    logger.info("dealforge_shutting_down")


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "DealForge — AI-native enterprise CRM and deal origination API.\n\n"
        "All endpoints are prefixed with `/api/v1`."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# Register middleware (order matters — CORS first, then logging)
register_middleware(app)

# Register global error handlers
register_error_handlers(app)

# Mount all API routes
app.include_router(api_router)
app.include_router(health_router)


# ── Root redirect ─────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# ── Dev runner ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
