"""SPEC-PERMISSION-001: /auth/login and /auth/refresh endpoints."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_refresh_token,
    create_user_token,
    decode_token,
    verify_password,
)
from app.deps import get_db
from app.models.user import User
from app.schemas.permission import LoginRequest, RefreshRequest, TokenResponse

import jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email + password and return JWT access token."""
    from app.config import Settings

    if not x_tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Tenant-ID header required")

    result = await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == x_tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account is inactive")

    settings = Settings()
    token = create_user_token(user.id, user.tenant_id, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_min * 60,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    body: RefreshRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access token given a valid refresh (or access) token."""
    from app.config import Settings

    try:
        payload = decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_id = payload.get("sub")
    token_tenant = payload.get("tenant_id")

    if x_tenant_id and token_tenant != x_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant ID mismatch")

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    settings = Settings()
    token = create_user_token(user.id, user.tenant_id, user.role)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_min * 60,
    )
