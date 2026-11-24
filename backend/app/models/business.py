"""Tenant-scoped deal origination and compliance models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Client(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    funding_requirement: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    assigned_originator_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("originators.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    onboarding_status: Mapped[str] = mapped_column(
        String(30), default="not_started", nullable=False
    )


class ClientInteraction(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "client_interactions"

    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    interaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Investor(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "investors"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    investor_type: Mapped[str] = mapped_column(String(50), default="institutional", nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    investment_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    investment_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    preferred_sectors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    investment_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    geography: Mapped[list | None] = mapped_column(JSON, nullable=True)
    thesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    historical_investments: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)


class Document(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "documents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    deal_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )


class DealMatch(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "deal_matches"
    __table_args__ = (
        UniqueConstraint("deal_id", "investor_id", name="uq_deal_matches_deal_investor"),
    )

    deal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False
    )
    investor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("investors.id", ondelete="CASCADE"), nullable=False
    )
    match_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    criteria_match: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mismatches: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="suggested", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Mandate(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "mandates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    originator_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("originators.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="active", nullable=False)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class ComplianceRecord(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "compliance_records"

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    check_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Transaction(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "transactions"

    deal_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    reference: Mapped[str | None] = mapped_column(String(150), nullable=True)
    completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    commission_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, default=Decimal('2.5'))
    success_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    invoice_milestones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    payment_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)


class ActivityLog(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "activity_logs"

    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
