"""Integration tests for CrawlOrchestrator (T-021, AC-001, AC-002).

CI-only: requires Docker daemon for testcontainers PostgreSQL.
Automatically skipped when Docker is unavailable (skip_no_docker marker from conftest).

Tests:
- AC-001: New document stored to blob with correct path + metadata row inserted,
           raw bytes NOT in the DB row.
- AC-002: Duplicate SHA-256 run inserts nothing new (row count stays at 1).
"""

from __future__ import annotations

import hashlib
import sys
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# Import skip marker from conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_no_docker  # noqa: E402


# ---------------------------------------------------------------------------
# Fake source builder (mirrors unit test helper)
# ---------------------------------------------------------------------------


def _make_fake_source(name: str, docs: list[tuple[str, bytes]]) -> MagicMock:
    source = MagicMock()
    source.SOURCE_NAME = name
    source.load_robots = AsyncMock()

    async def mock_discover() -> list[str]:
        return [url for url, _ in docs]

    async def mock_fetch(url: str) -> bytes:
        for u, content in docs:
            if u == url:
                return content
        raise ValueError(f"Unknown URL: {url}")

    source.discover_document_urls = mock_discover
    source.fetch_document = mock_fetch
    return source


def _make_fake_blob_client() -> MagicMock:
    """Fake blob client that records uploaded paths."""
    uploaded: dict[str, bytes] = {}

    client = MagicMock()

    async def fake_upload(source: str, filename: str, content: bytes, fetch_date: object) -> str:
        date_str = str(fetch_date)
        path = f"regulatory-docs/{source}/{date_str}/{filename}"
        uploaded[path] = content
        return path

    client.upload_document = fake_upload
    client._uploaded = uploaded
    return client


# ---------------------------------------------------------------------------
# AC-001: New document → blob + metadata row, no raw bytes in DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_docker
async def test_ac001_new_document_stored():
    """AC-001: orchestrator stores blob path + metadata row; raw bytes not in DB."""
    from testcontainers.postgres import PostgresContainer
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import sqlalchemy as sa
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    from app.models.base import Base
    import app.models.regulatory_document  # noqa: F401

    with PostgresContainer("postgres:16-alpine") as pg:
        sync_url = pg.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)

            content = b"%PDF-1.4 integration test document"
            source = _make_fake_source("fda", [("https://fda.gov/integration-doc.pdf", content)])
            fake_blob = _make_fake_blob_client()

            async with session_factory() as session:
                orch = CrawlOrchestrator(
                    sources=[source],
                    storage=fake_blob,
                    session=session,
                )
                await orch.run()

                # Verify DB row
                result = await session.execute(
                    sa.select(RegulatoryDocument).where(RegulatoryDocument.source == "fda")
                )
                rows = result.scalars().all()

            assert len(rows) == 1
            row = rows[0]

            # Blob path follows the convention (REQ-002)
            assert row.blob_path.startswith("regulatory-docs/fda/")
            assert row.blob_path.endswith("integration-doc.pdf")

            # Metadata fields populated
            expected_hash = hashlib.sha256(content).hexdigest()
            assert row.content_hash == expected_hash
            assert row.source_url == "https://fda.gov/integration-doc.pdf"
            assert row.fetched_at is not None

            # [HARD] Raw bytes must NOT be in PostgreSQL (FR-210, REQ-004)
            col_names = {c.key for c in RegulatoryDocument.__table__.columns}
            assert "content" not in col_names
            assert "raw_bytes" not in col_names
            assert "body" not in col_names

        finally:
            await engine.dispose()


# ---------------------------------------------------------------------------
# AC-002: Duplicate run → no new rows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_docker
async def test_ac002_duplicate_document_skipped():
    """AC-002: second run with same SHA-256 inserts nothing new (row count stays 1)."""
    from testcontainers.postgres import PostgresContainer
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    import sqlalchemy as sa
    from app.services.orchestrator import CrawlOrchestrator
    from app.models.regulatory_document import RegulatoryDocument
    from app.models.base import Base
    import app.models.regulatory_document  # noqa: F401

    with PostgresContainer("postgres:16-alpine") as pg:
        sync_url = pg.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

        engine = create_async_engine(async_url, echo=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            content = b"%PDF-1.4 duplicate check document"

            # First run — should insert
            source_a = _make_fake_source("fda", [("https://fda.gov/dup-doc.pdf", content)])
            fake_blob_a = _make_fake_blob_client()

            async with session_factory() as session_a:
                orch_a = CrawlOrchestrator(
                    sources=[source_a],
                    storage=fake_blob_a,
                    session=session_a,
                )
                await orch_a.run()

            # Verify first run inserted one row
            async with session_factory() as check_session:
                result = await check_session.execute(
                    sa.select(RegulatoryDocument).where(
                        RegulatoryDocument.content_hash == hashlib.sha256(content).hexdigest()
                    )
                )
                assert len(result.scalars().all()) == 1

            # Second run with same content — should skip
            source_b = _make_fake_source("fda", [("https://fda.gov/dup-doc.pdf", content)])
            fake_blob_b = _make_fake_blob_client()

            async with session_factory() as session_b:
                orch_b = CrawlOrchestrator(
                    sources=[source_b],
                    storage=fake_blob_b,
                    session=session_b,
                )
                await orch_b.run()

            # Row count must still be 1
            async with session_factory() as check_session2:
                result2 = await check_session2.execute(
                    sa.select(RegulatoryDocument).where(
                        RegulatoryDocument.content_hash == hashlib.sha256(content).hexdigest()
                    )
                )
                rows = result2.scalars().all()

            assert len(rows) == 1, "Duplicate document must not create a second row"

            # Blob upload was NOT called on second run
            assert len(fake_blob_b._uploaded) == 0

        finally:
            await engine.dispose()
