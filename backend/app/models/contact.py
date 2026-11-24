"""
DealForge Backend — Contact ORM Model.

Represents a person or organisation in the CRM.
"""

from __future__ import annotations

from typing import List

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDMixin


class Contact(Base, UUIDMixin, TenantMixin, TimestampMixin):
    """CRM contact — a person or organisation."""

    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_contacts_org_email"),)

    # ── Core fields ───────────────────────────────────────────────────
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(
        String(254), nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="lead", index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────
    deals: Mapped[List["Deal"]] = relationship(  # type: ignore[name-defined]
        "Deal", back_populates="contact", lazy="select"
    )

    # ── Computed ─────────────────────────────────────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Contact id={self.id!r} name={self.full_name!r} email={self.email!r}>"
