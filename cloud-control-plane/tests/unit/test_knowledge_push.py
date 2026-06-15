"""Unit tests for Regula knowledge push integration boundary."""

from __future__ import annotations

from typing import Any

import httpx
import pytest


class _FakeResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://regula.example/sync")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("push failed", request=request, response=response)


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
async def test_knowledge_push_skips_when_url_is_not_configured(monkeypatch):
    """Missing REGULA_KNOWLEDGE_PUSH_URL must be a no-op."""
    from app.services.knowledge_push import KnowledgePushService

    _FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.knowledge_push.httpx.AsyncClient", _FakeAsyncClient)

    service = KnowledgePushService(push_url="", push_secret="secret")

    await service.push(job_id="job-1", documents=[{"id": "doc-1"}])

    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_knowledge_push_skips_when_secret_is_not_configured(monkeypatch):
    """Configured URL without CRAWL_PUSH_SECRET must not send an unauthenticated push."""
    from app.services.knowledge_push import KnowledgePushService

    _FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.knowledge_push.httpx.AsyncClient", _FakeAsyncClient)

    service = KnowledgePushService(push_url="https://regula.example/sync", push_secret="")

    await service.push(job_id="job-1", documents=[{"id": "doc-1"}])

    assert _FakeAsyncClient.calls == []


@pytest.mark.asyncio
async def test_knowledge_push_posts_documents_with_secret_header(monkeypatch):
    """Configured push sends a batch with X-Crawl-Push-Secret."""
    from app.services.knowledge_push import KnowledgePushService

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 200
    monkeypatch.setattr("app.services.knowledge_push.httpx.AsyncClient", _FakeAsyncClient)

    service = KnowledgePushService(
        push_url="https://regula.example/api/admin/radar/sync",
        push_secret="crawl-secret",
    )

    await service.push(
        job_id="job-1",
        documents=[
            {
                "id": "blob/fda/doc.pdf",
                "url": "https://fda.gov/doc.pdf",
                "hash": "abc",
                "source": "fda",
                "content": "public guidance text",
            }
        ],
    )

    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"] == "https://regula.example/api/admin/radar/sync"
    assert call["headers"]["X-Crawl-Push-Secret"] == "crawl-secret"
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["json"]["job_id"] == "job-1"
    assert call["json"]["documents"][0]["source"] == "fda"


@pytest.mark.asyncio
async def test_knowledge_push_truncates_large_content(monkeypatch):
    """Large crawled documents are truncated before crossing the repo boundary."""
    from app.services.knowledge_push import KnowledgePushService

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 200
    monkeypatch.setattr("app.services.knowledge_push.httpx.AsyncClient", _FakeAsyncClient)

    service = KnowledgePushService(push_url="https://regula.example/sync", push_secret="secret")

    await service.push(
        job_id="job-1",
        documents=[{"id": "doc-1", "content": "x" * 60_000}],
    )

    content = _FakeAsyncClient.calls[0]["json"]["documents"][0]["content"]
    assert len(content) == 50_000


@pytest.mark.asyncio
async def test_knowledge_push_http_failure_is_non_blocking(monkeypatch):
    """Remote sync failure must not abort the crawl job."""
    from app.services.knowledge_push import KnowledgePushService

    _FakeAsyncClient.calls = []
    _FakeAsyncClient.status_code = 503
    monkeypatch.setattr("app.services.knowledge_push.httpx.AsyncClient", _FakeAsyncClient)

    service = KnowledgePushService(push_url="https://regula.example/sync", push_secret="secret")

    await service.push(job_id="job-1", documents=[{"id": "doc-1", "content": "text"}])

    assert len(_FakeAsyncClient.calls) == 1
