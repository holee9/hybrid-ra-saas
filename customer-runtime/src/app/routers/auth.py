"""SPEC-PERMISSION-001: /auth/login, /auth/refresh, and /auth/logout endpoints.

Issue #41: DB-backed refresh token revocation added.
- /auth/login now issues an opaque refresh token stored (hashed) in refresh_tokens table.
- /auth/refresh verifies the raw token against DB before issuing a new access token.
- /auth/logout revokes the refresh token in DB.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_user_token,
    generate_raw_refresh_token,
    hash_token,
    verify_password,
)
from app.deps import get_db
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.permission import LogoutRequest, LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email + password.

    Returns a short-lived access token and a long-lived opaque refresh token.
    The refresh token is stored hashed in the DB for revocation support.
    """
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
    access_token = create_user_token(user.id, user.tenant_id, user.role)

    # Issue DB-backed opaque refresh token (Issue #41)
    raw_refresh, expires_at = generate_raw_refresh_token()
    db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
        revoked=False,
    )
    db.add(db_token)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.jwt_ttl_min * 60,
        refresh_token=raw_refresh,
    )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token.

    # @MX:ANCHOR: [AUTO] POST /auth/refresh — token rotation entry point. DB lookup required.
    # @MX:REASON: Refresh token validity must be verified against DB for revocation support.

    Validates the raw token against the hashed record in refresh_tokens.
    Revoked or expired tokens are rejected. Issues a new opaque refresh token
    (token rotation) and revokes the old one.
    """
    from app.config import Settings

    token_hash = hash_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()

    if db_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if db_token.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

    if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user_result = await db.execute(
        select(User).where(User.id == db_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    settings = Settings()
    new_access_token = create_user_token(user.id, user.tenant_id, user.role)

    # Token rotation: revoke old, issue new opaque refresh token
    db_token.revoked = True
    raw_refresh, expires_at = generate_raw_refresh_token()
    new_db_token = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(raw_refresh),
        expires_at=expires_at,
        revoked=False,
    )
    db.add(new_db_token)
    await db.commit()

    return TokenResponse(
        access_token=new_access_token,
        expires_in=settings.jwt_ttl_min * 60,
        refresh_token=raw_refresh,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Revoke a refresh token, invalidating the session.

    Idempotent: calling with an already-revoked or unknown token returns 204.
    """
    token_hash = hash_token(body.refresh_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalar_one_or_none()
    if db_token and not db_token.revoked:
        db_token.revoked = True
        await db.commit()
