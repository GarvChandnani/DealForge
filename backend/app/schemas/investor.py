from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal

class InvestorBase(BaseModel):
    name: str = Field(..., max_length=200)
    investor_type: Optional[str] = Field(None, max_length=50)
    contact_email: Optional[str] = Field(None, max_length=254)
    investment_min: Optional[Decimal] = None
    investment_max: Optional[Decimal] = None
    preferred_sectors: Optional[List[str]] = None
    investment_stage: Optional[str] = None
    geography: Optional[List[str]] = None
    thesis: Optional[str] = None
    historical_investments: Optional[List[str]] = None
    status: Optional[str] = Field(default="active", max_length=30)

class InvestorCreate(InvestorBase):
    pass

class InvestorRead(InvestorBase):
    id: str
    tenant_id: str

class InvestorUpdate(BaseModel):
    name: Optional[str] = None
    investor_type: Optional[str] = None
    contact_email: Optional[str] = None
    investment_min: Optional[Decimal] = None
    investment_max: Optional[Decimal] = None
    preferred_sectors: Optional[List[str]] = None
    investment_stage: Optional[str] = None
    geography: Optional[List[str]] = None
    thesis: Optional[str] = None
    historical_investments: Optional[List[str]] = None
    status: Optional[str] = None
