"""
DealForge Backend — Deal ORM Model.

Represents a sales deal/opportunity in the CRM.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Deal(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """Sales deal / opportunity."""

    __tablename__ = "deals"

    # ── Core fields ───────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(
        String(50), nullable=False, default="lead_identified", index=True
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    deal_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transaction_size: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    ebitda: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    funding_requirement: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    target_valuation: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    probability: Mapped[int | None] = mapped_column(nullable=True)  # 0–100 %
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────
    # owner_id references the contacts table (the deal owner/account)
    contact_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    client_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    originator_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("originators.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    contact: Mapped["Contact"] = relationship(  # type: ignore[name-defined]
        "Contact", back_populates="deals", lazy="select"
    )

    # ── AI metadata ───────────────────────────────────────────────────
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_next_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Deal id={self.id!r} name={self.name!r} stage={self.stage!r}>"
