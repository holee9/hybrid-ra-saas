"""JWT HS256 token creation/validation and API key authentication.

SPEC-PERMISSION-001 additions:
  - hash_password / verify_password  (bcrypt direct — passlib removed, incompatible with bcrypt>=4)
  - create_user_token                (JWT with role claim)
  - create_refresh_token             (longer-lived JWT)

The original create_token, decode_token, and verify_api_key are FROZEN and
must NOT be modified.
"""
import hmac
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from fastapi import Header, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader


def _get_secret() -> str:
    from app.config import Settings
    return Settings().jwt_secret


def create_token(user_id: str, tenant_id: str, ttl_min: int = 60) -> str:
    """Create a signed JWT with sub and tenant_id claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_min),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    return jwt.decode(token, _get_secret(), algorithms=["HS256"])


def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt.

    # @MX:ANCHOR: [AUTO] Password hashing entry point for all user creation paths.
    # @MX:REASON: Called by user creation endpoint and test helpers; bcrypt is mandatory.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_user_token(
    user_id: str,
    tenant_id: str,
    role: str,
    ttl_min: int | None = None,
) -> str:
    """Create a signed JWT with sub, tenant_id, and role claims (SPEC-PERMISSION-001).

    # @MX:ANCHOR: [AUTO] User-facing JWT factory — includes role claim for RBAC.
    # @MX:REASON: get_current_user, /auth/login, /auth/refresh all depend on this.
    """
    from app.config import Settings

    effective_ttl = ttl_min if ttl_min is not None else Settings().jwt_ttl_min
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=effective_ttl),
    }
    return jwt.encode(payload, _get_secret(), algorithm="HS256")


def create_refresh_token(user_id: str, tenant_id: str, role: str) -> str:
    """Create a long-lived refresh token (SPEC-PERMISSION-001)."""
    from app.config import Settings

    ttl = Settings().jwt_refresh_ttl_min
    return create_user_token(user_id, tenant_id, role, ttl_min=ttl)


# GAP-02: server-to-server API key authentication for ra-med-bot → Customer Runtime calls
_api_key_header = APIKeyHeader(name="X-Regula-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    """FastAPI dependency: validate X-Regula-API-Key header.

    # @MX:ANCHOR: [AUTO] Auth boundary for ra-med-bot → Customer Runtime (GAP-02).
    # @MX:REASON: Used by any endpoint that accepts server-to-server calls from Regula SaaS.

    Raises:
        503 if REGULA_API_KEY is not configured on this runtime.
        401 if the key is missing or does not match.
    """
    from app.config import Settings
    expected = Settings().regula_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication not configured on this runtime",
        )
    if not api_key or not hmac.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Regula-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    allowed_tenants = Settings().regula_allowed_tenants_set
    if allowed_tenants and x_tenant_id not in allowed_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not allowed for Regula API key access",
        )
    return api_key
