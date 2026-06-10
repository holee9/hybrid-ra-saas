"""Crawl trigger and status API router (T-017/P2-carry-over, REQ-011/012, AC-005).

POST /crawl/trigger  — starts async job, returns job_id (REQ-011).
GET  /crawl/status/{job_id} — returns job status, 404 for unknown (REQ-012).

run_crawl_job() wires Settings → sources → storage → DB session → CrawlOrchestrator.
Job status lifecycle: pending → running (managed by orchestrator) → completed/failed.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.logging import get_logger
from app.schemas.crawl import JobStatusResponse, TriggerResponse
from app.services.orchestrator import CrawlOrchestrator, job_registry

logger = get_logger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])


def _build_orchestrator(settings: Any, storage: Any, session: Any) -> CrawlOrchestrator:
    """Build a CrawlOrchestrator from Settings, storage service, and DB session.

    Constructs only the sources that are enabled in Settings.
    Imported lazily so the router module stays importable without a live DB/Blob.

    # @MX:NOTE: [AUTO] Source enable flags (crawler_fda_enabled, etc.) come from Settings.
    #           Each source receives its listing URL and path prefix from Settings as well,
    #           so HTML structure changes can be mitigated via env-var override.
    """
    import httpx

    from app.services.crawler.eu_mdr import EUMDRSource
    from app.services.crawler.fda import FDASource
    from app.services.crawler.mfds import MFDSSource

    client = httpx.AsyncClient(timeout=settings.request_timeout)

    sources: list[Any] = []

    if settings.crawler_fda_enabled:
        sources.append(
            FDASource(
                client=client,
                listing_url=settings.fda_listing_url,
                media_path_prefix=settings.fda_media_prefix,
                retry_count=settings.retry_count,
                initial_delay=settings.retry_backoff_initial,
                multiplier=settings.retry_backoff_multiplier,
            )
        )

    if settings.crawler_mfds_enabled:
        sources.append(
            MFDSSource(
                client=client,
                listing_url=settings.mfds_listing_url,
                doc_path_prefix=settings.mfds_doc_prefix,
                retry_count=settings.retry_count,
                initial_delay=settings.retry_backoff_initial,
                multiplier=settings.retry_backoff_multiplier,
            )
        )

    if settings.crawler_eu_mdr_enabled:
        sources.append(
            EUMDRSource(
                client=client,
                listing_url=settings.eu_mdr_listing_url,
                doc_path_prefix=settings.eu_mdr_doc_prefix,
                retry_count=settings.retry_count,
                initial_delay=settings.retry_backoff_initial,
                multiplier=settings.retry_backoff_multiplier,
            )
        )

    return CrawlOrchestrator(
        sources=sources,
        storage=storage,
        session=session,
    )


async def _execute_crawl_job(job_id: str) -> None:
    """Execute the crawl pipeline for a pre-registered job_id.

    Called as a background task by trigger_crawl().
    Errors are logged with exc_info and job is marked "failed" — never re-raised
    because there is no caller to receive the exception in a background task.
    """
    from app.config import Settings
    from app.database import _session_factory
    from app.services.storage import make_storage_service

    settings = Settings()
    storage = make_storage_service(settings)

    try:
        if _session_factory is None:
            raise RuntimeError("Database not initialized. Call init_engine() first.")
        async with _session_factory() as session:
            orch = _build_orchestrator(settings, storage, session)
            await orch.run(job_id=job_id)
    except Exception:
        logger.error(
            "job_failed",
            extra={"job_id": job_id, "event": "job_failed"},
            exc_info=True,
        )
        job_registry[job_id] = {"status": "failed", "document_count": 0}


async def run_crawl_job() -> str:
    """Register a new job as 'pending' and return its job_id.

    The actual crawl execution must be scheduled separately via background_tasks.
    Kept as a standalone async function for testability.
    """
    job_id = str(uuid.uuid4())
    job_registry[job_id] = {"status": "pending", "document_count": 0}
    return job_id


@router.post("/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_crawl(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Start an async crawl job and return the job_id immediately (REQ-011).

    Registers the job as 'pending', schedules it as a background task,
    and returns 202 + job_id before the crawl completes.
    Use GET /crawl/status/{job_id} to poll for completion.
    """
    job_id = await run_crawl_job()
    background_tasks.add_task(_execute_crawl_job, job_id)
    return TriggerResponse(job_id=job_id)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Return the current status of a crawl job (REQ-012).

    Returns 404 if job_id is not found in the in-memory registry.
    """
    if job_id not in job_registry:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")

    info = job_registry[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=info["status"],
        document_count=info.get("document_count"),
        skipped_count=info.get("skipped_count"),
        failed_count=info.get("failed_count"),
    )
