"""T-015: Field correction handler + before/after AuditEvent (REQ-API-006, REQ-API-011).

Unit tests only — no Docker required.
"""
import hashlib
import json
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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



def _compute_hash(values: list[str]) -> str:
    """Compute SHA-256 of sorted values."""
    data = json.dumps(sorted(values), sort_keys=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


class TestFieldCorrectionAudit:
    """Test correction creates AuditEvent with correct before/after hashes."""

    async def test_correction_creates_audit_event_with_hashes(self):
        """PATCH /documents/{doc_id}/fields -> AuditEvent with before_hash + after_hash."""
        from app.routers.documents import compute_correction_hashes

        corrections = [
            {"field_name": "title", "before_value": "Old Title", "after_value": "New Title"},
            {"field_name": "version", "before_value": "1.0", "after_value": "2.0"},
        ]

        before_hash, after_hash = compute_correction_hashes(corrections)

        expected_before = _compute_hash(["Old Title", "1.0"])
        expected_after = _compute_hash(["New Title", "2.0"])

        assert before_hash == expected_before
        assert after_hash == expected_after

    async def test_audit_event_action_is_document_field_correction(self):
        """AuditEvent action='document.field_correction' recorded on PATCH."""
        from app.routers.documents import apply_field_correction

        mock_db = AsyncMock()
        mock_audit = MagicMock(record=AsyncMock())

        # Fake document that belongs to tenant
        fake_doc = MagicMock()
        fake_doc.tenant_id = "tenant-1"
        fake_doc.status = "needs_correction"
        fake_doc.doc_id = "doc-1"

        with patch(
            "app.routers.documents._get_document_or_404",
            new=AsyncMock(return_value=fake_doc),
        ):
            result = await apply_field_correction(
                db=mock_db,
                doc_id="doc-1",
                tenant_id="tenant-1",
                user_id="user-1",
                field_corrections=[
                    {"field_name": "title", "before_value": "Old", "after_value": "New"}
                ],
                audit_service=mock_audit,
            )

        mock_audit.record.assert_called_once()
        call_kwargs = mock_audit.record.call_args
        assert call_kwargs.kwargs.get("action") == "document.field_correction" or (
            len(call_kwargs.args) > 3 and call_kwargs.args[3] == "document.field_correction"
        )
        assert result["corrections_applied"] == 1
        assert "audit_event_id" in result

    async def test_status_transition_needs_correction_to_ready_for_check(self):
        """Document in needs_correction -> ready_for_check after correction with non-empty values."""
        from app.routers.documents import apply_field_correction

        mock_db = AsyncMock()
        mock_audit = MagicMock(record=AsyncMock(return_value=MagicMock(event_id="evt-1")))

        fake_doc = MagicMock()
        fake_doc.tenant_id = "tenant-1"
        fake_doc.status = "needs_correction"
        fake_doc.doc_id = "doc-1"

        with patch(
            "app.routers.documents._get_document_or_404",
            new=AsyncMock(return_value=fake_doc),
        ):
            await apply_field_correction(
                db=mock_db,
                doc_id="doc-1",
                tenant_id="tenant-1",
                user_id="user-1",
                field_corrections=[
                    {"field_name": "title", "before_value": "Old", "after_value": "New Title"}
                ],
                audit_service=mock_audit,
            )

        # Status should be set to ready_for_check
        assert fake_doc.status == "ready_for_check"

    async def test_audit_event_update_raises_runtime_error(self):
        """AuditEvent append-only: UPDATE attempt raises RuntimeError (model-level check)."""
        from app.models.audit import _block_update

        # Directly invoke the SQLAlchemy event listener — simulates ORM update
        with pytest.raises(RuntimeError, match="append-only"):
            _block_update(None, None, MagicMock())


class TestFieldCorrectionEndpoint:
    """Test PATCH /documents/{doc_id}/fields endpoint."""

    async def test_endpoint_requires_auth(self):
        """No auth header -> 401."""
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.deps import get_db

        app = create_app()

        async def mock_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.patch(
                "/documents/doc-1/fields",
                json={
                    "field_corrections": [
                        {"field_name": "title", "before_value": "Old", "after_value": "New"}
                    ],
                    "user_id": "user-1",
                },
            )
        assert resp.status_code == 401

    async def test_endpoint_returns_200_with_valid_request(self):
        """Valid PATCH request -> 200 with doc_id, corrections_applied, audit_event_id."""
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.core.security import create_token
        from app.deps import get_db

        app = create_app()

        mock_result = {
            "doc_id": "doc-1",
            "corrections_applied": 1,
            "audit_event_id": "evt-uuid-123",
        }

        with patch("app.routers.documents.apply_field_correction", new=AsyncMock(return_value=mock_result)):
            async def mock_db():
                yield MagicMock()

            app.dependency_overrides[get_db] = mock_db
            token = create_token("user-1", "tenant-1")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.patch(
                    "/documents/doc-1/fields",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Tenant-ID": "tenant-1",
                    },
                    json={
                        "field_corrections": [
                            {"field_name": "title", "before_value": "Old", "after_value": "New"}
                        ],
                        "user_id": "user-1",
                    },
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["doc_id"] == "doc-1"
        assert body["corrections_applied"] == 1
        assert "audit_event_id" in body
