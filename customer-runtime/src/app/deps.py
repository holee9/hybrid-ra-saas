"""FastAPI dependency functions."""
from typing import AsyncGenerator

import jwt
from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_async_session


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
