"""Unit tests for ORM model constraints — RED phase.

Uses SQLite+aiosqlite in-memory DB. No Docker or PostgreSQL required.
"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


@pytest_asyncio.fixture(scope="function")
async def sqlite_engine():
    """In-memory SQLite async engine with schema created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Import models so metadata is populated
    from app.models.base import Base
    import app.models.regulatory_document  # noqa: F401 — registers model

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session(sqlite_engine):
    """Async session for a single test."""
    factory = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    async with factory() as s:
        yield s


@pytest.mark.asyncio
async def test_regulatory_document_insert(session):
    """Can insert a RegulatoryDocument row with all required fields."""
    from app.models.regulatory_document import RegulatoryDocument
    from datetime import datetime, timezone

    doc = RegulatoryDocument(
        source="fda",
        blob_path="regulatory-docs/fda/2026-06-10/doc.pdf",
        content_hash="a" * 64,
        fetched_at=datetime.now(timezone.utc),
        source_url="https://fda.gov/doc.pdf",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    assert doc.id is not None
    assert doc.source == "fda"


@pytest.mark.asyncio
async def test_content_hash_unique_constraint(session):
    """Duplicate content_hash raises IntegrityError (UNIQUE constraint)."""
    from app.models.regulatory_document import RegulatoryDocument
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError

    hash_val = "b" * 64

    doc1 = RegulatoryDocument(
        source="fda",
        blob_path="regulatory-docs/fda/2026-06-10/doc1.pdf",
        content_hash=hash_val,
        fetched_at=datetime.now(timezone.utc),
        source_url="https://fda.gov/doc1.pdf",
    )
    doc2 = RegulatoryDocument(
        source="fda",
        blob_path="regulatory-docs/fda/2026-06-10/doc2.pdf",
        content_hash=hash_val,  # same hash — should fail
        fetched_at=datetime.now(timezone.utc),
        source_url="https://fda.gov/doc2.pdf",
    )
    session.add(doc1)
    await session.commit()

    session.add(doc2)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_no_raw_content_column(session):
    """RegulatoryDocument has no column for raw document content (FR-210)."""
    from app.models.regulatory_document import RegulatoryDocument

    columns = [col.key for col in RegulatoryDocument.__table__.columns]
    # None of these column names should exist
    forbidden = {"content", "raw_content", "body", "text", "raw_bytes", "data"}
    assert forbidden.isdisjoint(set(columns)), (
        f"Found forbidden raw content column(s): {forbidden & set(columns)}"
    )


@pytest.mark.asyncio
async def test_timestamp_mixin_sets_created_at(session):
    """TimestampMixin auto-populates created_at on insert."""
    from app.models.regulatory_document import RegulatoryDocument
    from datetime import datetime, timezone

    doc = RegulatoryDocument(
        source="mfds",
        blob_path="regulatory-docs/mfds/2026-06-10/doc.pdf",
        content_hash="c" * 64,
        fetched_at=datetime.now(timezone.utc),
        source_url="https://mfds.go.kr/doc.pdf",
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    assert doc.created_at is not None


@pytest.mark.asyncio
async def test_source_values_accepted(session):
    """All three valid source values can be stored."""
    from app.models.regulatory_document import RegulatoryDocument
    from datetime import datetime, timezone

    for i, src in enumerate(["fda", "mfds", "eu-mdr"]):
        doc = RegulatoryDocument(
            source=src,
            blob_path=f"regulatory-docs/{src}/2026-06-10/doc{i}.pdf",
            content_hash=f"d{i}" * 32,
            fetched_at=datetime.now(timezone.utc),
            source_url=f"https://example.com/doc{i}.pdf",
        )
        session.add(doc)

    await session.commit()  # all three should succeed
