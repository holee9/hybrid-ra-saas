"""FastAPI dependency functions."""
from typing import AsyncGenerator

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_async_session
from app.services.parser import EngineParserService, ParserService


async def get_current_tenant(
    authorization: str | None = Header(default=None, description="Bearer <token>"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    """Validate Bearer JWT and return tenant_id.

    Raises:
        401 — missing, malformed, or expired token
        403 — tenant_id in token does not match X-Tenant-ID header
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    token_tenant = payload.get("tenant_id")
    if token_tenant != x_tenant_id:
        raise HTTPException(status_code=403, detail="Tenant ID mismatch")

    return x_tenant_id


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an AsyncSession."""
    async for session in get_async_session():
        yield session


def get_parser() -> ParserService:
    """FastAPI dependency: return the real parser service backed by ParserEngine."""
    return EngineParserService()


# ---------------------------------------------------------------------------
# SPEC-PERMISSION-001: User auth dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    authorization: str | None = Header(default=None, description="Bearer <token>"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    """Validate Bearer JWT and return the active User from DB.

    # @MX:ANCHOR: [AUTO] Primary user auth gate — called by every user-facing endpoint.
    # @MX:REASON: Checks is_active on every request; JWT validity alone is not sufficient.

    Raises:
        401 — missing, malformed, expired token, or inactive user
        403 — tenant mismatch
    """
    from app.models.user import User

    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    token_tenant = payload.get("tenant_id")
    if token_tenant != x_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant ID mismatch")

    user_id = payload.get("sub")
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == x_tenant_id)
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: str):
    """Dependency factory: require the current user to have one of the given roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(user=Depends(get_current_user)) -> None:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {roles}. Current role: {user.role}",
            )
    return _check
