"""Tenant-scoped deal pipeline, activity, and document APIs."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db.session import get_db
from app.models.business import ActivityLog, Client, Document
from app.models.contact import Contact
from app.models.deal import Deal
from app.models.identity import Originator, User, UserRole
from app.schemas.deal import (
    DealActivityRead,
    DealCreate,
    DealDocumentRead,
    DealRead,
    DealUpdate,
)

router = APIRouter(prefix="/deals", tags=["Deals"])
WRITERS = (UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}


async def _get_deal(db: AsyncSession, deal_id: str, organization_id: str) -> Deal:
    result = await db.execute(
        select(Deal).where(
            Deal.id == deal_id,
            Deal.organization_id == organization_id,
        )
    )
    deal = result.scalar_one_or_none()
    if deal is None:
        raise HTTPException(status_code=404, detail=f"Deal {deal_id!r} not found")
    return deal


async def _validate_references(
    db: AsyncSession, organization_id: str, payload: dict[str, Any]
) -> None:
    for field, model in (
        ("contact_id", Contact),
        ("client_id", Client),
        ("originator_id", Originator),
    ):
        record_id = payload.get(field)
        if record_id is None:
            continue
        result = await db.execute(
            select(model.id).where(
                model.id == record_id,
                model.organization_id == organization_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail=f"{field} was not found")


def _activity(
    user: User, action: str, deal_id: str, details: dict[str, Any]
) -> ActivityLog:
    return ActivityLog(
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=action,
        entity_type="deal",
        entity_id=deal_id,
        details=details,
    )


@router.get("/", response_model=list[DealRead], summary="List all deals")
async def list_deals(
    skip: int = 0,
    limit: int = 20,
    stage: str | None = None,
    sector: str | None = None,
    originator_id: str | None = None,
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Deal]:
    query = select(Deal).where(Deal.organization_id == user.organization_id)
    if stage:
        query = query.where(Deal.stage == stage)
    if originator_id:
        query = query.where(Deal.originator_id == originator_id)
    if sector:
        query = query.outerjoin(Client, Deal.client_id == Client.id).where(
            or_(
                Deal.sector == sector,
                Client.sector == sector,
                Client.industry == sector,
            )
        ).distinct()
    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                Deal.name.ilike(term),
                Deal.company_name.ilike(term),
                Deal.description.ilike(term),
            )
        )
    result = await db.execute(
        query.order_by(Deal.updated_at.desc()).offset(max(skip, 0)).limit(min(limit, 200))
    )
    return list(result.scalars().all())


@router.post(
    "/", response_model=DealRead, status_code=status.HTTP_201_CREATED, summary="Create a deal"
)
async def create_deal(
    payload: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Deal:
    values = payload.model_dump()
    await _validate_references(db, user.organization_id, values)
    if values["transaction_size"] is not None and values["value"] is None:
        values["value"] = values["transaction_size"]
    elif values["value"] is not None and values["transaction_size"] is None:
        values["transaction_size"] = values["value"]
    deal = Deal(**values, organization_id=user.organization_id, created_by_id=user.id)
    db.add(deal)
    await db.flush()
    db.add(_activity(user, "deal.created", deal.id, {"name": deal.name, "stage": deal.stage}))
    await db.refresh(deal)
    return deal


@router.get("/{deal_id}", response_model=DealRead, summary="Get a deal by ID")
async def get_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Deal:
    return await _get_deal(db, deal_id, user.organization_id)


@router.patch("/{deal_id}", response_model=DealRead, summary="Update a deal")
async def update_deal(
    deal_id: str,
    payload: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Deal:
    deal = await _get_deal(db, deal_id, user.organization_id)
    updates = payload.model_dump(exclude_unset=True)
    await _validate_references(db, user.organization_id, updates)
    if "transaction_size" in updates and "value" not in updates:
        updates["value"] = updates["transaction_size"]
    elif "value" in updates and "transaction_size" not in updates:
        updates["transaction_size"] = updates["value"]
    changes: dict[str, dict[str, str | None]] = {}
    for field, value in updates.items():
        previous = getattr(deal, field)
        if previous != value:
            changes[field] = {
                "from": str(previous) if previous is not None else None,
                "to": str(value) if value is not None else None,
            }
            setattr(deal, field, value)
    if changes:
        db.add(_activity(user, "deal.updated", deal.id, {"changes": changes}))
    await db.flush()
    await db.refresh(deal)
    return deal


@router.delete(
    "/{deal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    summary="Delete a deal",
)
async def delete_deal(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Response:
    deal = await _get_deal(db, deal_id, user.organization_id)
    db.add(_activity(user, "deal.deleted", deal.id, {"name": deal.name}))
    result = await db.execute(
        select(Document).where(
            Document.deal_id == deal.id,
            Document.organization_id == user.organization_id,
        )
    )
    documents = list(result.scalars().all())
    await db.delete(deal)
    await db.flush()
    storage_root = get_settings().document_storage_dir.resolve()
    for document in documents:
        storage_path = (storage_root / document.storage_key).resolve()
        if storage_root in storage_path.parents and storage_path.is_file():
            storage_path.unlink()
        await db.delete(document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{deal_id}/activity", response_model=list[DealActivityRead])
async def list_deal_activity(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ActivityLog]:
    await _get_deal(db, deal_id, user.organization_id)
    result = await db.execute(
        select(ActivityLog)
        .where(
            ActivityLog.entity_type == "deal",
            ActivityLog.entity_id == deal_id,
            ActivityLog.organization_id == user.organization_id,
        )
        .order_by(ActivityLog.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{deal_id}/documents", response_model=list[DealDocumentRead])
async def list_deal_documents(
    deal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    await _get_deal(db, deal_id, user.organization_id)
    result = await db.execute(
        select(Document)
        .where(
            Document.deal_id == deal_id,
            Document.organization_id == user.organization_id,
        )
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/{deal_id}/documents",
    response_model=DealDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_deal_document(
    deal_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Document:
    deal = await _get_deal(db, deal_id, user.organization_id)
    original_name = Path(file.filename or "").name
    suffix = Path(original_name).suffix.lower()
    if not original_name or suffix not in ALLOWED_DOCUMENT_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail=f"File type is not supported. Allowed: {', '.join(sorted(ALLOWED_DOCUMENT_SUFFIXES))}",
        )
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB limit")

    storage_key = f"{user.organization_id}/{uuid.uuid4().hex}{suffix}"
    storage_path = get_settings().document_storage_dir / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)
    document = Document(
        name=original_name,
        storage_key=storage_key,
        content_type=file.content_type,
        size_bytes=len(content),
        deal_id=deal.id,
        uploaded_by_id=user.id,
        organization_id=user.organization_id,
    )
    db.add(document)
    try:
        await db.flush()
        db.add(_activity(user, "deal.document_uploaded", deal.id, {"name": original_name}))
        await db.refresh(document)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise
    return document


@router.delete(
    "/{deal_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_deal_document(
    deal_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Response:
    deal = await _get_deal(db, deal_id, user.organization_id)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.deal_id == deal.id,
            Document.organization_id == user.organization_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    storage_root = get_settings().document_storage_dir.resolve()
    storage_path = (storage_root / document.storage_key).resolve()
    if storage_root not in storage_path.parents:
        raise HTTPException(status_code=400, detail="Invalid document storage path")
    db.add(_activity(user, "deal.document_deleted", deal.id, {"name": document.name}))
    await db.delete(document)
    await db.flush()
    if storage_path.is_file():
        storage_path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{deal_id}/documents/{document_id}/file",
    response_class=FileResponse,
)
async def download_deal_document(
    deal_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    await _get_deal(db, deal_id, user.organization_id)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.deal_id == deal_id,
            Document.organization_id == user.organization_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    storage_root = get_settings().document_storage_dir.resolve()
    storage_path = (storage_root / document.storage_key).resolve()
    if storage_root not in storage_path.parents or not storage_path.is_file():
        raise HTTPException(status_code=404, detail="Document file was not found")
    return FileResponse(
        storage_path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.name,
    )
