from sqlalchemy import String, Text, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin, TenantMixin, TimestampMixin

class ResearchLead(Base, UUIDMixin, TenantMixin, TimestampMixin):
    __tablename__ = "research_leads"

    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    keywords: Mapped[list] = mapped_column(JSON, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verified_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    inference_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    opportunities: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="lead", nullable=False)
