"""JWT HS256 token creation/validation and API key authentication."""
import hmac
from datetime import datetime, timezone, timedelta

import jwt
from fastapi import HTTPException, Security, status
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


# GAP-02: server-to-server API key authentication for ra-med-bot → Customer Runtime calls
_api_key_header = APIKeyHeader(name="X-Regula-API-Key", auto_error=False)


async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> str:
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
    return api_key
