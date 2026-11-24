"""
DealForge Backend — Contacts API Endpoints (v1).
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.db.session import get_db
from app.models.contact import Contact
from app.models.identity import User, UserRole
from app.schemas.contact import ContactCreate, ContactRead, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["Contacts"])


@router.get("/", response_model=List[ContactRead], summary="List all contacts")
async def list_contacts(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[Contact]:
    result = await db.execute(
        select(Contact)
        .where(Contact.organization_id == user.organization_id)
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.post("/", response_model=ContactRead, status_code=status.HTTP_201_CREATED, summary="Create a contact")
async def create_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
    ),
) -> Contact:
    contact = Contact(**payload.model_dump(), organization_id=user.organization_id)
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactRead, summary="Get contact by ID")
async def get_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Contact:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == user.organization_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id!r} not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactRead, summary="Update a contact")
async def update_contact(
    contact_id: str,
    payload: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
    ),
) -> Contact:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == user.organization_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id!r} not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    await db.flush()
    await db.refresh(contact)
    return contact


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Delete a contact",
)
async def delete_contact(
    contact_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(
        require_roles(UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
    ),
) -> Response:
    result = await db.execute(
        select(Contact).where(
            Contact.id == contact_id,
            Contact.organization_id == user.organization_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail=f"Contact {contact_id!r} not found")
    await db.delete(contact)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
