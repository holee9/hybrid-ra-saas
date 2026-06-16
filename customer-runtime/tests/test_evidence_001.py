"""SPEC-EVIDENCE-001: Evidence Binder — TDD test suite.

AC-001 through AC-007 coverage using SQLite in-memory.
"""
import hashlib
import io
import os

# Set env before any app import
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
os.environ.setdefault("REGULA_API_KEY", "test-api-key")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def client():
    """Async httpx client backed by SQLite in-memory DB."""
    from app.main import create_app
    from app.models.base import Base
    # Import all models so SQLite schema includes evidence tables
    import app.models.evidence_binder  # noqa: F401
    import app.models.evidence_link  # noqa: F401
    import app.models.evidence_file  # noqa: F401
    import app.models.evidence_gap  # noqa: F401
    # Also need other models registered for the app
    import app.models  # noqa: F401

    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app import database as db_module
    db_module._engine = engine
    db_module._session_factory = session_factory

    from app.core.security import verify_hybrid_bearer_token

    os.environ["HYBRID_RA_API_TOKEN"] = "test-token-32-bytes-minimum-here!"
    app = create_app()
    app.dependency_overrides[verify_hybrid_bearer_token] = lambda: "test-tenant"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# AC-001: REQ-EVIDENCE-001, 002, 003 — binder create + retrieve
# ---------------------------------------------------------------------------


async def test_create_binder(client):
    resp = await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "Test Binder"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "binder_id" in data
    assert data["status"] == "draft"


async def test_create_binder_with_pack_id(client):
    resp = await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "Pack Binder", "pack_id": "pack-001"
    })
    assert resp.status_code == 201
    assert resp.json()["pack_id"] == "pack-001"


async def test_get_binder_with_gaps_summary(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    resp = await client.get(f"/api/v1/evidence-binders/{binder_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "gaps_summary" in data
    assert "gaps" in data
    assert "links" in data


# ---------------------------------------------------------------------------
# AC-002: REQ-EVIDENCE-004~008 — file upload
# ---------------------------------------------------------------------------


async def test_upload_valid_file(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    file_bytes = b"%PDF-1.4 test content"
    resp = await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("test.pdf", io.BytesIO(file_bytes), "application/pdf")}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "file_id" in data
    assert len(data["sha256"]) == 64


async def test_upload_too_large_rejected(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    # 51MB file
    large_bytes = b"x" * (51 * 1024 * 1024)
    resp = await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("big.pdf", io.BytesIO(large_bytes), "application/pdf")}
    )
    assert resp.status_code == 422


async def test_upload_invalid_format_rejected(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    resp = await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
    )
    assert resp.status_code == 422


async def test_sha256_computed_on_upload(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    content = b"test evidence content"
    expected_hash = hashlib.sha256(content).hexdigest()
    resp = await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("report.pdf", io.BytesIO(content), "application/pdf")}
    )
    assert resp.json()["sha256"] == expected_hash


async def test_list_files(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    await client.post(f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("f.pdf", io.BytesIO(b"pdf"), "application/pdf")})
    files = (await client.get(f"/api/v1/evidence-binders/{binder_id}/files")).json()
    assert len(files) == 1


# ---------------------------------------------------------------------------
# AC-003: REQ-EVIDENCE-009, 010 — link create/delete
# ---------------------------------------------------------------------------


