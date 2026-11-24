from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Column, Date, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin

class DueDiligenceReport(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "due_diligence_reports"

    deal_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    completeness_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    missing_items: Mapped[list | None] = mapped_column(JSON, nullable=True)
    financial_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str] = mapped_column(String(36), nullable=False)  # user id
