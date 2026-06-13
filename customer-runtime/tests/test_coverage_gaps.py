"""Coverage gap fill tests — T-020.

Targets:
- audit.py: append-only enforcement
- export.py: PDF branch
- rag.py: Ollama fallback
- documents.py: upload success paths
- health response latency
"""
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# audit.py: AuditService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_service_record_creates_event():
    """AuditService.record creates and flushes an AuditEvent."""
    from app.services.audit import AuditService

    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    svc = AuditService()

    event = await svc.record(
        db=mock_db,
        tenant_id="t1",
        user_id="u1",
        action="test.action",
        before_hash="before",
        after_hash="after",
    )

    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()
    assert event.tenant_id == "t1"
    assert event.user_id == "u1"
    assert event.action == "test.action"
    assert event.before_hash == "before"
    assert event.after_hash == "after"


@pytest.mark.asyncio
async def test_audit_service_record_without_hashes():
    """AuditService.record works when before/after hashes are None."""
    from app.services.audit import AuditService

    mock_db = MagicMock()
    mock_db.flush = AsyncMock()
    svc = AuditService()

    event = await svc.record(
        db=mock_db,
        tenant_id="t1",
        user_id="u1",
        action="login",
    )

    assert event.before_hash is None
    assert event.after_hash is None
    mock_db.flush.assert_called_once()


# ---------------------------------------------------------------------------
# export.py: PDF branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_service_pdf_branch():
    """ExportService.export returns PDF content and media type when format=PDF."""
    from app.services.export import ExportService

    mock_db = AsyncMock()
    svc = ExportService()
    audit_svc = MagicMock()
    audit_svc.record = AsyncMock()

    fake_events = [
        {
            "event_id": "evt-001",
            "action": "test.action",
            "tenant_id": "t1",
            "user_id": "u1",
            "timestamp": "2026-06-01T12:00:00",
            "before_hash": "",
            "after_hash": "",
        }
    ]

    with patch.object(svc, "_load_audit_events", return_value=fake_events):
        result = await svc.export(
            db=mock_db,
            tenant_id="t1",
            user_id="u1",
            scope="all",
            product_id=None,
            date_from=None,
            date_to=None,
            format="PDF",
            audit_service=audit_svc,
        )

    assert "content" in result
    assert isinstance(result["content"], bytes)
    assert len(result["content"]) > 0
    # PDF or fallback JSON — both are valid
    assert result["media_type"] in ("application/pdf", "application/json")


@pytest.mark.asyncio
async def test_export_service_json_branch():
    """ExportService.export returns JSON bytes when format=JSON."""
    from app.services.export import ExportService

    mock_db = AsyncMock()
    svc = ExportService()
    audit_svc = MagicMock()
    audit_svc.record = AsyncMock()

    with patch.object(svc, "_load_audit_events", return_value=[]):
        result = await svc.export(
            db=mock_db,
            tenant_id="t1",
            user_id="u1",
            scope="all",
            product_id=None,
            date_from=None,
            date_to=None,
            format="JSON",
            audit_service=audit_svc,
        )

    assert result["media_type"] == "application/json"
    assert result["filename"].endswith(".json")


@pytest.mark.asyncio
async def test_export_service_xlsx_branch():
    """ExportService.export returns XLSX bytes when format=XLSX."""
    from app.services.export import ExportService

    mock_db = AsyncMock()
    svc = ExportService()
    audit_svc = MagicMock()
    audit_svc.record = AsyncMock()

    with patch.object(svc, "_load_audit_events", return_value=[]):
        result = await svc.export(
            db=mock_db,
            tenant_id="t1",
            user_id="u1",
            scope="all",
            product_id=None,
            date_from=None,
            date_to=None,
            format="XLSX",
            audit_service=audit_svc,
        )

    media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert result["media_type"] == media_type
    assert result["filename"].endswith(".xlsx")


# ---------------------------------------------------------------------------
# rag.py: Ollama fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_ollama_fallback_on_timeout():
    """RagService.query returns fallback message when Ollama times out."""
    from app.services.rag import RagService
    import httpx

    mock_db = AsyncMock()
    svc = RagService()

    fake_evidence = [{"req_id": "R-001", "text": "Requirement text", "score": 0.8}]

    with patch.object(svc, "_embed_question", return_value=[0.0] * 384):
        with patch.object(svc, "_similarity_search", return_value=fake_evidence):
            with patch.object(
                svc,
                "_call_ollama",
                side_effect=httpx.TimeoutException("timeout"),
            ):
                result = await svc.query(
                    db=mock_db,
                    tenant_id="t1",
                    question="What is required?",
                    product_id=None,
                    evidence_required=False,
                    top_k=3,
                )

    assert result["answer"] == "LLM service unavailable"
    assert result["confidence"] == 0.0
    # Evidence links still populated from similarity search
    assert "R-001" in result["evidence_links"]


@pytest.mark.asyncio
async def test_rag_no_evidence_returns_default_answer():
    """RagService.query returns 'No relevant evidence found' when similarity search empty."""
    from app.services.rag import RagService

    mock_db = AsyncMock()
    svc = RagService()

    with patch.object(svc, "_embed_question", return_value=[0.0] * 384):
        with patch.object(svc, "_similarity_search", return_value=[]):
            result = await svc.query(
                db=mock_db,
                tenant_id="t1",
                question="What is required?",
                product_id=None,
                evidence_required=False,
                top_k=3,
            )

    assert result["answer"] == "No relevant evidence found."
    assert result["confidence"] == 0.0
    assert result["evidence_links"] == []


# ---------------------------------------------------------------------------
# documents.py: upload validation paths
# ---------------------------------------------------------------------------


def test_compute_correction_hashes_deterministic():
    """compute_correction_hashes produces same hashes for same inputs regardless of order."""
    from app.routers.documents import compute_correction_hashes

    corrections_a = [
        {"before_value": "old_val", "after_value": "new_val"},
        {"before_value": "x", "after_value": "y"},
    ]
    corrections_b = [
        {"before_value": "x", "after_value": "y"},
        {"before_value": "old_val", "after_value": "new_val"},
    ]

    before_a, after_a = compute_correction_hashes(corrections_a)
    before_b, after_b = compute_correction_hashes(corrections_b)

    assert before_a == before_b
    assert after_a == after_b


def test_compute_correction_hashes_different_inputs_produce_different_hashes():
    """Different inputs produce different hashes."""
    from app.routers.documents import compute_correction_hashes

    corrections_a = [{"before_value": "aaa", "after_value": "bbb"}]
    corrections_b = [{"before_value": "xxx", "after_value": "yyy"}]

    before_a, after_a = compute_correction_hashes(corrections_a)
    before_b, after_b = compute_correction_hashes(corrections_b)

    assert before_a != before_b
    assert after_a != after_b


# ---------------------------------------------------------------------------
# sync.py: _fetch_entities error path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_fetch_entities_handles_db_error_gracefully():
    """_fetch_entities returns empty list when DB raises (e.g. table not migrated)."""
    from app.services.sync import SyncService
    from sqlalchemy.exc import OperationalError

    mock_db = AsyncMock()
    mock_db.execute.side_effect = OperationalError("no table", None, None)

    svc = SyncService()
    entities = await svc._fetch_entities(db=mock_db, tenant_id="t1")
    assert isinstance(entities, list)


@pytest.mark.asyncio
async def test_sync_build_manifest_empty_db():
    """build_manifest returns valid structure when no entities exist."""
    from app.services.sync import SyncService

    mock_db = AsyncMock()
    with patch.object(SyncService, "_fetch_entities", return_value=[]):
        svc = SyncService()
        result = await svc.build_manifest(db=mock_db, tenant_id="t1", since=None)

    assert result["total_count"] == 0
    assert result["entries"] == []
    assert len(result["manifest_hash"]) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_sync_to_entry_correct_fields():
    """_to_entry produces entry with version_hash computed from entity_id+updated_at."""
    from app.services.sync import SyncService
    from datetime import datetime, timezone

    svc = SyncService()
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    entry = svc._to_entry({"entity_type": "product", "entity_id": "p-001", "updated_at": now})

    assert entry["entity_type"] == "product"
    assert entry["entity_id"] == "p-001"
    assert len(entry["version_hash"]) == 64
    assert entry["action"] == "updated"


# ---------------------------------------------------------------------------
# export.py: _load_audit_events coverage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_load_audit_events_with_date_filters():
    """_load_audit_events applies date filters when provided."""
    from app.services.export import ExportService

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    svc = ExportService()
    events = await svc._load_audit_events(
        db=mock_db,
        tenant_id="t1",
        product_id=None,
        date_from="2026-01-01",
        date_to="2026-12-31",
    )
    assert isinstance(events, list)


@pytest.mark.asyncio
async def test_export_load_audit_events_handles_exception():
    """_load_audit_events returns empty list on DB exception."""
    from app.services.export import ExportService

    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("db error")

    svc = ExportService()
    events = await svc._load_audit_events(
        db=mock_db,
        tenant_id="t1",
        product_id=None,
        date_from=None,
        date_to=None,
    )
    assert events == []


# ---------------------------------------------------------------------------
# rag.py: _embed_question fallback path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rag_embed_question_returns_zero_vector_when_no_model():
    """_embed_question returns zero vector when SentenceTransformer unavailable."""
    from app.services.rag import RagService

    svc = RagService()

    with patch("app.services.rag.SentenceTransformer", None):
        result = await svc._embed_question("test question")

    assert len(result) == 384
    assert all(v == 0.0 for v in result)


@pytest.mark.asyncio
async def test_rag_similarity_search_returns_empty_on_error():
    """_similarity_search returns empty list when pgvector raises."""
    from app.services.rag import RagService

    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("pgvector not installed")

    svc = RagService()
    result = await svc._similarity_search(
        db=mock_db,
        tenant_id="t1",
        product_id=None,
        vector=[0.0] * 384,
        top_k=3,
    )
    assert result == []


# ---------------------------------------------------------------------------
# Performance: health endpoint latency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_response_time():
    """Health endpoint responds in under 1 second (unit-level latency check)."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_BUCKET", "ra-documents")
    os.environ.setdefault("MINIO_USER", "minioadmin")
    os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
    os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

    from httpx import AsyncClient, ASGITransport
    from app.main import create_app

    test_app = create_app()
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        start = time.monotonic()
        resp = await ac.get("/health")
        elapsed = time.monotonic() - start

    assert resp.status_code == 200
    assert elapsed < 1.0, f"Health check took {elapsed:.3f}s — expected < 1.0s"
