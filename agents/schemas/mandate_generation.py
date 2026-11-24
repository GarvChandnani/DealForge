"""Structured Pydantic outputs for document-grounded deal generation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    document_id: str
    file_name: str
    location: str
    quote: str


class FieldEvidence(BaseModel):
    value: str | None = None
    status: Literal["available", "unavailable"] = "unavailable"
    source: SourceReference | None = None


class FactConflict(BaseModel):
    field: str
    values: list[str]
    sources: list[SourceReference]


class DocumentExtraction(BaseModel):
    source_document_id: str
    source_file_name: str
    document_type: Literal["pdf", "docx"]
    text_length: int = Field(ge=0)
    facts: dict[str, FieldEvidence]
    conflicts: list[FactConflict] = Field(default_factory=list)


class FinancialAnalysis(BaseModel):
    revenue: FieldEvidence
    ebitda: FieldEvidence
    liabilities: FieldEvidence
    assets: FieldEvidence
    profitability: FieldEvidence
    funding_requirement: FieldEvidence


class DealProposal(BaseModel):
    title: str
    company_name: FieldEvidence
    industry: FieldEvidence
    sector: FieldEvidence
    deal_type: FieldEvidence
    transaction_size: FieldEvidence
    revenue: FieldEvidence
    ebitda: FieldEvidence
    liabilities: FieldEvidence
    assets: FieldEvidence
    profitability: FieldEvidence
    funding_requirement: FieldEvidence
    target_valuation: FieldEvidence
    description: str
    source_document_id: str


class QualityReview(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    passed: bool
