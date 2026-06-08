"""Rate limiting — REQ-API-014: 100 requests/minute per tenant.

Uses slowapi with tenant-aware key function.

# @MX:NOTE: [AUTO] get_tenant_id is the rate-limit key; uses X-Tenant-ID header or falls back to client IP
# @MX:REASON: business rule — rate limits are per-tenant, not per-IP, to prevent cross-tenant throttling
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_tenant_id(request: Request) -> str:
    """Rate limit key: X-Tenant-ID header if present, else client IP.

    # @MX:NOTE: [AUTO] Falling back to IP prevents unauthenticated clients from
    # exhausting the global rate limit under a single tenant key.
    """
    tenant_id = request.headers.get("X-Tenant-ID")
    if tenant_id:
        return tenant_id
    return get_remote_address(request)


limiter = Limiter(key_func=get_tenant_id)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return HTTP 429 with detail message when rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )
