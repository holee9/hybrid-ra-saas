"""Unit tests for crawl trigger/status API (T-017, REQ-011/012, AC-005).

Uses httpx ASGI test client — no real server or Docker.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_client():
    """Create a test client with mocked DB and orchestrator."""

    # Patch Settings to avoid requiring real env vars
    from unittest.mock import patch, MagicMock

    fake_settings = MagicMock()
    fake_settings.database_url = "sqlite+aiosqlite:///:memory:"
    fake_settings.crawler_fda_enabled = True
    fake_settings.crawler_mfds_enabled = False
    fake_settings.crawler_eu_mdr_enabled = False
    fake_settings.request_timeout = 30.0
    fake_settings.retry_count = 3
    fake_settings.retry_backoff_initial = 2.0
    fake_settings.retry_backoff_multiplier = 2.0
    fake_settings.rate_limit_per_source = 1.0
    fake_settings.blob_account_name = "test"
    fake_settings.blob_container_name = "test"
    fake_settings.blob_account_key = "test"
    fake_settings.appinsights_connection_string = "InstrumentationKey=fake"

    # Pre-populate job registry for status tests
    from app.services.orchestrator import job_registry

    job_registry.clear()

    with patch("app.config.Settings", return_value=fake_settings):
        with patch("app.main.Settings", return_value=fake_settings):
            with patch("app.database.init_engine"):
                from app.main import create_app

                test_app = create_app()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_trigger_returns_job_id(app_client):
    """POST /crawl/trigger returns 202 with a job_id."""
    from unittest.mock import patch

    async def mock_run():
        from app.services.orchestrator import job_registry
        import uuid

        jid = str(uuid.uuid4())
        job_registry[jid] = {"status": "pending", "document_count": 0}
        return jid

    async def mock_execute(job_id: str) -> None:
        from app.services.orchestrator import job_registry

        job_registry[job_id] = {"status": "completed", "document_count": 0}

    with patch("app.routers.crawl.run_crawl_job", new=mock_run):
        with patch("app.routers.crawl._execute_crawl_job", new=mock_execute):
            response = await app_client.post("/crawl/trigger")

    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["job_id"] is not None


@pytest.mark.asyncio
async def test_trigger_is_non_blocking_returns_before_job_completes(app_client):
    """POST /crawl/trigger registers job as 'pending' and returns 202 immediately (REQ-011).

    The endpoint uses BackgroundTasks — the HTTP response is returned before
    _execute_crawl_job runs. We verify this by:
    1. Patching run_crawl_job to register the job and return the job_id.
    2. Patching _execute_crawl_job with a no-op so the background task completes
       instantly without touching the registry (simulating a fast, non-blocking return).
    3. The job_id registered as 'pending' must be present in the registry at response time.
    """
    from unittest.mock import patch

    execute_call_count = 0

    async def fast_register() -> str:
        import uuid
        from app.services.orchestrator import job_registry

        jid = str(uuid.uuid4())
        job_registry[jid] = {"status": "pending", "document_count": 0}
        return jid

    async def noop_execute(job_id: str) -> None:
        # Background task: do not update registry — let the test observe 'pending'
        nonlocal execute_call_count
        execute_call_count += 1

    with patch("app.routers.crawl.run_crawl_job", new=fast_register):
        with patch("app.routers.crawl._execute_crawl_job", new=noop_execute):
            response = await app_client.post("/crawl/trigger")

    # HTTP response arrives with 202 — BackgroundTasks is scheduled, not awaited inline
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    job_id = body["job_id"]

    # Job must exist in registry (registered before the background task runs)
    from app.services.orchestrator import job_registry

    assert job_id in job_registry
    # Status is 'pending' because noop_execute does not change it
    assert job_registry[job_id]["status"] == "pending"
    # The background task was scheduled and executed exactly once via add_task —
    # guards against the endpoint silently dropping the BackgroundTasks wiring
    assert execute_call_count == 1


@pytest.mark.asyncio
async def test_status_returns_known_job():
    """GET /crawl/status/{job_id} returns status for a known job."""
    import uuid
    from app.services.orchestrator import job_registry
    from unittest.mock import patch, MagicMock

    # Setup a known job in the registry
    job_id = str(uuid.uuid4())
    job_registry[job_id] = {"status": "completed", "document_count": 3}

    fake_settings = MagicMock()
    fake_settings.database_url = "sqlite+aiosqlite:///:memory:"
    fake_settings.crawler_fda_enabled = True
    fake_settings.crawler_mfds_enabled = False
    fake_settings.crawler_eu_mdr_enabled = False
    fake_settings.request_timeout = 30.0
    fake_settings.retry_count = 3
    fake_settings.retry_backoff_initial = 2.0
    fake_settings.retry_backoff_multiplier = 2.0
    fake_settings.rate_limit_per_source = 1.0
    fake_settings.blob_account_name = "test"
    fake_settings.blob_container_name = "test"
    fake_settings.blob_account_key = "test"
    fake_settings.appinsights_connection_string = "InstrumentationKey=fake"

    with patch("app.config.Settings", return_value=fake_settings):
        with patch("app.main.Settings", return_value=fake_settings):
            with patch("app.database.init_engine"):
                from app.main import create_app

                test_app = create_app()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get(f"/crawl/status/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "completed"


@pytest.mark.asyncio
async def test_status_returns_404_for_unknown_job():
    """GET /crawl/status/{unknown_id} returns 404."""
    from unittest.mock import patch, MagicMock
    from app.services.orchestrator import job_registry

    job_registry.clear()

    fake_settings = MagicMock()
    fake_settings.database_url = "sqlite+aiosqlite:///:memory:"
    fake_settings.crawler_fda_enabled = True
    fake_settings.crawler_mfds_enabled = False
    fake_settings.crawler_eu_mdr_enabled = False
    fake_settings.request_timeout = 30.0
    fake_settings.retry_count = 3
    fake_settings.retry_backoff_initial = 2.0
    fake_settings.retry_backoff_multiplier = 2.0
    fake_settings.rate_limit_per_source = 1.0
    fake_settings.blob_account_name = "test"
    fake_settings.blob_container_name = "test"
    fake_settings.blob_account_key = "test"
    fake_settings.appinsights_connection_string = "InstrumentationKey=fake"

    with patch("app.config.Settings", return_value=fake_settings):
        with patch("app.main.Settings", return_value=fake_settings):
            with patch("app.database.init_engine"):
                from app.main import create_app

                test_app = create_app()

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/crawl/status/nonexistent-job-id")

    assert response.status_code == 404
