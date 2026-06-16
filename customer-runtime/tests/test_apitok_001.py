"""SPEC-APITOK-001: unit tests for verify_hybrid_bearer_token dependency.

Uses a minimal probe FastAPI app (no DB) so tests are pure unit tests.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
os.environ.setdefault("MINIO_BUCKET", "ra-documents")
os.environ.setdefault("MINIO_USER", "minioadmin")
os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

_VALID_TOKEN = "test-bearer-token-secret-32-bytes!"
_TENANT = "tenant-abc"


def _probe_app(token: str = _VALID_TOKEN):
    """Minimal FastAPI app with a single /probe route protected by verify_hybrid_bearer_token.

    No DB dependency — purely tests the auth function itself.
    """
    from fastapi import FastAPI, Depends
    from app.core.security import verify_hybrid_bearer_token

    os.environ["HYBRID_RA_API_TOKEN"] = token

    probe = FastAPI()

    @probe.get("/probe")
    async def probe_route(tenant: str = Depends(verify_hybrid_bearer_token)):
        return {"tenant": tenant}

    return probe


async def _get(app, path: str, headers: dict | None = None):
    from httpx import ASGITransport, AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        return await ac.get(path, headers=headers or {})


# ---------------------------------------------------------------------------
# verify_hybrid_bearer_token unit tests (via minimal probe app — no DB needed)
# ---------------------------------------------------------------------------

PROBE = "/probe"
VALID_HEADERS = {
    "Authorization": f"Bearer {_VALID_TOKEN}",
    "X-Tenant-ID": _TENANT,
}


async def test_valid_token_returns_non_401():
    """Valid Bearer token + X-Tenant-ID must not return 401 or 503."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers=VALID_HEADERS)
    # May be 500 due to missing DB, but auth layer must pass (not 401/503)
    assert resp.status_code not in (401, 403, 503), resp.text


async def test_missing_authorization_header_returns_401():
    """No Authorization header → 401."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers={"X-Tenant-ID": _TENANT})
    assert resp.status_code == 401
    assert "Bearer" in resp.text


async def test_wrong_token_returns_401():
    """Wrong token value → 401."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers={
        "Authorization": "Bearer wrong-token",
        "X-Tenant-ID": _TENANT,
    })
    assert resp.status_code == 401


async def test_missing_tenant_id_returns_400():
    """Valid token but missing X-Tenant-ID → 400."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers={"Authorization": f"Bearer {_VALID_TOKEN}"})
    assert resp.status_code == 400


async def test_unconfigured_token_returns_503():
    """HYBRID_RA_API_TOKEN not set → 503."""
    app = _probe_app(token="")
    resp = await _get(app, PROBE, headers=VALID_HEADERS)
    assert resp.status_code == 503
    assert "not configured" in resp.text


async def test_non_bearer_scheme_returns_401():
    """Basic auth scheme (not Bearer) → 401."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers={
        "Authorization": f"ApiKey {_VALID_TOKEN}",
        "X-Tenant-ID": _TENANT,
    })
    assert resp.status_code == 401


async def test_valid_token_returns_tenant():
    """Valid Bearer token + X-Tenant-ID returns tenant in response body."""
    app = _probe_app()
    resp = await _get(app, PROBE, headers=VALID_HEADERS)
    assert resp.status_code == 200
    assert resp.json() == {"tenant": _TENANT}
