"""arq crawl job task for cloud-control-plane (AC-006, SPEC-JOBQUEUE-001).

Migrated from FastAPI BackgroundTasks to arq persistent queue.
ctx must be the first argument for all arq task functions.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.orchestrator import job_registry

logger = get_logger(__name__)


async def execute_crawl_job(ctx: dict, job_id: str) -> None:
    """Execute the crawl pipeline for a pre-registered job_id (AC-006).

    # @MX:ANCHOR: [AUTO] arq crawl task — enqueued by POST /crawl/trigger
    # @MX:REASON: External crawl trigger boundary; migrated from BackgroundTasks to arq

    Args:
        ctx: arq worker context (MUST be first arg).
        job_id: Job identifier registered in job_registry.
    """
    from app.config import Settings
    from app.database import _session_factory
    from app.services.storage import make_storage_service
    from app.routers.crawl import _build_orchestrator

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
