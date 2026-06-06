"""T-011: Parser service + parse job state machine + GET /parse/jobs/{job_id}."""
import asyncio
import os
import pytest

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


# --- State machine unit tests ---

def test_valid_transition_uploaded_to_parsing():
    from app.core.state_machine import validate_transition
    from app.models.document import DocumentStatus
    validate_transition(DocumentStatus.UPLOADED, DocumentStatus.PARSING)  # no exception


def test_invalid_transition_raises():
    from app.core.state_machine import validate_transition
    from app.models.document import DocumentStatus
    with pytest.raises(ValueError):
        validate_transition(DocumentStatus.UPLOADED, DocumentStatus.APPROVED)


def test_parsing_to_needs_correction():
    from app.core.state_machine import validate_transition
    from app.models.document import DocumentStatus
    validate_transition(DocumentStatus.PARSING, DocumentStatus.NEEDS_CORRECTION)


def test_parsing_to_ready_for_check():
    from app.core.state_machine import validate_transition
    from app.models.document import DocumentStatus
    validate_transition(DocumentStatus.PARSING, DocumentStatus.READY_FOR_CHECK)


# --- Integration tests (require DB) ---

@pytest.mark.integration
async def test_parse_job_low_confidence_needs_correction(client):
    """Parser confidence=0.5 → Document becomes needs_correction."""
    from app.core.security import create_token
    from app.services.parser import StubParserService, ParseResult
    from app.jobs.parse_job import run_parse_job
    from app.database import async_session
    from app.models.document import Document, DocumentStatus
    from app.models.parse_job import ParseJob, ParseJobStatus
    from app.models.base import new_id
    import io, zipfile

    token = create_token("user-1", "tenant-1")

    # Upload a doc first to get doc_id + job_id
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-1"},
        files={"file": ("test.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200
    body = resp.json()
    doc_id = body["doc_id"]
    job_id = body["parse_job_id"]

    # Run parse job with low-confidence stub parser
    low_parser = StubParserService(
        ParseResult(confidence=0.5, field_candidates={"title": "My Doc"}, required_missing=["hazard"])
    )
    await run_parse_job(job_id=job_id, doc_id=doc_id, tenant="tenant-1", parser=low_parser)

    # Check document status
    async with async_session() as db:
        doc = await db.get(Document, doc_id)
        assert doc.status == DocumentStatus.NEEDS_CORRECTION

    # Check via API
    job_resp = await client.get(
        f"/parse/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-1"},
    )
    assert job_resp.status_code == 200
    job_body = job_resp.json()
    assert job_body["status"] == "done"
    assert job_body["confidence"] == 0.5


@pytest.mark.integration
async def test_parse_job_high_confidence_ready_for_check(client):
    """Parser confidence=0.9 → Document becomes ready_for_check."""
    from app.core.security import create_token
    from app.services.parser import StubParserService, ParseResult
    from app.jobs.parse_job import run_parse_job
    from app.database import async_session
    from app.models.document import Document, DocumentStatus
    import io, zipfile

    token = create_token("user-2", "tenant-2")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-2"},
        files={"file": ("srs.docx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200
    body = resp.json()
    doc_id = body["doc_id"]
    job_id = body["parse_job_id"]

    high_parser = StubParserService(
        ParseResult(confidence=0.9, field_candidates={"device_name": "X200"}, required_missing=[])
    )
    await run_parse_job(job_id=job_id, doc_id=doc_id, tenant="tenant-2", parser=high_parser)

    async with async_session() as db:
        doc = await db.get(Document, doc_id)
        assert doc.status == DocumentStatus.READY_FOR_CHECK


@pytest.mark.integration
async def test_parse_job_status_transitions_via_api(client):
    """GET /parse/jobs/{id} reflects pending→running→done transitions."""
    from app.core.security import create_token
    from app.services.parser import StubParserService, ParseResult
    from app.jobs.parse_job import run_parse_job
    import io, zipfile

    token = create_token("user-3", "tenant-3")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')

    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-3"},
        files={"file": ("report.xlsx", buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert resp.status_code == 200
    job_id = resp.json()["parse_job_id"]
    doc_id = resp.json()["doc_id"]

    # Before running: status should be pending
    job_resp = await client.get(
        f"/parse/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-3"},
    )
    assert job_resp.json()["status"] == "pending"

    # Run job
    parser = StubParserService(ParseResult(confidence=0.85, field_candidates={}, required_missing=[]))
    await run_parse_job(job_id=job_id, doc_id=doc_id, tenant="tenant-3", parser=parser)

    # After running: status should be done
    job_resp2 = await client.get(
        f"/parse/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-3"},
    )
    assert job_resp2.json()["status"] == "done"
