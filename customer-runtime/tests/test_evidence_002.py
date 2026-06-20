"""SPEC-EVIDENCE-002: Evidence Export Real Bytes + MinIO Delete — TDD test suite.

REQ-EVIDENCE-002-001 through REQ-EVIDENCE-002-008 coverage.
Tests use mocks to avoid MinIO network dependency.
"""
from __future__ import annotations

import io
import json
import os
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

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

import pytest

from app.services.evidence.exporter import _extract_binder_id_from_ref, export_zip


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_binder(binder_id: str = "binder-001") -> SimpleNamespace:
    return SimpleNamespace(
        binder_id=binder_id,
        product_profile_id="pp-001",
        pack_id=None,
        name="Test Binder",
        status="draft",
        created_by="system",
        sealed_at=None,
    )


def _make_file(
    file_id: str = "file-001",
    filename: str = "report.pdf",
    binder_id: str = "binder-001",
    sha256: str = "abc123",
) -> SimpleNamespace:
    return SimpleNamespace(
        file_id=file_id,
        original_filename=filename,
        content_type="application/pdf",
        size_bytes=100,
        sha256=sha256,
        storage_ref=f"local/evidence/{binder_id}/uuid-123/{filename}",
    )


def _make_storage(download_bytes: bytes = b"real-file-content") -> AsyncMock:
    storage = AsyncMock()
    storage.download = AsyncMock(return_value=download_bytes)
    storage.delete = AsyncMock()
    return storage


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-001: real bytes included
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_uses_real_bytes():
    """REQ-EVIDENCE-002-001: ZIP contains real file bytes from MinIO, not sha256 stub."""
    binder = _make_binder()
    evidence_file = _make_file()
    real_content = b"PDF file real bytes"
    storage = _make_storage(download_bytes=real_content)

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[evidence_file],
        storage=storage,
    )

    storage.download.assert_awaited_once_with(evidence_file.storage_ref)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        extracted = zf.read(f"files/{evidence_file.original_filename}")
    assert extracted == real_content, "ZIP must contain real bytes, not sha256 stub"


@pytest.mark.asyncio
async def test_export_zip_manifest_contains_included_list():
    """REQ-EVIDENCE-002-007: manifest has 'export_summary.included' with file info."""
    binder = _make_binder()
    evidence_file = _make_file()
    storage = _make_storage()

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[evidence_file],
        storage=storage,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("manifest.json"))

    summary = manifest["export_summary"]
    assert summary["included_count"] == 1
    assert summary["failed_count"] == 0
    assert any(e["file_id"] == evidence_file.file_id for e in summary["included"])


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-002: missing object → manifest failed entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_missing_object_recorded_in_manifest():
    """REQ-EVIDENCE-002-002: object not found in MinIO → logged + manifest failed entry."""
    binder = _make_binder()
    evidence_file = _make_file()

    storage = AsyncMock()
    storage.download = AsyncMock(side_effect=Exception("NoSuchKey: the specified key does not exist"))

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[evidence_file],
        storage=storage,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("manifest.json"))

    summary = manifest["export_summary"]
    assert summary["failed_count"] == 1
    assert summary["included_count"] == 0
    failed_entry = summary["failed"][0]
    assert failed_entry["file_id"] == evidence_file.file_id
    assert "NoSuchKey" in failed_entry["error"]


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-003: tenant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_tenant_isolation_rejects_mismatched_binder_id():
    """REQ-EVIDENCE-002-003: file whose storage_ref contains different binder_id is denied."""
    binder = _make_binder(binder_id="binder-001")

    # File with storage_ref pointing to a DIFFERENT binder
    malicious_file = SimpleNamespace(
        file_id="file-evil",
        original_filename="evil.pdf",
        content_type="application/pdf",
        size_bytes=100,
        sha256="deadbeef",
        storage_ref="local/evidence/binder-DIFFERENT/uuid-x/evil.pdf",
    )

    storage = _make_storage()

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[malicious_file],
        storage=storage,
    )

    # storage.download must NOT have been called (access denied before fetch)
    storage.download.assert_not_awaited()

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("manifest.json"))

    summary = manifest["export_summary"]
    assert summary["failed_count"] == 1
    assert summary["failed"][0]["error"] == "tenant_isolation_violation"


