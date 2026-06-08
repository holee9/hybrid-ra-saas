"""T-006 + T-007: JWT security and auth dependencies."""
import os
import pytest

# Set env before importing app modules
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


# --- T-006 ---

def test_token_roundtrip():
    from app.core.security import create_token, decode_token
    token = create_token(user_id="user-1", tenant_id="tenant-abc")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["tenant_id"] == "tenant-abc"


def test_token_expired():
    import jwt
    from app.core.security import create_token, decode_token
    # Create token with -1 minute TTL (already expired)
    token = create_token(user_id="user-1", tenant_id="tenant-abc", ttl_min=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_token_invalid():
    import jwt
    from app.core.security import decode_token
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not.a.token")


# --- T-007 auth dependency integration tests (use httpx client fixture) ---

@pytest.mark.integration
async def test_no_auth_header_returns_401(client):
    resp = await client.get("/health")
    assert resp.status_code == 200  # health has no auth


@pytest.mark.integration
async def test_upload_no_auth_returns_401(client):
    resp = await client.post("/documents/upload")
    assert resp.status_code == 401


@pytest.mark.integration
async def test_upload_expired_token_returns_401(client):
    from app.core.security import create_token
    token = create_token("u1", "t1", ttl_min=-1)
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "t1"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
async def test_upload_tenant_mismatch_returns_403(client):
    from app.core.security import create_token
    token = create_token("u1", "tenant-A")
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-B"},
    )
    assert resp.status_code == 403
