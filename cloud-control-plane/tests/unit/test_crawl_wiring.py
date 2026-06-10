"""Unit tests for run_crawl_job() wiring (P2 carry-over, REQ-011, AC-005).

Verifies that run_crawl_job() builds sources from Settings, runs the
orchestrator pipeline, and transitions the job registry status correctly.

All external I/O is patched — no real DB, network, or blob storage.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_fake_settings(
    *,
    fda_enabled: bool = True,
    mfds_enabled: bool = False,
    eu_mdr_enabled: bool = False,
) -> MagicMock:
    s = MagicMock()
    s.database_url = "sqlite+aiosqlite:///:memory:"
    s.crawler_fda_enabled = fda_enabled
    s.crawler_mfds_enabled = mfds_enabled
    s.crawler_eu_mdr_enabled = eu_mdr_enabled
    s.request_timeout = 30.0
    s.retry_count = 3
    s.retry_backoff_initial = 2.0
    s.retry_backoff_multiplier = 2.0
    s.rate_limit_per_source = 1.0
    s.blob_account_name = "acct"
    s.blob_container_name = "container"
    s.blob_account_key = "key"
    s.appinsights_connection_string = "InstrumentationKey=fake"
    s.fda_listing_url = "https://fda.gov/guidance/"
    s.fda_media_prefix = "/media/"
    s.mfds_listing_url = "https://www.mfds.go.kr/brd/m_218/list.do"
    s.mfds_doc_prefix = "/brd/"
    s.eu_mdr_listing_url = "https://eur-lex.europa.eu/search.html"
    s.eu_mdr_doc_prefix = "/legal-content/"
    return s


@pytest.mark.asyncio
async def test_run_crawl_job_returns_job_id():
    """run_crawl_job() returns a non-None job_id string."""
    from app.routers.crawl import run_crawl_job
    from app.services.orchestrator import job_registry

    job_registry.clear()

    expected_orch_id = str(uuid.uuid4())
    job_registry[expected_orch_id] = {"status": "completed", "document_count": 0}

    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=expected_orch_id)

    fake_session = MagicMock()
    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.config.Settings", return_value=_make_fake_settings()):
        with patch("app.services.storage.make_storage_service", return_value=MagicMock()):
            with patch("app.database._session_factory", fake_session_factory):
                with patch("app.routers.crawl._build_orchestrator", return_value=mock_orch):
                    job_id = await run_crawl_job()

    assert job_id is not None
    assert isinstance(job_id, str)


@pytest.mark.asyncio
async def test_run_crawl_job_sets_pending_before_run():
    """run_crawl_job() registers 'pending' status before calling orchestrator.run()."""
    from app.routers.crawl import run_crawl_job
    from app.services.orchestrator import job_registry

    job_registry.clear()

    statuses_at_run_time: list[str] = []
    orch_id = str(uuid.uuid4())

    async def recording_run() -> str:
        for info in job_registry.values():
            statuses_at_run_time.append(info["status"])
        job_registry[orch_id] = {"status": "completed", "document_count": 0}
        return orch_id

    mock_orch = MagicMock()
    mock_orch.run = recording_run

    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.config.Settings", return_value=_make_fake_settings()):
        with patch("app.services.storage.make_storage_service", return_value=MagicMock()):
            with patch("app.database._session_factory", fake_session_factory):
                with patch("app.routers.crawl._build_orchestrator", return_value=mock_orch):
                    await run_crawl_job()

    assert "pending" in statuses_at_run_time


@pytest.mark.asyncio
async def test_build_orchestrator_only_fda_enabled():
    """Only FDASource is built when only fda is enabled in Settings."""
    from app.routers.crawl import _build_orchestrator

    settings = _make_fake_settings(fda_enabled=True, mfds_enabled=False, eu_mdr_enabled=False)

    mock_fda_instance = MagicMock()
    MockFDA = MagicMock(return_value=mock_fda_instance)
    mock_mfds_instance = MagicMock()
    MockMFDS = MagicMock(return_value=mock_mfds_instance)
    mock_eu_instance = MagicMock()
    MockEU = MagicMock(return_value=mock_eu_instance)

    import sys

    fda_mock_mod = MagicMock()
    fda_mock_mod.FDASource = MockFDA
    mfds_mock_mod = MagicMock()
    mfds_mock_mod.MFDSSource = MockMFDS
    eu_mock_mod = MagicMock()
    eu_mock_mod.EUMDRSource = MockEU

    _SENTINEL = object()
    orig_fda = sys.modules.get("app.services.crawler.fda", _SENTINEL)
    orig_mfds = sys.modules.get("app.services.crawler.mfds", _SENTINEL)
    orig_eu = sys.modules.get("app.services.crawler.eu_mdr", _SENTINEL)

    sys.modules["app.services.crawler.fda"] = fda_mock_mod
    sys.modules["app.services.crawler.mfds"] = mfds_mock_mod
    sys.modules["app.services.crawler.eu_mdr"] = eu_mock_mod

    try:
        with patch("httpx.AsyncClient"):
            _build_orchestrator(settings, MagicMock(), MagicMock())
    finally:
        if orig_fda is _SENTINEL:
            del sys.modules["app.services.crawler.fda"]
        else:
            sys.modules["app.services.crawler.fda"] = orig_fda
        if orig_mfds is _SENTINEL:
            del sys.modules["app.services.crawler.mfds"]
        else:
            sys.modules["app.services.crawler.mfds"] = orig_mfds
        if orig_eu is _SENTINEL:
            del sys.modules["app.services.crawler.eu_mdr"]
        else:
            sys.modules["app.services.crawler.eu_mdr"] = orig_eu

    MockFDA.assert_called_once()
    MockMFDS.assert_not_called()
    MockEU.assert_not_called()


@pytest.mark.asyncio
async def test_build_orchestrator_all_sources_enabled():
    """All three sources are built when all enable flags are True."""
    from app.routers.crawl import _build_orchestrator
    import sys

    settings = _make_fake_settings(fda_enabled=True, mfds_enabled=True, eu_mdr_enabled=True)

    MockFDA = MagicMock()
    MockMFDS = MagicMock()
    MockEU = MagicMock()

    fda_mock_mod = MagicMock()
    fda_mock_mod.FDASource = MockFDA
    mfds_mock_mod = MagicMock()
    mfds_mock_mod.MFDSSource = MockMFDS
    eu_mock_mod = MagicMock()
    eu_mock_mod.EUMDRSource = MockEU

    _SENTINEL = object()
    orig_fda = sys.modules.get("app.services.crawler.fda", _SENTINEL)
    orig_mfds = sys.modules.get("app.services.crawler.mfds", _SENTINEL)
    orig_eu = sys.modules.get("app.services.crawler.eu_mdr", _SENTINEL)

    sys.modules["app.services.crawler.fda"] = fda_mock_mod
    sys.modules["app.services.crawler.mfds"] = mfds_mock_mod
    sys.modules["app.services.crawler.eu_mdr"] = eu_mock_mod

    try:
        with patch("httpx.AsyncClient"):
            _build_orchestrator(settings, MagicMock(), MagicMock())
    finally:
        if orig_fda is _SENTINEL:
            del sys.modules["app.services.crawler.fda"]
        else:
            sys.modules["app.services.crawler.fda"] = orig_fda
        if orig_mfds is _SENTINEL:
            del sys.modules["app.services.crawler.mfds"]
        else:
            sys.modules["app.services.crawler.mfds"] = orig_mfds
        if orig_eu is _SENTINEL:
            del sys.modules["app.services.crawler.eu_mdr"]
        else:
            sys.modules["app.services.crawler.eu_mdr"] = orig_eu

    MockFDA.assert_called_once()
    MockMFDS.assert_called_once()
    MockEU.assert_called_once()


@pytest.mark.asyncio
async def test_run_crawl_job_marks_failed_on_orchestrator_error():
    """If orchestrator.run() raises, job_registry shows 'failed' status."""
    from app.routers.crawl import run_crawl_job
    from app.services.orchestrator import job_registry

    job_registry.clear()

    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(side_effect=RuntimeError("Orchestrator exploded"))

    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.config.Settings", return_value=_make_fake_settings()):
        with patch("app.services.storage.make_storage_service", return_value=MagicMock()):
            with patch("app.database._session_factory", fake_session_factory):
                with patch("app.routers.crawl._build_orchestrator", return_value=mock_orch):
                    job_id = await run_crawl_job()

    assert job_id is not None
    assert job_registry[job_id]["status"] == "failed"


@pytest.mark.asyncio
async def test_run_crawl_job_propagates_orchestrator_job_status():
    """run_crawl_job() copies orchestrator's completed status to the pending entry."""
    from app.routers.crawl import run_crawl_job
    from app.services.orchestrator import job_registry

    job_registry.clear()

    orch_job_id = str(uuid.uuid4())
    job_registry[orch_job_id] = {"status": "completed", "document_count": 5}

    mock_orch = MagicMock()
    mock_orch.run = AsyncMock(return_value=orch_job_id)

    fake_session_factory = MagicMock()
    fake_session_factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch("app.config.Settings", return_value=_make_fake_settings()):
        with patch("app.services.storage.make_storage_service", return_value=MagicMock()):
            with patch("app.database._session_factory", fake_session_factory):
                with patch("app.routers.crawl._build_orchestrator", return_value=mock_orch):
                    trigger_job_id = await run_crawl_job()

    assert trigger_job_id in job_registry
    assert job_registry[trigger_job_id]["status"] == "completed"
