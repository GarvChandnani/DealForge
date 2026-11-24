"""
DealForge Agents — CRM LangChain Tools.

These tools allow LangGraph agents to interact with the CRM backend.
Each tool wraps a backend API call or database query.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from langchain_core.tools import tool

_BACKEND_URL = os.getenv("VITE_API_URL", "http://localhost:8000")
_API_BASE = f"{_BACKEND_URL}/api/v1"


@tool
async def get_deal(deal_id: str) -> dict:
    """Retrieve a CRM deal by its ID."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_API_BASE}/deals/{deal_id}")
        response.raise_for_status()
        return response.json()


@tool
async def list_deals(skip: int = 0, limit: int = 10) -> list:
    """List CRM deals with optional pagination."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_API_BASE}/deals/", params={"skip": skip, "limit": limit}
        )
        response.raise_for_status()
        return response.json()


@tool
async def create_deal(
    name: str,
    stage: str = "prospecting",
    value: Optional[float] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a new CRM deal.

    Args:
        name: Deal name / title.
        stage: Pipeline stage (prospecting, qualification, proposal, negotiation,
               closed_won, closed_lost).
        value: Deal monetary value (optional).
        description: Free-text description (optional).
    """
    payload = {"name": name, "stage": stage}
    if value is not None:
        payload["value"] = str(value)
    if description:
        payload["description"] = description

    async with httpx.AsyncClient() as client:
        response = await client.post(f"{_API_BASE}/deals/", json=payload)
        response.raise_for_status()
        return response.json()


@tool
async def search_contacts(company: Optional[str] = None, limit: int = 10) -> list:
    """Search CRM contacts, optionally filtered by company name."""
    async with httpx.AsyncClient() as client:
        params = {"limit": limit}
        response = await client.get(f"{_API_BASE}/contacts/", params=params)
        response.raise_for_status()
        contacts = response.json()
        if company:
            contacts = [
                c for c in contacts
                if company.lower() in (c.get("company") or "").lower()
            ]
        return contacts


# Registry of all available CRM tools for use in LangGraph graphs
CRM_TOOLS = [get_deal, list_deals, create_deal, search_contacts]