@pytest.mark.asyncio
async def test_export_allows_correct_binder_id():
    """REQ-EVIDENCE-002-003: file whose storage_ref matches binder_id is allowed."""
    binder = _make_binder(binder_id="binder-999")
    evidence_file = _make_file(binder_id="binder-999")
    real_bytes = b"correct tenant data"
    storage = _make_storage(download_bytes=real_bytes)

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[evidence_file],
        storage=storage,
    )

    storage.download.assert_awaited_once()
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        extracted = zf.read(f"files/{evidence_file.original_filename}")
    assert extracted == real_bytes


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-004: per-file failure continues for remaining files
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_continues_after_single_file_failure():
    """REQ-EVIDENCE-002-004: one file failure does not abort export of remaining files."""
    binder = _make_binder()
    file_ok = _make_file(file_id="file-ok", filename="ok.pdf")
    file_fail = _make_file(file_id="file-fail", filename="fail.pdf")

    ok_bytes = b"ok file content"

    async def download_side_effect(key: str) -> bytes:
        if "fail.pdf" in key:
            raise Exception("S3 connection error")
        return ok_bytes

    storage = AsyncMock()
    storage.download = AsyncMock(side_effect=download_side_effect)

    # file_ok first, file_fail second
    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[file_ok, file_fail],
        storage=storage,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        manifest = json.loads(zf.read("manifest.json"))

    # ok.pdf must be in archive, fail.pdf must not
    assert "files/ok.pdf" in names
    assert "files/fail.pdf" not in names

    summary = manifest["export_summary"]
    assert summary["included_count"] == 1
    assert summary["failed_count"] == 1


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-005 & REQ-EVIDENCE-002-008: delete executes real call + audit log
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_object_calls_boto3_delete():
    """REQ-EVIDENCE-002-005: MinioAdapter.delete calls boto3 delete_object (not no-op)."""
    from app.services.storage import StorageService
    from app.services.storage_minio import MinioAdapter

    mock_client = MagicMock()
    mock_service = StorageService(client=mock_client, bucket="test-bucket")
    adapter = MinioAdapter(service=mock_service)

    await adapter.delete("local/evidence/b-001/uuid/file.pdf")

    mock_client.delete_object.assert_called_once_with(
        Bucket="test-bucket", Key="local/evidence/b-001/uuid/file.pdf"
    )


@pytest.mark.asyncio
async def test_delete_object_audit_log_on_success(caplog):
    """REQ-EVIDENCE-002-008: successful deletion logged in audit log."""
    import logging

    from app.services.storage import StorageService
    from app.services.storage_minio import MinioAdapter

    mock_client = MagicMock()
    mock_service = StorageService(client=mock_client, bucket="test-bucket")
    adapter = MinioAdapter(service=mock_service)

    with caplog.at_level(logging.INFO, logger="app.services.storage_minio"):
        await adapter.delete("some/key")

    assert any("minio_delete_succeeded" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-006: delete failure propagated (not silenced)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_object_failure_propagates():
    """REQ-EVIDENCE-002-006: MinioAdapter.delete raises on boto3 failure (not silent no-op)."""
    from app.services.storage import StorageService
    from app.services.storage_minio import MinioAdapter

    mock_client = MagicMock()
    mock_client.delete_object.side_effect = Exception("NoSuchBucket")
    mock_service = StorageService(client=mock_client, bucket="missing-bucket")
    adapter = MinioAdapter(service=mock_service)

    with pytest.raises(Exception, match="NoSuchBucket"):
        await adapter.delete("some/key")


@pytest.mark.asyncio
async def test_delete_object_failure_logs_error(caplog):
    """REQ-EVIDENCE-002-006: delete failure emits error log before re-raising."""
    import logging

    from app.services.storage import StorageService
    from app.services.storage_minio import MinioAdapter

    mock_client = MagicMock()
    mock_client.delete_object.side_effect = RuntimeError("S3 unavailable")
    mock_service = StorageService(client=mock_client, bucket="test-bucket")
    adapter = MinioAdapter(service=mock_service)

    with caplog.at_level(logging.ERROR, logger="app.services.storage_minio"):
        with pytest.raises(RuntimeError):
            await adapter.delete("any/key")

    assert any("minio_delete_failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Unit: _extract_binder_id_from_ref helper
# ---------------------------------------------------------------------------


def test_extract_binder_id_standard_path():
    ref = "local/evidence/binder-abc/uuid-123/file.pdf"
    assert _extract_binder_id_from_ref(ref) == "binder-abc"


def test_extract_binder_id_no_evidence_segment():
    ref = "custom/path/to/file.pdf"
    assert _extract_binder_id_from_ref(ref) is None


def test_extract_binder_id_edge_case_evidence_at_end():
    ref = "prefix/evidence"
    assert _extract_binder_id_from_ref(ref) is None


# ---------------------------------------------------------------------------
# REQ-EVIDENCE-002-001: fallback when no storage injected (backwards-compat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_fallback_stub_when_no_storage():
    """Backwards-compat: when storage=None, sha256 stub used (no regression on old callers)."""
    binder = _make_binder()
    evidence_file = _make_file()

    zip_bytes = await export_zip(
        binder=binder,
        links=[],
        files=[evidence_file],
        storage=None,
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        extracted = zf.read(f"files/{evidence_file.original_filename}")
    assert extracted == f"sha256:{evidence_file.sha256}\n".encode()
