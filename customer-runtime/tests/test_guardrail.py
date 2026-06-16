"""T-012: Guardrail rule engine + POST /guardrail/run (REQ-API-007).

Unit tests only — no Docker required.
Integration test marked with @skip_no_docker.
"""
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


class TestGuardrailRuleEngine:
    """Test rule engine logic without DB."""

    async def test_document_with_no_linked_requirements_yields_medium_finding(self):
        """Rule: doc with no requirements -> Finding(severity=Medium)."""
        from app.services.guardrail import evaluate_document_rules

        findings = await evaluate_document_rules(
            doc_id="doc-1",
            requirements=[],  # No requirements linked
        )
        assert len(findings) == 1
        assert findings[0]["severity"] == "Medium"
        assert "no linked requirements" in findings[0]["message"].lower()

    async def test_document_with_requirements_but_no_risks_yields_high_finding(self):
        """Rule: requirements with no risk linkage -> Finding(severity=High)."""
        from app.services.guardrail import evaluate_document_rules

        reqs = [{"req_id": "req-1", "risks": []}]
        findings = await evaluate_document_rules(
            doc_id="doc-1",
            requirements=reqs,
        )
        assert len(findings) == 1
        assert findings[0]["severity"] == "High"
        assert "no risk linkage" in findings[0]["message"].lower()

    async def test_document_with_requirements_and_risks_yields_no_finding(self):
        """Rule: well-linked doc -> no findings."""
        from app.services.guardrail import evaluate_document_rules

        reqs = [{"req_id": "req-1", "risks": [{"risk_id": "risk-1"}]}]
        findings = await evaluate_document_rules(
            doc_id="doc-1",
            requirements=reqs,
        )
        assert findings == []


class TestGuardrailService:
    """Test GuardrailService.run_guardrail with mocked DB."""

    async def test_run_guardrail_returns_findings_and_run_id(self):
        """run_guardrail returns dict with findings, run_id, documents_flagged."""
        from app.services.guardrail import GuardrailService

        svc = GuardrailService()
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()

        # Patch _load_documents_with_requirements to return one doc with no reqs
        with patch.object(
            svc,
            "_load_documents_with_requirements",
            new=AsyncMock(return_value={"doc-1": []}),
        ):
            # Patch _update_document_status_to_finding_open to no-op
            with patch.object(svc, "_update_document_status_to_finding_open", new=AsyncMock()):
                result = await svc.run_guardrail(
                    db=mock_db,
                    tenant_id="tenant-1",
                    user_id="user-1",
                    product_id="prod-1",
                    doc_set_ids=["doc-1"],
                    rule_set_version="1.0",
                    audit_service=MagicMock(record=AsyncMock()),
                )

        assert "run_id" in result
        assert isinstance(result["findings"], list)
        assert isinstance(result["documents_flagged"], list)

    async def test_high_severity_finding_flags_document(self):
        """High severity finding -> document added to documents_flagged."""
        from app.services.guardrail import GuardrailService

        svc = GuardrailService()
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()

        # requirements with no risks -> High finding
        reqs_map = {"doc-1": [{"req_id": "req-1", "risks": []}]}

        flagged_docs: list[str] = []

        async def fake_update(db, doc_id, tenant_id):
            flagged_docs.append(doc_id)

        with patch.object(
            svc,
            "_load_documents_with_requirements",
            new=AsyncMock(return_value=reqs_map),
        ):
            with patch.object(
                svc, "_update_document_status_to_finding_open", new=fake_update
            ):
                result = await svc.run_guardrail(
                    db=mock_db,
                    tenant_id="tenant-1",
                    user_id="user-1",
                    product_id="prod-1",
                    doc_set_ids=["doc-1"],
                    rule_set_version="1.0",
                    audit_service=MagicMock(record=AsyncMock()),
                )

        assert "doc-1" in result["documents_flagged"]
        assert any(f["severity"] == "High" for f in result["findings"])

    async def test_audit_event_recorded_on_guardrail_run(self):
        """AuditEvent action='guardrail.run' is recorded."""
        from app.services.guardrail import GuardrailService

        svc = GuardrailService()
        mock_db = MagicMock()
        mock_db.flush = AsyncMock()
        mock_audit = MagicMock()
        mock_audit.record = AsyncMock()

        with patch.object(
            svc,
            "_load_documents_with_requirements",
            new=AsyncMock(return_value={}),
        ):
            with patch.object(svc, "_update_document_status_to_finding_open", new=AsyncMock()):
                await svc.run_guardrail(
                    db=mock_db,
                    tenant_id="tenant-1",
                    user_id="user-1",
                    product_id="prod-1",
                    doc_set_ids=[],
                    rule_set_version="1.0",
                    audit_service=mock_audit,
                )

        mock_audit.record.assert_called_once()
        call_kwargs = mock_audit.record.call_args
        assert call_kwargs.kwargs.get("action") == "guardrail.run" or (
            len(call_kwargs.args) > 3 and call_kwargs.args[3] == "guardrail.run"
        )


class TestGuardrailEndpoint:
    """Test POST /guardrail/run endpoint with mocked dependencies."""

    async def test_endpoint_requires_auth(self):
        """No auth header -> 401."""
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
            resp = await ac.post("/guardrail/run", json={
                "product_id": "prod-1",
                "doc_set_ids": ["doc-1"],
            })
        assert resp.status_code == 401

    async def test_endpoint_returns_200_with_valid_request(self):
        """Valid request -> 200 with findings, run_id, documents_flagged."""
        import os
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.deps import get_db
        from app.services.guardrail import GuardrailService

        _api_token = "test-token-32-bytes-minimum-here!"
        os.environ["HYBRID_RA_API_TOKEN"] = _api_token
        app = create_app()

        async def mock_db():
            yield MagicMock()

        mock_result = {
            "findings": [],
            "run_id": "run-uuid-123",
            "documents_flagged": [],
        }

        with patch.object(
            GuardrailService,
            "run_guardrail",
            new=AsyncMock(return_value=mock_result),
        ):
            app.dependency_overrides[get_db] = mock_db

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/guardrail/run",
                    headers={
                        "Authorization": f"Bearer {_api_token}",
                        "X-Tenant-ID": "tenant-1",
                    },
                    json={"product_id": "prod-1", "doc_set_ids": ["doc-1"]},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "findings" in body
        assert "run_id" in body
        assert "documents_flagged" in body


# ---------------------------------------------------------------------------
# Integration test (requires Docker)
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.integration
async def test_guardrail_endpoint_integration(client):
    """Full endpoint: guardrail run creates Finding rows, AuditEvent recorded."""
    from app.core.security import create_token

    token = create_token("user-1", "tenant-1")
    resp = await client.post(
        "/guardrail/run",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-1"},
        json={
            "product_id": "prod-integration-test",
            "doc_set_ids": [],
            "rule_set_version": "1.0",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "run_id" in body
    assert "findings" in body
