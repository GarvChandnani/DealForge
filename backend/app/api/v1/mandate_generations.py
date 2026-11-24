"""Tenant-scoped document-to-mandate generation APIs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.graph.mandate_generation import (
    DocumentProcessingError,
    build_mandate_generation_graph,
    is_mock_mode,
)
from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db.session import get_db
from app.logging_config import get_logger
from app.models.business import ActivityLog, Document
from app.models.identity import User, UserRole
from app.models.mandate_generation import MandateGeneration
from app.schemas.mandate_generation import (
    MandateGenerationRead,
    MandateGenerationUpdate,
)

router = APIRouter(prefix="/mandate-generations", tags=["Mandate Generation"])
logger = get_logger("mandate_generation")
WRITERS = (UserRole.ADMIN, UserRole.ORIGINATOR, UserRole.ANALYST)
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
ALLOWED_SUFFIXES = {".pdf", ".docx"}


def _safe_storage_path(storage_key: str) -> Path:
    root = get_settings().document_storage_dir.resolve()
    path = (root / storage_key).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Source document was not found") from exc
    return path


async def _get_generation(
    db: AsyncSession, generation_id: str, organization_id: str
) -> MandateGeneration:
    result = await db.execute(
        select(MandateGeneration).where(
            MandateGeneration.id == generation_id,
            MandateGeneration.organization_id == organization_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail="Generation record was not found")
    return record


async def _read_generation(
    db: AsyncSession, record: MandateGeneration
) -> MandateGenerationRead:
    document_result = await db.execute(
        select(Document.name).where(
            Document.id == record.source_document_id,
            Document.organization_id == record.organization_id,
        )
    )
    document_name = document_result.scalar_one_or_none()
    if document_name is None:
        raise HTTPException(status_code=404, detail="Source document was not found")
    return MandateGenerationRead(
        id=record.id,
        source_document_id=record.source_document_id,
        source_document_name=document_name,
        status=record.status,
        processing_mode=record.processing_mode,
        extracted_data=record.extracted_data,
        financial_analysis=record.financial_analysis,
        deal_proposal=record.deal_proposal,
        mandate_draft=record.mandate_draft,
        teaser_draft=record.teaser_draft,
        quality_review=record.quality_review,
        agent_history=record.agent_history,
        error_message=record.error_message,
        approved_by_id=record.approved_by_id,
        approved_at=record.approved_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _activity(user: User, record: MandateGeneration, action: str) -> ActivityLog:
    return ActivityLog(
        organization_id=user.organization_id,
        actor_user_id=user.id,
        action=action,
        entity_type="mandate_generation",
        entity_id=record.id,
        details={"source_document_id": record.source_document_id},
    )


@router.get("/", response_model=list[MandateGenerationRead])
async def list_generations(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MandateGenerationRead]:
    result = await db.execute(
        select(MandateGeneration)
        .where(MandateGeneration.organization_id == user.organization_id)
        .order_by(MandateGeneration.updated_at.desc())
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 100))
    )
    return [
        await _read_generation(db, record)
        for record in result.scalars().all()
    ]


@router.post(
    "/",
    response_model=MandateGenerationRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> MandateGenerationRead:
    file_name = Path(file.filename or "").name
    suffix = Path(file_name).suffix.lower()
    if not file_name or suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=415,
            detail="Only PDF and DOCX source documents are supported.",
        )
    content = await file.read(MAX_DOCUMENT_BYTES + 1)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(status_code=413, detail="Document exceeds the 10 MB limit.")
    if not content:
        raise HTTPException(status_code=422, detail="The uploaded document is empty.")

    document_id = str(uuid.uuid4())
    storage_key = f"{user.organization_id}/mandate-generation/{document_id}{suffix}"
    storage_path = _safe_storage_path(storage_key)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(content)
    document = Document(
        id=document_id,
        organization_id=user.organization_id,
        name=file_name[:255],
        storage_key=storage_key,
        content_type=file.content_type,
        size_bytes=len(content),
        uploaded_by_id=user.id,
    )
    db.add(document)
    record = MandateGeneration(
        organization_id=user.organization_id,
        source_document_id=document_id,
        created_by_id=user.id,
        status="uploaded",
    )
    db.add(record)
    try:
        await db.flush()
        db.add(_activity(user, record, "mandate_generation.uploaded"))
        await db.refresh(record)
        return await _read_generation(db, record)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise


@router.get("/{generation_id}", response_model=MandateGenerationRead)
async def get_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MandateGenerationRead:
    record = await _get_generation(db, generation_id, user.organization_id)
    return await _read_generation(db, record)


@router.get("/{generation_id}/source", response_class=FileResponse)
async def download_source_document(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FileResponse:
    record = await _get_generation(db, generation_id, user.organization_id)
    document_result = await db.execute(
        select(Document).where(
            Document.id == record.source_document_id,
            Document.organization_id == user.organization_id,
        )
    )
    document = document_result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Source document was not found")
    path = _safe_storage_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Source document file was not found")
    return FileResponse(
        path,
        media_type=document.content_type or "application/octet-stream",
        filename=document.name,
    )


@router.post(
    "/{generation_id}/process",
    response_model=MandateGenerationRead,
)
async def process_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> MandateGenerationRead:
    record = await _get_generation(db, generation_id, user.organization_id)
    if record.status not in {"uploaded", "failed"}:
        raise HTTPException(
            status_code=409,
            detail="Only uploaded or failed records can be processed.",
        )
    document_result = await db.execute(
        select(Document).where(
            Document.id == record.source_document_id,
            Document.organization_id == user.organization_id,
        )
    )
    document = document_result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Source document was not found")
    path = _safe_storage_path(document.storage_key)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Source document file was not found")

    mode = "mock" if is_mock_mode() else "litellm"
    record_id = record.id
    record.status = "processing"
    record.processing_mode = mode
    record.error_message = None
    record.agent_history = [
        *record.agent_history,
        {
            "agent": "workflow",
            "status": "started",
            "mode": mode,
            "started_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    await db.commit()

    try:
        result = await build_mandate_generation_graph().ainvoke(
            {
                "source_document_id": document.id,
                "source_file_name": document.name,
                "source_content": path.read_bytes(),
                "mode": mode,
                "agent_history": record.agent_history,
            }
        )
        record.extracted_data = result["extraction"]
        record.financial_analysis = result["financial_analysis"]
        record.deal_proposal = result["deal_proposal"]
        record.mandate_draft = result["mandate_draft"]
        record.teaser_draft = result["teaser_draft"]
        record.quality_review = result["quality_review"]
        record.agent_history = result["agent_history"]
        record.status = "awaiting_review"
        document.extracted_fields = result["extraction"]["facts"]
        db.add(_activity(user, record, "mandate_generation.processed"))
        await db.commit()
        await db.refresh(record)
        return await _read_generation(db, record)
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "mandate_generation_failed",
            generation_id=record_id,
            organization_id=user.organization_id,
        )
        failed_record = await _get_generation(db, generation_id, user.organization_id)
        failed_record.status = "failed"
        if isinstance(exc, DocumentProcessingError):
            failed_record.error_message = str(exc)
        else:
            failed_record.error_message = (
                "AI processing failed. Check the provider configuration and retry."
            )
        failed_record.agent_history = [
            *failed_record.agent_history,
            {
                "agent": "workflow",
                "status": "failed",
                "message": failed_record.error_message,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        await db.commit()
        raise HTTPException(
            status_code=422 if isinstance(exc, DocumentProcessingError) else 502,
            detail=failed_record.error_message,
        ) from exc


@router.patch("/{generation_id}", response_model=MandateGenerationRead)
async def update_drafts(
    generation_id: str,
    payload: MandateGenerationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> MandateGenerationRead:
    record = await _get_generation(db, generation_id, user.organization_id)
    if record.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail="Drafts can only be edited while awaiting human review.",
        )
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one draft to edit.")
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Draft contents cannot be null.")
    for field, value in updates.items():
        if value is not None:
            setattr(record, field, value)
    record.agent_history = [
        *record.agent_history,
        {
            "agent": "human_editor",
            "status": "completed",
            "summary": "A reviewer edited one or more draft documents.",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    db.add(_activity(user, record, "mandate_generation.drafts_edited"))
    await db.flush()
    await db.refresh(record)
    return await _read_generation(db, record)


@router.post("/{generation_id}/approve", response_model=MandateGenerationRead)
async def approve_generation(
    generation_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(*WRITERS)),
) -> MandateGenerationRead:
    record = await _get_generation(db, generation_id, user.organization_id)
    if record.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail="Only drafts awaiting review can be approved.",
        )
    if not record.mandate_draft or not record.teaser_draft:
        raise HTTPException(
            status_code=409,
            detail="Both draft documents must contain content before approval.",
        )
    review = record.quality_review or {}
    if review.get("unsupported_claims") or review.get("contradictions"):
        raise HTTPException(
            status_code=409,
            detail="Resolve unsupported claims and source contradictions before approval.",
        )
    record.status = "approved"
    record.approved_by_id = user.id
    record.approved_at = datetime.now(timezone.utc)
    record.agent_history = [
        *record.agent_history,
        {
            "agent": "human_approval",
            "status": "approved",
            "approved_by_id": user.id,
            "approved_at": record.approved_at.isoformat(),
        },
    ]
    db.add(_activity(user, record, "mandate_generation.approved"))
    await db.flush()
    await db.refresh(record)
    return await _read_generation(db, record)
