"""Tests for GET /sync/manifest — REQ-API-012, FR-210.

Unit tests: mock DB, no Docker required.
Integration tests: require Docker, marked with @skip_no_docker.
"""
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import skip_no_docker


# ---------------------------------------------------------------------------
# Unit: manifest structure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manifest_returns_correct_structure():
    """Manifest response contains manifest_hash, generated_at, entries, total_count."""
    from app.services.sync import SyncService

    mock_db = AsyncMock()

    # Build fake rows for products, requirements, controls
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    fake_entity = MagicMock()
    fake_entity.entity_id = "prod-001"
    fake_entity.entity_type = "product"
    fake_entity.updated_at = now

    with patch.object(SyncService, "_fetch_entities", return_value=[
        {"entity_type": "product", "entity_id": "prod-001", "updated_at": now}
    ]):
        svc = SyncService()
        result = await svc.build_manifest(db=mock_db, tenant_id="t1", since=None)

    assert "manifest_hash" in result
    assert "generated_at" in result
    assert "entries" in result
    assert "total_count" in result
    assert result["total_count"] == 1
    assert len(result["entries"]) == 1

    entry = result["entries"][0]
    assert "entity_type" in entry
    assert "entity_id" in entry
    assert "version_hash" in entry
    assert "action" in entry
    assert "updated_at" in entry


@pytest.mark.asyncio
async def test_manifest_hash_is_sha256_of_content():
    """manifest_hash is SHA-256 of the JSON-serialized manifest content."""
    from app.services.sync import SyncService

    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_db = AsyncMock()

    with patch.object(SyncService, "_fetch_entities", return_value=[
        {"entity_type": "product", "entity_id": "prod-001", "updated_at": now}
    ]):
        svc = SyncService()
        result = await svc.build_manifest(db=mock_db, tenant_id="t1", since=None)

    # Recompute manifest_hash from the entries and verify
    entries_for_hash = json.dumps(result["entries"], default=str, sort_keys=True)
    expected_hash = hashlib.sha256(entries_for_hash.encode()).hexdigest()
    assert result["manifest_hash"] == expected_hash


@pytest.mark.asyncio
async def test_manifest_since_filter_excludes_older_items():
    """since= parameter filters out entities updated before the cutoff."""
    from app.services.sync import SyncService

    old_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    new_time = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    since_cutoff = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    mock_db = AsyncMock()

    all_entities = [
        {"entity_type": "product", "entity_id": "prod-old", "updated_at": old_time},
        {"entity_type": "product", "entity_id": "prod-new", "updated_at": new_time},
    ]

    with patch.object(SyncService, "_fetch_entities", return_value=all_entities):
        svc = SyncService()
        result = await svc.build_manifest(
            db=mock_db, tenant_id="t1", since=since_cutoff.isoformat()
        )

    entity_ids = [e["entity_id"] for e in result["entries"]]
    assert "prod-new" in entity_ids
    assert "prod-old" not in entity_ids
    assert result["total_count"] == 1


@pytest.mark.asyncio
async def test_manifest_no_sensitive_fields_in_entries():
    """Manifest entries MUST NOT contain storage_key, content, or raw document data (FR-210)."""
    from app.services.sync import SyncService

    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_db = AsyncMock()

    with patch.object(SyncService, "_fetch_entities", return_value=[
        {"entity_type": "product", "entity_id": "prod-001", "updated_at": now}
    ]):
        svc = SyncService()
        result = await svc.build_manifest(db=mock_db, tenant_id="t1", since=None)

    sensitive_fields = {"storage_key", "content", "raw_text", "file_content", "document_text"}
    for entry in result["entries"]:
        for field in sensitive_fields:
            assert field not in entry, f"Sensitive field '{field}' found in manifest entry"


@pytest.mark.asyncio
async def test_sync_manifest_endpoint_requires_auth():
    """GET /sync/manifest without auth returns 401."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_BUCKET", "ra-documents")
    os.environ.setdefault("MINIO_USER", "minioadmin")
    os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
    os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

    from httpx import AsyncClient, ASGITransport
    from app.main import create_app

    os.environ["HYBRID_RA_API_TOKEN"] = "test-token-32-bytes-minimum-here!"
    test_app = create_app()
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        resp = await ac.get("/sync/manifest", headers={"X-Tenant-ID": "t1"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sync_manifest_endpoint_returns_200():
    """GET /sync/manifest with valid auth returns 200 and correct schema."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_BUCKET", "ra-documents")
    os.environ.setdefault("MINIO_USER", "minioadmin")
    os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
    os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

    from httpx import AsyncClient, ASGITransport
    from app.services.sync import SyncService
    from app.deps import get_db
    from app.main import create_app

    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    fake_manifest = {
        "manifest_hash": "abc123",
        "generated_at": now.isoformat(),
        "entries": [],
        "total_count": 0,
    }

    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    _api_token = "test-token-32-bytes-minimum-here!"
    os.environ["HYBRID_RA_API_TOKEN"] = _api_token
    test_app = create_app()
    test_app.dependency_overrides[get_db] = override_get_db

    with patch.object(SyncService, "build_manifest", new=AsyncMock(return_value=fake_manifest)):
        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            resp = await ac.get(
                "/sync/manifest",
                headers={"Authorization": f"Bearer {_api_token}", "X-Tenant-ID": "t1"},
            )

    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "manifest_hash" in data
    assert "entries" in data


# ---------------------------------------------------------------------------
# Integration: requires Docker
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.integration
async def test_sync_manifest_integration(client):
    """Integration: GET /sync/manifest returns 200 with correct schema."""
    from app.core.security import create_token

    token = create_token(user_id="u1", tenant_id="t1")
    resp = await client.get(
        "/sync/manifest",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "t1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "manifest_hash" in data
    assert "generated_at" in data
    assert "entries" in data
    assert "total_count" in data
