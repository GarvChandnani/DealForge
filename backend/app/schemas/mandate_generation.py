"""API schemas for AI document processing and approval."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class MandateGenerationUpdate(BaseModel):
    mandate_draft: str | None = Field(None, max_length=50_000)
    teaser_draft: str | None = Field(None, max_length=20_000)


class MandateGenerationRead(BaseModel):
    id: str
    source_document_id: str
    source_document_name: str
    status: Literal[
        "uploaded", "processing", "awaiting_review", "approved", "failed"
    ]
    processing_mode: Literal["mock", "litellm"] | None
    extracted_data: dict[str, Any] | None
    financial_analysis: dict[str, Any] | None
    deal_proposal: dict[str, Any] | None
    mandate_draft: str | None
    teaser_draft: str | None
    quality_review: dict[str, Any] | None
    agent_history: list[dict[str, Any]]
    error_message: str | None
    approved_by_id: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime
