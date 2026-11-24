"""
DealForge Backend — Pydantic Schemas for Contact.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    contact_type: str = Field("lead", description="lead | prospect | customer | partner")
    notes: Optional[str] = None

    @field_validator("contact_type")
    @classmethod
    def validate_contact_type(cls, v: str) -> str:
        from shared.constants import ContactType
        if v not in ContactType.ALL:
            raise ValueError(f"contact_type must be one of {ContactType.ALL}")
        return v


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""
    pass


class ContactUpdate(BaseModel):
    """Schema for partially updating a contact."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)
    company: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=100)
    contact_type: Optional[str] = None
    notes: Optional[str] = None


class ContactRead(ContactBase):
    """Schema for reading a contact from the API."""
    id: str
    full_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
