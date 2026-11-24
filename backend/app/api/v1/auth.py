"""Registration, login, and authenticated user profile endpoints."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_roles
from app.config import get_settings
from app.db.session import get_db
from app.logging_config import get_logger
from app.models.business import ActivityLog
from app.models.identity import Organization, Originator, User, UserRole
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    CreateUserRequest,
    OrganizationRead,
    ProfileUpdate,
    RegisterRequest,
    UserRead,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth")


def _organization_slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "organization"
    return f"{base[:200]}-{uuid.uuid4().hex[:8]}"


def _issue_auth_response(user: User, organization: Organization) -> AuthResponse:
    settings = get_settings()
    return AuthResponse(
        access_token=create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
        ),
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
        organization=OrganizationRead.model_validate(organization),
    )


async def _email_exists(db: AsyncSession, email: str) -> bool:
    result = await db.execute(select(User.id).where(User.email == email))
    return result.scalar_one_or_none() is not None


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an organization and its first administrator",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    email = str(payload.email).lower()
    if await _email_exists(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    organization = Organization(
        name=payload.organization_name.strip(),
        slug=_organization_slug(payload.organization_name),
    )
    db.add(organization)
    await db.flush()

    user = User(
        organization_id=organization.id,
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=UserRole.ADMIN.value,
    )
    db.add(user)
    await db.flush()
    db.add(
        ActivityLog(
            organization_id=organization.id,
            actor_user_id=user.id,
            action="organization.registered",
            entity_type="organization",
            entity_id=organization.id,
        )
    )
    logger.info("organization_registered", organization_id=organization.id, user_id=user.id)
    return _issue_auth_response(user, organization)


@router.post("/login", response_model=AuthResponse, summary="Exchange credentials for a JWT")
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    email = form.username.strip().lower()
    result = await db.execute(
        select(User, Organization)
        .join(Organization, User.organization_id == Organization.id)
        .where(User.email == email)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, organization = row
    if (
        not user.is_active
        or not organization.is_active
        or not verify_password(form.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.add(
        ActivityLog(
            organization_id=user.organization_id,
            actor_user_id=user.id,
            action="user.logged_in",
            entity_type="user",
            entity_id=user.id,
        )
    )
    logger.info("user_logged_in", organization_id=user.organization_id, user_id=user.id)
    return _issue_auth_response(user, organization)


@router.get("/me", response_model=UserRead, summary="Get the current user profile")
async def get_profile(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserRead, summary="Update the current user profile")
async def update_profile(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> User:
    user.full_name = payload.full_name.strip()
    db.add(
        ActivityLog(
            organization_id=user.organization_id,
            actor_user_id=user.id,
            action="user.profile_updated",
            entity_type="user",
            entity_id=user.id,
        )
    )
    return user


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    user.password_hash = hash_password(payload.new_password)
    db.add(
        ActivityLog(
            organization_id=user.organization_id,
            actor_user_id=user.id,
            action="user.password_changed",
            entity_type="user",
            entity_id=user.id,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List users in the current organization (admin only)",
)
async def list_organization_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[User]:
    result = await db.execute(
        select(User)
        .where(User.organization_id == admin.organization_id)
        .order_by(User.created_at)
    )
    return list(result.scalars().all())


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user in the current organization (admin only)",
)
async def create_organization_user(
    payload: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> User:
    email = str(payload.email).lower()
    if await _email_exists(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        organization_id=admin.organization_id,
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role.value,
    )
    db.add(user)
    await db.flush()
    if user.role == UserRole.ORIGINATOR.value:
        db.add(
            Originator(
                organization_id=admin.organization_id,
                user_id=user.id,
                full_name=user.full_name,
                email=user.email,
            )
        )
    db.add(
        ActivityLog(
            organization_id=admin.organization_id,
            actor_user_id=admin.id,
            action="user.created",
            entity_type="user",
            entity_id=user.id,
            details={"role": user.role},
        )
    )
    return user
