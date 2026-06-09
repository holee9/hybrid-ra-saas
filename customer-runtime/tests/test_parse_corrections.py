"""T-010: PATCH /parse/{job_id}/corrections endpoint 테스트."""
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set required env vars before any app import
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
os.environ.setdefault("MINIO_BUCKET", "ra-documents")
os.environ.setdefault("MINIO_USER", "minioadmin")
os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")


def _make_auth_headers(tenant_id: str = "tenant-001") -> dict:
    """Create test JWT headers."""
    import jwt as pyjwt
    token = pyjwt.encode(
        {"tenant_id": tenant_id, "sub": "test-user"},
        "test-secret-32-bytes-minimum-here!",
        algorithm="HS256",
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id,
    }


def _make_parsed_fields_dict(overall_confidence: float = 0.75) -> dict:
    """Return a parsed_fields dict compatible with result_json storage."""
    from app.schemas.parse import ExtractionStage, FieldExtraction, IFU_FIELD_NAMES, ParsedFields
    fe = FieldExtraction(
        value="original value",
        confidence=overall_confidence,
        stage=ExtractionStage.RULE,
        needs_correction=True,
    )
    kwargs = {name: fe for name in IFU_FIELD_NAMES}
    pf = ParsedFields(overall_confidence=overall_confidence, requires_correction=True, **kwargs)
    return json.loads(pf.model_dump_json())


@pytest.mark.asyncio
async def test_patch_corrections_updates_field_value():
    """scenario 9: PATCH device_name → updated, confidence=1.0, stage=NONE, needs_correction=False."""
    from httpx import ASGITransport, AsyncClient
    from app.models.parse_job import ParseJob, ParseJobStatus
    from app.schemas.parse import IFU_FIELD_NAMES

    parsed_fields_data = _make_parsed_fields_dict(0.65)
    mock_job = MagicMock(spec=ParseJob)
    mock_job.job_id = "job-001"
    mock_job.tenant_id = "tenant-001"
    mock_job.status = ParseJobStatus.DONE
    mock_job.result_json = {"parsed_fields": parsed_fields_data}

    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_job)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    async def mock_get_db():
        yield mock_db

    async def mock_get_tenant(authorization=None, x_tenant_id=None):
        return "tenant-001"

    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

    from app.main import create_app
    from app import deps

    app = create_app()
    app.dependency_overrides[deps.get_db] = mock_get_db
    app.dependency_overrides[deps.get_current_tenant] = mock_get_tenant

    headers = _make_auth_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/parse/job-001/corrections",
            json={"corrections": {"device_name": "X-ray Model A"}},
            headers=headers,
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["parsed_fields"]["device_name"]["value"] == "X-ray Model A"
    assert data["parsed_fields"]["device_name"]["confidence"] == 1.0
    assert data["parsed_fields"]["device_name"]["needs_correction"] is False


@pytest.mark.asyncio
async def test_patch_corrections_unknown_field_returns_422():
    """scenario 10: PATCH unknown_field → 422."""
    from httpx import ASGITransport, AsyncClient
    from app.models.parse_job import ParseJob, ParseJobStatus

    mock_job = MagicMock(spec=ParseJob)
    mock_job.job_id = "job-002"
    mock_job.tenant_id = "tenant-001"
    mock_job.status = ParseJobStatus.DONE
    mock_job.result_json = {"parsed_fields": _make_parsed_fields_dict()}

    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=mock_job)

    async def mock_get_db():
        yield mock_db

    async def mock_get_tenant(authorization=None, x_tenant_id=None):
        return "tenant-001"

    from app.main import create_app
    from app import deps

    app = create_app()
    app.dependency_overrides[deps.get_db] = mock_get_db
    app.dependency_overrides[deps.get_current_tenant] = mock_get_tenant

    headers = _make_auth_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/parse/job-002/corrections",
            json={"corrections": {"unknown_field": "x"}},
            headers=headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_corrections_unknown_job_returns_404():
    """PATCH with unknown job_id → 404."""
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=None)

    async def mock_get_db():
        yield mock_db

    async def mock_get_tenant(authorization=None, x_tenant_id=None):
        return "tenant-001"

    from httpx import ASGITransport, AsyncClient
    from app.main import create_app
    from app import deps

    app = create_app()
    app.dependency_overrides[deps.get_db] = mock_get_db
    app.dependency_overrides[deps.get_current_tenant] = mock_get_tenant

    headers = _make_auth_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.patch(
            "/parse/nonexistent-job/corrections",
            json={"corrections": {"device_name": "X"}},
            headers=headers,
        )

    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_corrections_request_validates_field_whitelist():
    """CorrectionsRequest rejects fields not in IFU_FIELD_NAMES."""
    from pydantic import ValidationError
    from app.schemas.parse import CorrectionsRequest

    with pytest.raises(ValidationError):
        CorrectionsRequest(corrections={"invalid_field_name": "value"})


def test_corrections_request_accepts_valid_fields():
    from app.schemas.parse import CorrectionsRequest

    req = CorrectionsRequest(corrections={"device_name": "Test Device", "product_code": "ABC-001"})
    assert req.corrections["device_name"] == "Test Device"
