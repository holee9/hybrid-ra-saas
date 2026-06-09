"""T-LIST: GET /parse/jobs list endpoint + _extract_summary_fields unit tests.

Integration tests use @skip_no_docker — CI only.
Unit tests (_extract_summary_fields) require no Docker.
"""
import os
import pytest
from tests.conftest import skip_no_docker

# Required env for module-level imports
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


# ---------------------------------------------------------------------------
# Unit tests — pure function, no Docker required
# ---------------------------------------------------------------------------

def test_extract_summary_fields_none_result_json():
    """_extract_summary_fields returns (None, False) when result_json is None."""
    from app.routers.parse import _extract_summary_fields
    confidence, requires = _extract_summary_fields(None)
    assert confidence is None
    assert requires is False


def test_extract_summary_fields_empty_dict():
    """_extract_summary_fields returns (None, False) when result_json is {}."""
    from app.routers.parse import _extract_summary_fields
    confidence, requires = _extract_summary_fields({})
    assert confidence is None
    assert requires is False


def test_extract_summary_fields_no_parsed_fields_key():
    """_extract_summary_fields returns (None, False) when parsed_fields key absent."""
    from app.routers.parse import _extract_summary_fields
    confidence, requires = _extract_summary_fields({"other_key": "value"})
    assert confidence is None
    assert requires is False


def test_extract_summary_fields_normal():
    """_extract_summary_fields extracts confidence and requires_correction."""
    from app.routers.parse import _extract_summary_fields
    result_json = {
        "parsed_fields": {
            "overall_confidence": 0.85,
            "requires_correction": True,
        }
    }
    confidence, requires = _extract_summary_fields(result_json)
    assert confidence == pytest.approx(0.85)
    assert requires is True


def test_extract_summary_fields_requires_correction_false():
    """_extract_summary_fields handles requires_correction=False."""
    from app.routers.parse import _extract_summary_fields
    result_json = {
        "parsed_fields": {
            "overall_confidence": 0.92,
            "requires_correction": False,
        }
    }
    confidence, requires = _extract_summary_fields(result_json)
    assert confidence == pytest.approx(0.92)
    assert requires is False


def test_extract_summary_fields_missing_confidence():
    """_extract_summary_fields returns None for confidence when key absent."""
    from app.routers.parse import _extract_summary_fields
    result_json = {"parsed_fields": {"requires_correction": True}}
    confidence, requires = _extract_summary_fields(result_json)
    assert confidence is None
    assert requires is True


# ---------------------------------------------------------------------------
# Integration tests — require Docker (CI only)
# ---------------------------------------------------------------------------

pytestmark_int = pytest.mark.usefixtures()


def _make_zip_bytes() -> bytes:
    """Create a minimal valid DOCX (ZIP) for upload tests."""
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
        )
    return buf.getvalue()


