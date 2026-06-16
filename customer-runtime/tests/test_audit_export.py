"""T-014: Export service + POST /audit/export (REQ-API-010).

Unit tests only — no Docker required.
Integration test marked with @skip_no_docker.
"""
import io
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

from tests.conftest import skip_no_docker


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestExportService:
    """Test ExportService format generation."""

    async def test_json_export_returns_valid_json_bytes(self):
        """JSON format -> parseable bytes, AuditEvent recorded."""
        from app.services.export import ExportService

        svc = ExportService()
        mock_db = AsyncMock()
        mock_audit = MagicMock(record=AsyncMock())

        events = [
            {
                "event_id": "evt-1",
                "action": "document.upload",
                "tenant_id": "tenant-1",
                "user_id": "user-1",
                "timestamp": "2026-01-01T00:00:00",
            }
        ]

        with patch.object(svc, "_load_audit_events", new=AsyncMock(return_value=events)):
            result = await svc.export(
                db=mock_db,
                tenant_id="tenant-1",
                user_id="user-1",
                scope="full",
                product_id=None,
                date_from=None,
                date_to=None,
                format="JSON",
                audit_service=mock_audit,
            )

        assert result["media_type"] == "application/json"
        parsed = json.loads(result["content"])
        assert isinstance(parsed, (list, dict))
        mock_audit.record.assert_called_once()
        call_args = mock_audit.record.call_args
        assert call_args.kwargs.get("action") == "audit.export" or (
            len(call_args.args) > 3 and call_args.args[3] == "audit.export"
        )

    async def test_xlsx_export_returns_valid_xlsx_bytes(self):
        """XLSX format -> valid openpyxl-parseable bytes."""
        import openpyxl

        from app.services.export import ExportService

        svc = ExportService()
        mock_db = AsyncMock()
        mock_audit = MagicMock(record=AsyncMock())

        events = [
            {
                "event_id": "evt-1",
                "action": "document.upload",
                "tenant_id": "tenant-1",
                "user_id": "user-1",
                "timestamp": "2026-01-01T00:00:00",
            }
        ]

        with patch.object(svc, "_load_audit_events", new=AsyncMock(return_value=events)):
            result = await svc.export(
                db=mock_db,
                tenant_id="tenant-1",
                user_id="user-1",
                scope="full",
                product_id=None,
                date_from=None,
                date_to=None,
                format="XLSX",
                audit_service=mock_audit,
            )

        expected_ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert result["media_type"] == expected_ct
        # Verify bytes can be parsed by openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(result["content"]))
        assert len(wb.sheetnames) >= 1

    async def test_pdf_export_returns_bytes(self):
        """PDF format -> bytes returned (or fallback JSON)."""
        from app.services.export import ExportService

        svc = ExportService()
        mock_db = AsyncMock()
        mock_audit = MagicMock(record=AsyncMock())

        events: list = []

        with patch.object(svc, "_load_audit_events", new=AsyncMock(return_value=events)):
            result = await svc.export(
                db=mock_db,
                tenant_id="tenant-1",
                user_id="user-1",
                scope="full",
                product_id=None,
                date_from=None,
                date_to=None,
                format="PDF",
                audit_service=mock_audit,
            )

        # Either PDF or JSON fallback
        assert result["media_type"] in ("application/pdf", "application/json")
        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0

    async def test_audit_event_recorded_for_each_export(self):
        """AuditEvent with action='audit.export' recorded for every format."""
        from app.services.export import ExportService

        svc = ExportService()
        mock_db = AsyncMock()

        for fmt in ("JSON", "XLSX", "PDF"):
            mock_audit = MagicMock(record=AsyncMock())
            with patch.object(svc, "_load_audit_events", new=AsyncMock(return_value=[])):
                await svc.export(
                    db=mock_db,
                    tenant_id="tenant-1",
                    user_id="user-1",
                    scope="full",
                    product_id=None,
                    date_from=None,
                    date_to=None,
                    format=fmt,
                    audit_service=mock_audit,
                )
            mock_audit.record.assert_called_once()


class TestAuditExportEndpoint:
    """Test POST /audit/export endpoint."""

    async def test_endpoint_requires_auth(self):
        """No auth header -> 401 (HYBRID_RA_API_TOKEN must be configured)."""
        import os
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.deps import get_db

        os.environ["HYBRID_RA_API_TOKEN"] = "test-token-32-bytes-minimum-here!"
        app = create_app()

        async def mock_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/audit/export",
                json={"scope": "full", "format": "JSON"},
            )
        assert resp.status_code == 401

    async def test_endpoint_returns_200_json_export(self):
        """Valid JSON export request -> 200 StreamingResponse."""
        import os
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.deps import get_db
        from app.services.export import ExportService

        _api_token = "test-token-32-bytes-minimum-here!"
        os.environ["HYBRID_RA_API_TOKEN"] = _api_token
        app = create_app()

        mock_result = {
            "content": b'[{"event_id": "evt-1"}]',
            "media_type": "application/json",
            "filename": "audit_export_20260101.json",
        }

        with patch.object(ExportService, "export", new=AsyncMock(return_value=mock_result)):
            async def mock_db():
                yield MagicMock()

            app.dependency_overrides[get_db] = mock_db

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/audit/export",
                    headers={
                        "Authorization": f"Bearer {_api_token}",
                        "X-Tenant-ID": "tenant-1",
                    },
                    json={"scope": "full", "format": "JSON"},
                )
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Integration test (requires Docker)
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.integration
async def test_audit_export_integration(client):
    """Full endpoint: returns binary for JSON format."""
    from app.core.security import create_token

    token = create_token("user-1", "tenant-1")
    resp = await client.post(
        "/audit/export",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-1"},
        json={"scope": "full", "format": "JSON"},
    )
    assert resp.status_code == 200
