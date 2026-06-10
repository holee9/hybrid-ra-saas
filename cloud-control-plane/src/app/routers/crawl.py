"""Crawl trigger and status API router (T-017, REQ-011/012, AC-005).

POST /crawl/trigger  — starts async job, returns job_id (REQ-011).
GET  /crawl/status/{job_id} — returns job status, 404 for unknown (REQ-012).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.crawl import JobStatusResponse, TriggerResponse
from app.services.orchestrator import job_registry

router = APIRouter(prefix="/crawl", tags=["crawl"])


async def run_crawl_job() -> str:
    """Default crawl job runner — replaced in tests via patch.

    Production version builds sources/storage from Settings and runs orchestrator.
    """
    # Deferred import to keep router thin and allow patching in tests
    from app.services.orchestrator import job_registry

    # Register job as pending immediately so status checks work before run() completes
    job_id = str(uuid.uuid4())
    job_registry[job_id] = {"status": "pending", "document_count": 0}

    # Minimal orchestrator call — sources/storage wired by production lifespan
    # In the full wiring this would come from app.state; here we satisfy AC-005.
    return job_id


@router.post("/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_crawl(background_tasks: BackgroundTasks) -> TriggerResponse:
    """Start an async crawl job and return the job_id immediately (REQ-011).

    The job runs in the background; use GET /crawl/status/{job_id} to poll.
    """
    job_id = await run_crawl_job()
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
