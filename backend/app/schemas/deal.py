"""
DealForge Backend — Pydantic Schemas for Deal.

Separate schemas for create, update, and read operations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_serializer, field_validator


class DealBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Deal name")
    stage: str = Field("lead_identified", description="Pipeline stage")
    value: Optional[Decimal] = Field(None, ge=0, description="Deal value")
    company_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=120)
    sector: Optional[str] = Field(None, max_length=120)
    deal_type: Optional[str] = Field(None, max_length=100)
    transaction_size: Optional[Decimal] = Field(None, ge=0)
    revenue: Optional[Decimal] = Field(None, ge=0)
    ebitda: Optional[Decimal] = None
    funding_requirement: Optional[Decimal] = Field(None, ge=0)
    target_valuation: Optional[Decimal] = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    probability: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    contact_id: Optional[str] = None
    client_id: Optional[str] = None
    originator_id: Optional[str] = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        from shared.constants import DealStage
        if v not in DealStage.ALL:
            raise ValueError(f"stage must be one of {DealStage.ALL}")
        return v

    @field_serializer(
        "value",
        "transaction_size",
        "revenue",
        "ebitda",
        "funding_requirement",
        "target_valuation",
    )
    def serialize_amount(self, amount: Decimal | None) -> float | None:
        return float(amount) if amount is not None else None


class DealCreate(DealBase):
    """Schema for creating a new deal."""
    pass


class DealUpdate(BaseModel):
    """Schema for partially updating a deal (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    stage: Optional[str] = None
    value: Optional[Decimal] = Field(None, ge=0)
    company_name: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=120)
    sector: Optional[str] = Field(None, max_length=120)
    deal_type: Optional[str] = Field(None, max_length=100)
    transaction_size: Optional[Decimal] = Field(None, ge=0)
    revenue: Optional[Decimal] = Field(None, ge=0)
    ebitda: Optional[Decimal] = None
    funding_requirement: Optional[Decimal] = Field(None, ge=0)
    target_valuation: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    probability: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None
    contact_id: Optional[str] = None
    client_id: Optional[str] = None
    originator_id: Optional[str] = None

    @field_validator("stage")
    @classmethod
    def validate_stage(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from shared.constants import DealStage
        if value not in DealStage.ALL:
            raise ValueError(f"stage must be one of {DealStage.ALL}")
        return value


class DealRead(DealBase):
    """Schema for reading a deal from the API."""
    id: str
    ai_summary: Optional[str] = None
    ai_next_action: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DealDocumentRead(BaseModel):
    id: str
    name: str
    content_type: str | None
    size_bytes: int | None
    deal_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DealActivityRead(BaseModel):
    id: str
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
