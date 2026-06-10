"""Unit tests for SHA-256 dedup service (T-013, REQ-003/003b, AC-002).

Uses SQLite in-memory — no Docker required.
"""

import hashlib

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session():
    """In-memory SQLite session with regulatory_documents schema."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    from app.models.base import Base
    import app.models.regulatory_document  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.asyncio
async def test_is_duplicate_returns_false_for_new_hash(db_session):
    """is_duplicate returns False when hash is not in DB."""
    from app.services.dedup import DedupService

    svc = DedupService(db_session)
    result = await svc.is_duplicate(sha256_hex(b"some new content"))

    assert result is False


@pytest.mark.asyncio
async def test_is_duplicate_returns_true_after_insert(db_session):
    """is_duplicate returns True after the same hash is stored."""
    from app.services.dedup import DedupService
    from app.models.regulatory_document import RegulatoryDocument
    from datetime import datetime, timezone

    content = b"duplicate content"
    h = sha256_hex(content)

    doc = RegulatoryDocument(
        source="fda",
        blob_path="regulatory-docs/fda/2026-06-10/dup.pdf",
        content_hash=h,
        fetched_at=datetime.now(timezone.utc),
        source_url="https://fda.gov/dup.pdf",
    )
    db_session.add(doc)
    await db_session.commit()

    svc = DedupService(db_session)
    result = await svc.is_duplicate(h)

    assert result is True


@pytest.mark.asyncio
async def test_compute_hash_returns_sha256_hex(db_session):
    """compute_hash produces correct SHA-256 hex digest."""
    from app.services.dedup import DedupService

    svc = DedupService(db_session)
    data = b"hello world"
    expected = hashlib.sha256(data).hexdigest()

    assert svc.compute_hash(data) == expected


@pytest.mark.asyncio
async def test_different_contents_are_not_duplicates(db_session):
    """Two documents with different bytes are never duplicates."""
    from app.services.dedup import DedupService

    svc = DedupService(db_session)

    h1 = sha256_hex(b"content A")
    h2 = sha256_hex(b"content B")

    assert not await svc.is_duplicate(h1)
    assert not await svc.is_duplicate(h2)