async def test_create_link(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    resp = await client.post(f"/api/v1/evidence-binders/{binder_id}/links", json={
        "source_entity_type": "risk_control",
        "source_entity_id": "rc-001",
        "target_entity_type": "file",
        "target_ref": "file-123",
        "link_type": "verifies"
    })
    assert resp.status_code == 201
    assert "link_id" in resp.json()


async def test_delete_link(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    link_id = (await client.post(f"/api/v1/evidence-binders/{binder_id}/links", json={
        "source_entity_type": "test", "source_entity_id": "t-001",
        "target_entity_type": "file", "target_ref": "f-001", "link_type": "satisfies"
    })).json()["link_id"]
    resp = await client.delete(f"/api/v1/evidence-binders/{binder_id}/links/{link_id}")
    assert resp.status_code == 204


# ---------------------------------------------------------------------------
# AC-004: REQ-EVIDENCE-011~014 — auto gap derivation
# ---------------------------------------------------------------------------


async def test_gaps_auto_computed_on_get(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    # No links — high-risk control rc-001 has no verifying evidence → critical gap
    detail = (await client.get(f"/api/v1/evidence-binders/{binder_id}")).json()
    gaps = detail["gaps"]
    assert len(gaps) > 0
    assert any(g["severity"] == "critical" for g in gaps)


async def test_critical_gap_for_unverified_high_risk(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    gaps = (await client.get(f"/api/v1/evidence-binders/{binder_id}/gaps")).json()
    critical = [g for g in gaps if g["severity"] == "critical"]
    assert len(critical) >= 1
    assert critical[0]["gap_type"] == "unverified_high_risk"


async def test_gap_resolved_after_verifies_link(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    # Add verifies link for rc-001
    await client.post(f"/api/v1/evidence-binders/{binder_id}/links", json={
        "source_entity_type": "risk_control", "source_entity_id": "rc-001",
        "target_entity_type": "file", "target_ref": "report-001", "link_type": "verifies"
    })
    detail = (await client.get(f"/api/v1/evidence-binders/{binder_id}")).json()
    # After adding verifies link, rc-001 should no longer have unverified_high_risk critical gap
    critical_for_rc001 = [
        g for g in detail["gaps"]
        if g["entity_id"] == "rc-001" and g["severity"] == "critical"
    ]
    assert len(critical_for_rc001) == 0


async def test_gap_severity_filter(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    critical_gaps = (await client.get(
        f"/api/v1/evidence-binders/{binder_id}/gaps?severity=critical"
    )).json()
    assert all(g["severity"] == "critical" for g in critical_gaps)


# ---------------------------------------------------------------------------
# AC-006: REQ-EVIDENCE-016, 017 — seal + immutability
# ---------------------------------------------------------------------------


async def test_seal_binder(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    resp = await client.post(f"/api/v1/evidence-binders/{binder_id}/seal")
    assert resp.status_code == 200
    assert resp.json()["status"] == "sealed"


async def test_sealed_binder_rejects_link_add(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    await client.post(f"/api/v1/evidence-binders/{binder_id}/seal")
    resp = await client.post(f"/api/v1/evidence-binders/{binder_id}/links", json={
        "source_entity_type": "test", "source_entity_id": "t-x",
        "target_entity_type": "file", "target_ref": "f-x", "link_type": "satisfies"
    })
    assert resp.status_code == 409


async def test_sealed_binder_rejects_file_upload(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    await client.post(f"/api/v1/evidence-binders/{binder_id}/seal")
    resp = await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("r.pdf", io.BytesIO(b"pdf"), "application/pdf")}
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# AC-007: REQ-EVIDENCE-018 — ZIP export
# ---------------------------------------------------------------------------


async def test_export_zip(client):
    binder_id = (await client.post("/api/v1/evidence-binders", json={
        "product_profile_id": "pp-001", "name": "B"
    })).json()["binder_id"]
    await client.post(
        f"/api/v1/evidence-binders/{binder_id}/files",
        files={"file": ("report.pdf", io.BytesIO(b"pdf content"), "application/pdf")}
    )
    resp = await client.post(f"/api/v1/evidence-binders/{binder_id}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert "filename" in data
    assert data["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Unit tests for file_store
# ---------------------------------------------------------------------------


def test_file_validation_rejects_bad_content_type():
    from app.services.evidence.file_store import ALLOWED_CONTENT_TYPES
    assert "application/pdf" in ALLOWED_CONTENT_TYPES
    assert "application/octet-stream" not in ALLOWED_CONTENT_TYPES


def test_sha256_computation():
    content = b"test"
    assert (
        hashlib.sha256(content).hexdigest()
        == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )
