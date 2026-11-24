"""
DealForge Backend — Centralized Error Handling.

Implements RFC 7807 Problem Details responses for all error types.
All handlers are registered on the FastAPI application instance.
"""

from __future__ import annotations

import traceback
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.logging_config import get_logger

logger = get_logger("errors")


def _problem_detail(
    status_code: int,
    title: str,
    detail: str,
    *,
    instance: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an RFC 7807 Problem Details payload."""
    payload: dict[str, Any] = {
        "status": status_code,
        "title": title,
        "detail": detail,
    }
    if instance:
        payload["instance"] = instance
    if extra:
        payload.update(extra)
    return payload


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning(
            "http_exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_problem_detail(
                status_code=exc.status_code,
                title=_status_title(exc.status_code),
                detail=str(exc.detail),
                instance=str(request.url),
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        logger.warning(
            "validation_error",
            path=request.url.path,
            errors=errors,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_problem_detail(
                status_code=422,
                title="Validation Error",
                detail="One or more request fields failed validation.",
                instance=str(request.url),
                extra={"errors": jsonable_encoder(errors)},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            exc_type=type(exc).__name__,
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_problem_detail(
                status_code=500,
                title="Internal Server Error",
                detail="An unexpected error occurred. Please try again later.",
                instance=str(request.url),
            ),
        )


def _status_title(status_code: int) -> str:
    """Map HTTP status code to a human-readable title."""
    titles = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }
    return titles.get(status_code, f"HTTP {status_code}")
