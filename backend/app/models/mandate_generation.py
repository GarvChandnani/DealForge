"""Tenant-scoped AI document processing and mandate drafts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class MandateGeneration(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "mandate_generations"

    source_document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="uploaded", nullable=False, index=True
    )
    processing_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    extracted_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    financial_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    deal_proposal: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    mandate_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    teaser_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_review: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    agent_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
