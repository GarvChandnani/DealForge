from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Column, Date, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin

class ComplianceCheck(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "compliance_checks"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending, passed, flagged
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # user id of reviewer
