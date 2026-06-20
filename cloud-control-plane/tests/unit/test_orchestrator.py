"""Unit tests for crawl orchestrator (T-016, REQ-001/004/006/010).

Uses in-memory SQLite and mock sources/storage — no Docker.
Tests cover:
- Per-document failure isolation (bad doc doesn't abort job)
- Per-source failure isolation (bad source doesn't abort job)
- Dedup skip path (hash match skips blob upload + DB insert)
- Structured log events emitted
- job_id returned and job status trackable
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# ---------------------------------------------------------------------------
# SQLite in-memory fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def sqlite_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    from app.models.base import Base
    import app.models.regulatory_document  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(sqlite_engine):
    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    async with factory() as s:
        yield s


# ---------------------------------------------------------------------------
# Fake source builder
# ---------------------------------------------------------------------------


def _make_fake_source(
    name: str,
    docs: list[tuple[str, bytes]],  # (url, content)
    fail_urls: set[str] | None = None,
) -> MagicMock:
    """Build a mock CrawlerSource that yields given (url, bytes) pairs."""
    source = MagicMock()
    source.SOURCE_NAME = name
    source.load_robots = AsyncMock()

    fail_urls = fail_urls or set()

    async def mock_discover():
        return [url for url, _ in docs]

    async def mock_fetch(url: str) -> bytes:
        if url in fail_urls:
            raise ConnectionError(f"Simulated failure for {url}")
        for u, content in docs:
            if u == url:
                return content
        raise ValueError(f"Unknown URL: {url}")

    source.discover_document_urls = mock_discover
    source.fetch_document = mock_fetch
    return source


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_stores_new_document(db_session):
    """Orchestrator inserts a metadata row for a new document."""
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    import sqlalchemy as sa

    content = b"PDF content"
    source = _make_fake_source("fda", [("https://fda.gov/doc.pdf", content)])

    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock(return_value="regulatory-docs/fda/2026-06-10/doc.pdf")

    orch = CrawlOrchestrator(
        sources=[source],
        storage=mock_storage,
        session=db_session,
    )

    job_id = await orch.run()

    # Verify DB row was inserted
    result = await db_session.execute(
        sa.select(RegulatoryDocument).where(RegulatoryDocument.source == "fda")
    )
    rows = result.scalars().all()

    assert len(rows) == 1
    assert rows[0].content_hash == hashlib.sha256(content).hexdigest()
    assert rows[0].source_url == "https://fda.gov/doc.pdf"
    assert job_id is not None


@pytest.mark.asyncio
async def test_dedup_skips_duplicate(db_session):
    """REQ-CRAWLER-002-006: duplicate document (same SHA-256) is skipped — NOT stored twice.

    Verifies idempotency: a document with content_hash already in DB must not trigger
    blob upload, DB insert, or appearance in the push payload.
    """
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    import sqlalchemy as sa

    content = b"idempotency test content"
    h = hashlib.sha256(content).hexdigest()

    # Pre-insert so the dedup check will fire
    db_session.add(
        RegulatoryDocument(
            source="fda",
            blob_path="regulatory-docs/fda/2026-06-01/dup.pdf",
            content_hash=h,
            fetched_at=datetime.now(timezone.utc),
            source_url="https://fda.gov/dup.pdf",
        )
    )
    await db_session.commit()

    source = _make_fake_source("fda", [("https://fda.gov/dup.pdf", content)])
    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock()

    orch = CrawlOrchestrator(sources=[source], storage=mock_storage, session=db_session)
    await orch.run()

    # Blob upload MUST NOT be called for duplicate
    mock_storage.upload_document.assert_not_called()

    # DB row count must remain 1 — not stored twice
    result = await db_session.execute(
        sa.select(RegulatoryDocument).where(RegulatoryDocument.content_hash == h)
    )
    assert len(result.scalars().all()) == 1, "Duplicate document must not be stored twice"


@pytest.mark.asyncio
async def test_orchestrator_skips_duplicate(db_session):
    """Duplicate document (same SHA-256) skips blob upload and DB insert."""
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    import sqlalchemy as sa

    content = b"existing content"
    h = hashlib.sha256(content).hexdigest()

    # Pre-insert the document
    existing = RegulatoryDocument(
        source="fda",
        blob_path="regulatory-docs/fda/2026-06-10/existing.pdf",
        content_hash=h,
        fetched_at=datetime.now(timezone.utc),
        source_url="https://fda.gov/existing.pdf",
    )
    db_session.add(existing)
    await db_session.commit()

    source = _make_fake_source("fda", [("https://fda.gov/existing.pdf", content)])

    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock()

    orch = CrawlOrchestrator(
        sources=[source],
        storage=mock_storage,
        session=db_session,
    )

    await orch.run()

    # Blob upload must NOT have been called
    mock_storage.upload_document.assert_not_called()

    # Still only one row
    result = await db_session.execute(
        sa.select(RegulatoryDocument).where(RegulatoryDocument.content_hash == h)
    )
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_orchestrator_continues_after_document_failure(db_session):
    """One bad document does not abort the job — other docs still processed."""
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    import sqlalchemy as sa

    docs = [
        ("https://fda.gov/bad.pdf", b"bad"),
        ("https://fda.gov/good.pdf", b"good content"),
    ]
    source = _make_fake_source("fda", docs, fail_urls={"https://fda.gov/bad.pdf"})

    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock(return_value="regulatory-docs/fda/2026-06-10/good.pdf")

    orch = CrawlOrchestrator(
        sources=[source],
        storage=mock_storage,
        session=db_session,
    )

    # Must NOT raise
    await orch.run()

    # Good document should be stored
    result = await db_session.execute(sa.select(RegulatoryDocument))
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].source_url == "https://fda.gov/good.pdf"


@pytest.mark.asyncio
async def test_orchestrator_continues_after_source_failure(db_session):
    """One source failing entirely does not abort the job — other sources run."""
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    import sqlalchemy as sa

    # Source A: will raise on discover
    bad_source = MagicMock()
    bad_source.SOURCE_NAME = "bad-source"
    bad_source.load_robots = AsyncMock()
    bad_source.discover_document_urls = AsyncMock(side_effect=RuntimeError("Source unavailable"))

    # Source B: normal
    good_source = _make_fake_source("fda", [("https://fda.gov/ok.pdf", b"ok content")])

    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock(return_value="regulatory-docs/fda/2026-06-10/ok.pdf")

    orch = CrawlOrchestrator(
        sources=[bad_source, good_source],
        storage=mock_storage,
        session=db_session,
    )

    await orch.run()

    result = await db_session.execute(sa.select(RegulatoryDocument))
    rows = result.scalars().all()
    assert len(rows) == 1, "FDA document should be stored despite bad source failing"


@pytest.mark.asyncio
async def test_orchestrator_emits_job_started_log(db_session):
    """Orchestrator emits a structured 'job_started' log event with job_id.

    The app logger uses propagate=False and a custom JsonFormatter writing to
    stdout, so caplog cannot capture records via the standard propagation path.
    Instead, a MemoryHandler is attached directly to the orchestrator logger to
    capture records before they reach the JsonFormatter.
    """
    import logging
    from app.services.orchestrator import CrawlOrchestrator

    # Attach a MemoryHandler directly to the orchestrator module logger so that
    # propagate=False does not prevent capture.
    orchestrator_logger = logging.getLogger("app.services.orchestrator")
    captured: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _ListHandler(level=logging.INFO)
    orchestrator_logger.addHandler(handler)
    try:
        source = _make_fake_source("fda", [])
        mock_storage = AsyncMock()

        orch = CrawlOrchestrator(
            sources=[source],
            storage=mock_storage,
            session=db_session,
        )

        job_id = await orch.run()
    finally:
        orchestrator_logger.removeHandler(handler)

    # Verify: at least one record has message 'job_started' and carries the job_id field
    job_started_records = [
        r
        for r in captured
        if r.getMessage() == "job_started" and getattr(r, "job_id", None) == job_id
    ]
    assert len(job_started_records) >= 1, (
        f"Expected a 'job_started' log record with job_id={job_id!r}. "
        f"Got records: {[(r.getMessage(), getattr(r, 'job_id', None)) for r in captured]}"
    )


@pytest.mark.asyncio
async def test_job_registry_tracks_status(db_session):
    """job_id registry allows checking status after run."""
    from app.services.orchestrator import CrawlOrchestrator, job_registry

    source = _make_fake_source("fda", [])
    mock_storage = AsyncMock()

    orch = CrawlOrchestrator(
        sources=[source],
        storage=mock_storage,
        session=db_session,
    )

    job_id = await orch.run()

    assert job_id in job_registry
    assert job_registry[job_id]["status"] in ("completed", "failed")


@pytest.mark.asyncio
async def test_orchestrator_pushes_only_newly_stored_documents(db_session, monkeypatch):
    """Knowledge push receives newly stored documents, not duplicate skips."""
    from app.models.regulatory_document import RegulatoryDocument
    from app.services.orchestrator import CrawlOrchestrator
    import sqlalchemy as sa

    existing_content = b"existing content"
    existing_hash = hashlib.sha256(existing_content).hexdigest()
    db_session.add(
        RegulatoryDocument(
            source="fda",
            blob_path="regulatory-docs/fda/2026-06-10/existing.pdf",
            content_hash=existing_hash,
            fetched_at=datetime.now(timezone.utc),
            source_url="https://fda.gov/existing.pdf",
        )
    )
    await db_session.commit()

    push_calls: list[dict] = []

    class FakeKnowledgePushService:
        def __init__(self, push_url: str, push_secret: str) -> None:
            self.push_url = push_url
            self.push_secret = push_secret

        async def push(self, job_id: str, documents: list[dict]) -> None:
            push_calls.append(
                {
                    "job_id": job_id,
                    "push_url": self.push_url,
                    "push_secret": self.push_secret,
                    "documents": documents,
                }
            )

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "acct")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "container")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=fake")
    monkeypatch.setenv("REGULA_KNOWLEDGE_PUSH_URL", "https://regula.example/sync")
    monkeypatch.setenv("CRAWL_PUSH_SECRET", "secret")
    monkeypatch.setattr("app.services.orchestrator.KnowledgePushService", FakeKnowledgePushService)

    source = _make_fake_source(
        "fda",
        [
            ("https://fda.gov/existing.pdf", existing_content),
            ("https://fda.gov/new.pdf", b"new public guidance"),
        ],
    )
    mock_storage = AsyncMock()
    mock_storage.upload_document = AsyncMock(return_value="regulatory-docs/fda/2026-06-10/new.pdf")

    orch = CrawlOrchestrator(sources=[source], storage=mock_storage, session=db_session)

    job_id = await orch.run(job_id="job-123")

    result = await db_session.execute(sa.select(RegulatoryDocument))
    rows = result.scalars().all()
    assert len(rows) == 2
    assert job_id == "job-123"
    assert len(push_calls) == 1
    assert push_calls[0]["push_url"] == "https://regula.example/sync"
    assert push_calls[0]["push_secret"] == "secret"
    assert [doc["url"] for doc in push_calls[0]["documents"]] == ["https://fda.gov/new.pdf"]
