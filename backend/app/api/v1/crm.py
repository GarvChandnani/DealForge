"""Tenant-scoped originator, client, and client interaction APIs."""

from __future__ import annotations

import uuid
from pathlib import Path
import re

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db.session import get_db
from app.models.business import Client, ClientInteraction, ComplianceRecord, Document, Mandate
from app.models.identity import Originator, User, UserRole
from app.schemas.crm import (
    ClientCreate,
    ClientDocumentRead,
    ClientInteractionCreate,
    ClientInteractionRead,
    ClientRead,
    ClientUpdate,
    OriginatorCreate,
    OriginatorRead,
    OriginatorUpdate,
    VerificationCheckCreate,
    VerificationCheckRead,
    MandateRead,
)

router = APIRouter(tags=["CRM"])
WRITERS = (UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_DOCUMENT_SUFFIXES = {".pdf", ".docx", ".txt", ".csv", ".xlsx"}
SUPPORTED_VERIFICATION_CHECKS = {"mca", "din", "kyc", "aml"}


async def _get_tenant_record(db: AsyncSession, model, record_id: str, org_id: str):
    result = await db.execute(
        select(model).where(model.id == record_id, model.organization_id == org_id)
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} was not found")
    return record


async def _validate_originator(
    db: AsyncSession, organization_id: str, originator_id: str | None
) -> None:
    if originator_id is None:
        return
    await _get_tenant_record(db, Originator, originator_id, organization_id)


def _extract_company_fields(suffix: str, content: bytes) -> dict[str, str] | None:
    if suffix not in {".txt", ".csv"}:
        return None
    text = content[:2 * 1024 * 1024].decode("utf-8-sig", errors="replace")
    labels = {
        "company": "company_name",
        "company name": "company_name",
        "company_name": "company_name",
        "sector": "sector",
        "industry": "industry",
        "location": "location",
        "revenue": "revenue",
        "annual revenue": "revenue",
        "turnover": "turnover",
        "annual turnover": "turnover",
        "funding requirement": "funding_requirement",
        "funding_requirement": "funding_requirement",
        "email": "contact_email",
        "contact email": "contact_email",
        "phone": "phone",
    }
    extracted: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*([^,:=]+)\s*[:,=]\s*(.*?)\s*$", line)
        if not match:
            continue
        key = re.sub(r"\s+", " ", match.group(1).strip().lower())
        value = match.group(2).strip()
        if key in labels and value:
            extracted[labels[key]] = value[:500]
    return extracted


@router.get("/mandates/", response_model=list[MandateRead])
async def list_mandates(
    originator_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Mandate]:
    query = select(Mandate).where(Mandate.organization_id == user.organization_id)
    if originator_id:
        query = query.where(Mandate.originator_id == originator_id)
    result = await db.execute(query.order_by(Mandate.created_at.desc()))
    return list(result.scalars().all())


@router.get("/originators/", response_model=list[OriginatorRead])
async def list_originators(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Originator]:
    result = await db.execute(
        select(Originator)
        .where(Originator.organization_id == user.organization_id)
        .order_by(Originator.created_at.desc())
        .offset(skip)
        .limit(min(limit, 200))
    )
    return list(result.scalars().all())


@router.post(
    "/originators/",
    response_model=OriginatorRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_originator(
    payload: OriginatorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Originator:
    values = payload.model_dump()
    linked_user_id = values.pop("user_id")
    if linked_user_id is not None:
        linked_user = await _get_tenant_record(
            db, User, linked_user_id, user.organization_id
        )
        existing = await db.execute(
            select(Originator.id).where(Originator.user_id == linked_user.id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="User already has an originator profile")
    originator = Originator(
        **values, user_id=linked_user_id, organization_id=user.organization_id
    )
    db.add(originator)
    await db.flush()
    await db.refresh(originator)
    return originator


@router.get("/originators/{originator_id}", response_model=OriginatorRead)
async def get_originator(
    originator_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Originator:
    return await _get_tenant_record(db, Originator, originator_id, user.organization_id)


@router.patch("/originators/{originator_id}", response_model=OriginatorRead)
async def update_originator(
    originator_id: str,
    payload: OriginatorUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Originator:
    originator = await _get_tenant_record(db, Originator, originator_id, user.organization_id)
    updates = payload.model_dump(exclude_unset=True)
    if "user_id" in updates:
        linked_user_id = updates["user_id"]
        if linked_user_id is not None:
            await _get_tenant_record(db, User, linked_user_id, user.organization_id)
            duplicate = await db.execute(
                select(Originator.id).where(
                    Originator.user_id == linked_user_id,
                    Originator.id != originator.id,
                )
            )
            if duplicate.scalar_one_or_none():
                raise HTTPException(
                    status_code=409, detail="User already has an originator profile"
                )
    for field, value in updates.items():
        setattr(originator, field, value)
    await db.flush()
    await db.refresh(originator)
    return originator


@router.delete(
    "/originators/{originator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_originator(
    originator_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Response:
    originator = await _get_tenant_record(db, Originator, originator_id, user.organization_id)
    await db.delete(originator)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/clients/", response_model=list[ClientRead])
async def list_clients(
    skip: int = 0,
    limit: int = 100,
    status_filter: str | None = None,
    sector: str | None = None,
    originator_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Client]:
    query = select(Client).where(Client.organization_id == user.organization_id)
    if status_filter:
        query = query.where(Client.status == status_filter)
    if sector:
        query = query.where((Client.sector == sector) | (Client.industry == sector))
    if originator_id:
        query = query.where(Client.assigned_originator_id == originator_id)
    result = await db.execute(
        query.order_by(Client.created_at.desc()).offset(skip).limit(min(limit, 200))
    )
    return list(result.scalars().all())


@router.post("/clients/", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Client:
    values = payload.model_dump()
    await _validate_originator(db, user.organization_id, values["assigned_originator_id"])
    client = Client(**values, organization_id=user.organization_id)
    db.add(client)
    await db.flush()
    await db.refresh(client)
    return client


@router.get("/clients/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Client:
    return await _get_tenant_record(db, Client, client_id, user.organization_id)


@router.patch("/clients/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: str,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Client:
    client = await _get_tenant_record(db, Client, client_id, user.organization_id)
    updates = payload.model_dump(exclude_unset=True)
    if "assigned_originator_id" in updates:
        await _validate_originator(db, user.organization_id, updates["assigned_originator_id"])
    for field, value in updates.items():
        setattr(client, field, value)
    await db.flush()
    await db.refresh(client)
    return client


@router.delete(
    "/clients/{client_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_client(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Response:
    client = await _get_tenant_record(db, Client, client_id, user.organization_id)
    await db.delete(client)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/clients/{client_id}/interactions", response_model=list[ClientInteractionRead])
async def list_client_interactions(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ClientInteraction]:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    result = await db.execute(
        select(ClientInteraction)
        .where(
            ClientInteraction.client_id == client_id,
            ClientInteraction.organization_id == user.organization_id,
        )
        .order_by(ClientInteraction.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/clients/{client_id}/interactions",
    response_model=ClientInteractionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_client_interaction(
    client_id: str,
    payload: ClientInteractionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> ClientInteraction:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    interaction = ClientInteraction(
        **payload.model_dump(),
        client_id=client_id,
        user_id=user.id,
        organization_id=user.organization_id,
    )
    db.add(interaction)
    await db.flush()
    await db.refresh(interaction)
    return interaction


@router.get(
    "/clients/{client_id}/documents", response_model=list[ClientDocumentRead]
)
async def list_client_documents(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Document]:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    result = await db.execute(
        select(Document)
        .where(
            Document.client_id == client_id,
            Document.organization_id == user.organization_id,
        )
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/clients/{client_id}/documents",
    response_model=ClientDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_client_document(
    client_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> dict:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
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

    extracted_fields = _extract_company_fields(suffix, content)
    document = Document(
        name=original_name,
        storage_key=storage_key,
        content_type=file.content_type,
        size_bytes=len(content),
        extracted_fields=extracted_fields,
        client_id=client_id,
        uploaded_by_id=user.id,
        organization_id=user.organization_id,
    )
    db.add(document)
    try:
        await db.flush()
        await db.refresh(document)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise
    response = ClientDocumentRead.model_validate(document, from_attributes=True)
    return response.model_dump()


@router.delete(
    "/clients/{client_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def delete_client_document(
    client_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> Response:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.client_id == client_id,
            Document.organization_id == user.organization_id,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found")
    storage_path = get_settings().document_storage_dir / document.storage_key
    await db.delete(document)
    if storage_path.is_file():
        storage_path.unlink()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/clients/{client_id}/documents/{document_id}/file",
    response_class=FileResponse,
)
async def download_client_document(
    client_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.client_id == client_id,
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


@router.get(
    "/clients/{client_id}/verification-checks",
    response_model=list[VerificationCheckRead],
)
async def list_client_verification_checks(
    client_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ComplianceRecord]:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    result = await db.execute(
        select(ComplianceRecord)
        .where(
            ComplianceRecord.entity_type == "client",
            ComplianceRecord.entity_id == client_id,
            ComplianceRecord.organization_id == user.organization_id,
        )
        .order_by(ComplianceRecord.created_at.desc())
    )
    return list(result.scalars().all())


@router.post(
    "/clients/{client_id}/verification-checks",
    response_model=VerificationCheckRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_simulated_verification_check(
    client_id: str,
    payload: VerificationCheckCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> ComplianceRecord:
    await _get_tenant_record(db, Client, client_id, user.organization_id)
    check_type = payload.check_type.lower()
    if check_type not in SUPPORTED_VERIFICATION_CHECKS:
        raise HTTPException(
            status_code=422,
            detail=f"check_type must be one of {sorted(SUPPORTED_VERIFICATION_CHECKS)}",
        )
    record = ComplianceRecord(
        organization_id=user.organization_id,
        entity_type="client",
        entity_id=client_id,
        check_type=check_type,
        status="simulated",
        details={
            "simulated": True,
            "external_provider_configured": False,
            "message": "No external registry, identity, or screening provider was contacted.",
        },
        reviewed_by_id=user.id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record
