"""Schemas for tenant-scoped originator and client CRM records."""

from __future__ import annotations

from datetime import datetime
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, EmailStr


class OriginatorFields(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    title: str | None = Field(None, max_length=120)
    firm_name: str | None = Field(None, max_length=200)
    biography: str | None = None
    sectors: str | None = Field(None, max_length=500)
    status: str = Field("active", max_length=30)


class OriginatorCreate(OriginatorFields):
    user_id: str | None = None


class OriginatorUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    title: str | None = Field(None, max_length=120)
    firm_name: str | None = Field(None, max_length=200)
    biography: str | None = None
    sectors: str | None = Field(None, max_length=500)
    status: str | None = Field(None, max_length=30)
    user_id: str | None = None


class OriginatorRead(OriginatorFields):
    id: str
    user_id: str | None
    full_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientFields(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    industry: str | None = Field(None, max_length=120)
    sector: str | None = Field(None, max_length=120)
    website: str | None = Field(None, max_length=500)
    contact_email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=200)
    turnover: Decimal | None = Field(None, ge=0)
    revenue: Decimal | None = Field(None, ge=0)
    funding_requirement: Decimal | None = Field(None, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    assigned_originator_id: str | None = None
    description: str | None = None
    status: str = Field("active", max_length=30)
    onboarding_status: str = Field("not_started", max_length=30)


class ClientCreate(ClientFields):
    pass


class ClientUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    industry: str | None = Field(None, max_length=120)
    sector: str | None = Field(None, max_length=120)
    website: str | None = Field(None, max_length=500)
    contact_email: EmailStr | None = None
    phone: str | None = Field(None, max_length=30)
    location: str | None = Field(None, max_length=200)
    turnover: Decimal | None = Field(None, ge=0)
    revenue: Decimal | None = Field(None, ge=0)
    funding_requirement: Decimal | None = Field(None, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=3)
    assigned_originator_id: str | None = None
    description: str | None = None
    status: str | None = Field(None, max_length=30)
    onboarding_status: str | None = Field(None, max_length=30)


class ClientRead(ClientFields):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientInteractionCreate(BaseModel):
    interaction_type: str = Field(..., min_length=1, max_length=40)
    summary: str = Field(..., min_length=1, max_length=500)
    notes: str | None = None


class ClientInteractionRead(ClientInteractionCreate):
    id: str
    client_id: str
    user_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClientDocumentRead(BaseModel):
    id: str
    name: str
    content_type: str | None
    size_bytes: int | None
    client_id: str | None
    extracted_fields: dict[str, str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VerificationCheckCreate(BaseModel):
    check_type: str = Field(..., min_length=1, max_length=30)


class VerificationCheckRead(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    check_type: str
    status: str
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MandateRead(BaseModel):
    id: str
    name: str
    client_id: str
    originator_id: str | None
    description: str | None
    target_value: Decimal | None
    currency: str
    status: str
    expires_on: date | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
