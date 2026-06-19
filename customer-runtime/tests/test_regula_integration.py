"""Regression tests for Regula server-to-server integration boundaries."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest
from fastapi import HTTPException

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


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://regula.example/webhook")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("webhook failed", request=request, response=response)


class _FakeAsyncClient:
    calls: list[dict[str, Any]] = []
    status_code = 200

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, json: dict[str, Any], headers: dict[str, str]) -> _FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
        return _FakeResponse(status_code=self.status_code)


@pytest.mark.asyncio
async def test_verify_api_key_returns_503_when_not_configured(monkeypatch):
    """Server-to-server auth must fail closed if REGULA_API_KEY is absent."""
    from app.core.security import verify_api_key

    monkeypatch.setenv("REGULA_API_KEY", "")

    with pytest.raises(HTTPException) as exc:
        await anext(verify_api_key(api_key="anything"))

    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_verify_api_key_rejects_missing_or_wrong_key(monkeypatch):
    """Missing or invalid X-Regula-API-Key must return 401."""
    from app.core.security import verify_api_key

    monkeypatch.setenv("REGULA_API_KEY", "expected")

    for supplied in (None, "wrong"):
        with pytest.raises(HTTPException) as exc:
            await anext(verify_api_key(api_key=supplied))
        assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_api_key_accepts_expected_key(monkeypatch):
    """Correct API key succeeds when no tenant allowlist is configured."""
    from app.core.security import verify_api_key

    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setenv("REGULA_ALLOWED_TENANTS", "")

    assert await anext(verify_api_key(api_key="expected")) == "expected"


@pytest.mark.asyncio
async def test_verify_api_key_enforces_tenant_allowlist(monkeypatch):
    """REGULA_ALLOWED_TENANTS limits server-to-server access by X-Tenant-ID."""
    from app.core.security import verify_api_key

    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setenv("REGULA_ALLOWED_TENANTS", "tenant-a,tenant-b")

    with pytest.raises(HTTPException) as exc:
        await anext(verify_api_key(api_key="expected", x_tenant_id="tenant-c"))

    assert exc.value.status_code == 403
    assert await anext(verify_api_key(api_key="expected", x_tenant_id="tenant-a")) == "expected"


@pytest.mark.asyncio
async def test_audit_webhook_returns_skipped_when_url_is_unset(monkeypatch):
    """Audit webhook is a safe no-op until REGULA_AUDIT_WEBHOOK_URL is configured."""
    from app.routers.audit import audit_webhook
    from app.schemas.audit import AuditWebhookRequest

    monkeypatch.setenv("REGULA_AUDIT_WEBHOOK_URL", "")

    response = await audit_webhook(
        AuditWebhookRequest(event_type="audit.flagged", product_id="prod-1", data={"severity": "high"}),
        tenant="tenant-a",
    )

    assert response.status == "skipped"


@pytest.mark.asyncio
async def test_audit_webhook_forwards_payload_and_api_key(monkeypatch):
    """Configured audit webhook forwards tenant, event payload, and API key header."""
    from app.routers.audit import audit_webhook
    from app.schemas.audit import AuditWebhookRequest

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 200
    monkeypatch.setenv("REGULA_AUDIT_WEBHOOK_URL", "https://regula.example/audit")
    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setattr("app.routers.audit.httpx.AsyncClient", _FakeAsyncClient)

    response = await audit_webhook(
        AuditWebhookRequest(event_type="audit.flagged", product_id="prod-1", data={"severity": "high"}),
        tenant="tenant-a",
    )

    assert response.status == "sent"
    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://regula.example/audit"
    assert call["headers"]["X-Regula-API-Key"] == "expected"
    assert call["json"]["tenant_id"] == "tenant-a"
    assert call["json"]["event_type"] == "audit.flagged"


@pytest.mark.asyncio
async def test_audit_webhook_returns_502_on_upstream_http_error(monkeypatch):
    """Non-2xx Regula audit response is reported as a gateway failure."""
    from app.routers.audit import audit_webhook
    from app.schemas.audit import AuditWebhookRequest

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 500
    monkeypatch.setenv("REGULA_AUDIT_WEBHOOK_URL", "https://regula.example/audit")
    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setattr("app.routers.audit.httpx.AsyncClient", _FakeAsyncClient)

    with pytest.raises(HTTPException) as exc:
        await audit_webhook(
            AuditWebhookRequest(event_type="audit.flagged", product_id="prod-1", data={}),
            tenant="tenant-a",
        )

    assert exc.value.status_code == 502


@pytest.mark.asyncio
async def test_ifu_push_is_noop_when_url_is_unset(monkeypatch):
    """IFU parse push is fire-and-forget and skipped until URL is configured."""
    from app.jobs.parse_job import _push_ifu_result_to_regula
    from app.services.parser import ParseResult

    _FakeAsyncClient.calls = []
    monkeypatch.setenv("REGULA_IFU_WEBHOOK_URL", "")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_ifu_result_to_regula(
        job_id="job-1",
        doc_id="doc-1",
        tenant="tenant-a",
        doc_type="ifu",
        result=ParseResult(confidence=0.91, field_candidates={"device_name": "Pump"}, required_missing=[]),
    )

    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_ifu_push_forwards_parse_result_and_api_key(monkeypatch):
    """Configured IFU webhook receives parse result fields and API key header."""
    from app.jobs.parse_job import _push_ifu_result_to_regula
    from app.services.parser import ParseResult

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 200
    monkeypatch.setenv("REGULA_IFU_WEBHOOK_URL", "https://regula.example/ifu")
    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_ifu_result_to_regula(
        job_id="job-1",
        doc_id="doc-1",
        tenant="tenant-a",
        doc_type="ifu",
        result=ParseResult(
            confidence=0.91,
            field_candidates={"device_name": "Pump"},
            required_missing=["warnings"],
        ),
    )

    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://regula.example/ifu"
    assert call["headers"]["X-Regula-API-Key"] == "expected"
    assert call["json"]["tenant_id"] == "tenant-a"
    assert call["json"]["confidence"] == 0.91
    assert call["json"]["field_candidates"] == {"device_name": "Pump"}
    assert call["json"]["required_missing"] == ["warnings"]


@pytest.mark.asyncio
async def test_ifu_push_http_failure_is_non_fatal(monkeypatch):
    """IFU webhook failures are logged but do not fail the parse job."""
    from app.jobs.parse_job import _push_ifu_result_to_regula
    from app.services.parser import ParseResult

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 503
    monkeypatch.setenv("REGULA_IFU_WEBHOOK_URL", "https://regula.example/ifu")
    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_ifu_result_to_regula(
        job_id="job-1",
        doc_id="doc-1",
        tenant="tenant-a",
        doc_type="ifu",
        result=ParseResult(confidence=0.91, field_candidates={}, required_missing=[]),
    )

    assert len(_FakeAsyncClient.calls) == 1


@pytest.mark.asyncio
async def test_knowledge_sync_push_skipped_when_not_configured(monkeypatch):
    """Knowledge sync push is fire-and-forget and skipped until URL is configured."""
    from app.jobs.parse_job import _push_knowledge_sync_to_regula

    _FakeAsyncClient.calls = []
    monkeypatch.setenv("REGULA_KNOWLEDGE_PUSH_URL", "")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_knowledge_sync_to_regula(job_id="job-1", tenant="tenant-a")

    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_knowledge_sync_push_sends_trigger_and_api_key(monkeypatch):
    """Configured knowledge sync URL receives trigger payload and API key header."""
    from app.jobs.parse_job import _push_knowledge_sync_to_regula

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 200
    monkeypatch.setenv("REGULA_KNOWLEDGE_PUSH_URL", "https://regula.example/knowledge-sync")
    monkeypatch.setenv("REGULA_API_KEY", "expected")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_knowledge_sync_to_regula(job_id="job-1", tenant="tenant-a")

    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://regula.example/knowledge-sync"
    assert call["headers"]["X-Regula-API-Key"] == "expected"
    assert call["json"]["tenant_id"] == "tenant-a"
    assert call["json"]["trigger"] == "parse_completed"
    assert call["json"]["job_id"] == "job-1"


@pytest.mark.asyncio
async def test_knowledge_sync_push_http_failure_is_non_fatal(monkeypatch):
    """Knowledge sync push failures are logged but do not fail the parse job."""
    from app.jobs.parse_job import _push_knowledge_sync_to_regula

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 500
    monkeypatch.setenv("REGULA_KNOWLEDGE_PUSH_URL", "https://regula.example/knowledge-sync")
    monkeypatch.setattr("app.jobs.parse_job.httpx.AsyncClient", _FakeAsyncClient)

    await _push_knowledge_sync_to_regula(job_id="job-1", tenant="tenant-a")

    assert len(_FakeAsyncClient.calls) == 1
