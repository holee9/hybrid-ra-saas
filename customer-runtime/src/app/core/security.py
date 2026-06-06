"""JWT HS256 token creation and validation."""
from datetime import datetime, timezone, timedelta

import jwt


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