async def _upload_doc(client, token: str, tenant: str) -> tuple[str, str]:
    """Upload a document and return (doc_id, job_id)."""
    resp = await client.post(
        "/documents/upload",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": tenant},
        files={"file": ("test.docx", _make_zip_bytes(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert resp.status_code == 200, f"upload failed: {resp.text}"
    body = resp.json()
    return body["doc_id"], body["parse_job_id"]


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_returns_empty_for_new_tenant(client):
    """GET /parse/jobs returns empty list for a tenant with no jobs."""
    from app.core.security import create_token
    token = create_token("user-list-1", "tenant-list-empty")
    resp = await client.get(
        "/parse/jobs",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-empty"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["skip"] == 0
    assert body["limit"] == 50


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_tenant_isolation(client):
    """GET /parse/jobs only returns jobs for the requesting tenant."""
    from app.core.security import create_token

    # Tenant A uploads a document
    token_a = create_token("user-list-a", "tenant-list-a")
    await _upload_doc(client, token_a, "tenant-list-a")

    # Tenant B should see zero jobs
    token_b = create_token("user-list-b", "tenant-list-b")
    resp = await client.get(
        "/parse/jobs",
        headers={"Authorization": f"Bearer {token_b}", "X-Tenant-ID": "tenant-list-b"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_returns_own_jobs(client):
    """GET /parse/jobs returns all jobs for the correct tenant."""
    from app.core.security import create_token
    token = create_token("user-list-own", "tenant-list-own")

    _, job_id = await _upload_doc(client, token, "tenant-list-own")

    resp = await client.get(
        "/parse/jobs",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-own"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["job_id"] == job_id
    assert item["status"] in ("pending", "running", "done", "failed")
    assert "doc_id" in item
    assert "created_at" in item
    # overall_confidence is None for a freshly uploaded (pending) job
    assert item["overall_confidence"] is None
    assert item["requires_correction"] is False


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_status_filter(client):
    """GET /parse/jobs?status=done returns only done jobs."""
    from app.core.security import create_token
    from app.services.parser import StubParserService, ParseResult
    from app.jobs.parse_job import run_parse_job

    token = create_token("user-list-filter", "tenant-list-filter")
    _, job_id = await _upload_doc(client, token, "tenant-list-filter")

    # Run the job so it becomes "done"
    parser = StubParserService(
        ParseResult(confidence=0.9, field_candidates={"title": "Doc"}, required_missing=[])
    )
    await run_parse_job(job_id=job_id, doc_id="ignored", tenant="tenant-list-filter", parser=parser)

    resp_done = await client.get(
        "/parse/jobs?status=done",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-filter"},
    )
    assert resp_done.status_code == 200
    body = resp_done.json()
    assert body["total"] >= 1
    for item in body["items"]:
        assert item["status"] == "done"

    # status=pending should be 0 for this tenant (job already ran)
    resp_pending = await client.get(
        "/parse/jobs?status=pending",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-filter"},
    )
    assert resp_pending.status_code == 200
    body_pending = resp_pending.json()
    for item in body_pending["items"]:
        assert item["status"] == "pending"


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_invalid_status_returns_422(client):
    """GET /parse/jobs?status=invalid returns 422."""
    from app.core.security import create_token
    token = create_token("user-list-422", "tenant-list-422")
    resp = await client.get(
        "/parse/jobs?status=invalid_status",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-422"},
    )
    assert resp.status_code == 422


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_pagination(client):
    """GET /parse/jobs skip/limit correctly paginates."""
    from app.core.security import create_token
    token = create_token("user-list-page", "tenant-list-page")

    # Upload 3 documents
    for _ in range(3):
        await _upload_doc(client, token, "tenant-list-page")

    # Get all
    resp_all = await client.get(
        "/parse/jobs?skip=0&limit=50",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-page"},
    )
    body_all = resp_all.json()
    assert body_all["total"] == 3

    # Page 1: limit=2
    resp_p1 = await client.get(
        "/parse/jobs?skip=0&limit=2",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-page"},
    )
    body_p1 = resp_p1.json()
    assert len(body_p1["items"]) == 2
    assert body_p1["total"] == 3
    assert body_p1["skip"] == 0
    assert body_p1["limit"] == 2

    # Page 2: skip=2, limit=2
    resp_p2 = await client.get(
        "/parse/jobs?skip=2&limit=2",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-page"},
    )
    body_p2 = resp_p2.json()
    assert len(body_p2["items"]) == 1
    assert body_p2["total"] == 3


@skip_no_docker
@pytest.mark.integration
async def test_list_jobs_requires_correction_filter(client):
    """GET /parse/jobs?requires_correction=true returns only correction-needed jobs."""
    from app.core.security import create_token
    from app.services.parser import StubParserService, ParseResult
    from app.jobs.parse_job import run_parse_job

    token = create_token("user-list-req", "tenant-list-req")
    _, job_id = await _upload_doc(client, token, "tenant-list-req")

    # Run with low confidence to trigger requires_correction=True
    parser = StubParserService(
        ParseResult(confidence=0.3, field_candidates={}, required_missing=["device_name"])
    )
    await run_parse_job(job_id=job_id, doc_id="ignored", tenant="tenant-list-req", parser=parser)

    resp = await client.get(
        "/parse/jobs?requires_correction=true",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-list-req"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # All returned items must have requires_correction=True
    for item in body["items"]:
        assert item["requires_correction"] is True
