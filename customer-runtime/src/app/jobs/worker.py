"""arq WorkerSettings for the customer-runtime parse job worker (SPEC-JOBQUEUE-001).

AC-002: on_startup performs orphan recovery.
AC-003/004: max_tries=3 with exponential backoff; on_job_abort marks terminal FAILED.
AC-005: Worker runs as a separate arq process (not as a FastAPI background task).
AC-008: Worker emits Redis heartbeat key on each health_check tick.
"""

from __future__ import annotations

import logging

from arq.connections import RedisSettings

from app.jobs.parse_job import run_parse_job
from app.jobs.worker_health import HEARTBEAT_KEY, HEARTBEAT_TTL_SECONDS

logger = logging.getLogger(__name__)


async def on_startup(ctx: dict) -> None:
    """Orphan recovery: detect RUNNING ParseJobs with no active arq entry.

    # @MX:WARN: [AUTO] Modifies ParseJob rows at worker startup — touches DB state.
    # @MX:REASON: Orphan recovery must run before any new jobs are processed.
    #             Race condition possible if multiple workers start simultaneously;
    #             mitigated by Container App single-instance constraint (REQ-NF-JQ-002).

    REQ-JQ-003: On worker startup, re-enqueue or mark failed any
    ParseJob.status='running' jobs not currently tracked in arq.
    """
    from sqlalchemy import select
    from app.database import async_session
    from app.db.tenant_context import bypass_tenant_context
    from app.models.parse_job import ParseJob, ParseJobStatus

    logger.info("worker.on_startup: scanning for orphaned RUNNING jobs")

    try:
        async with bypass_tenant_context():
            async with async_session() as db:
                result = await db.execute(
                    select(ParseJob).where(ParseJob.status == ParseJobStatus.RUNNING)
                )
                orphans = result.scalars().all()

        if not orphans:
            logger.info("worker.on_startup: no orphaned jobs found")
            return

        pool = ctx.get("redis")
        for job in orphans:
            if pool is not None:
                try:
                    # Re-enqueue: arq will pick up and process
                    await pool.enqueue_job(
                        "run_parse_job",
                        job.job_id,
                        job.doc_id,
                        job.tenant_id,
                    )
                    logger.warning(
                        "worker.on_startup: re-enqueued orphan job=%s", job.job_id
                    )
                except Exception:
                    # If re-enqueue fails, mark as failed (AC-002 fallback)
                    logger.error(
                        "worker.on_startup: failed to re-enqueue job=%s, marking FAILED",
                        job.job_id,
                        exc_info=True,
                    )
                    async with bypass_tenant_context():
                        async with async_session() as db:
                            j = await db.get(ParseJob, job.job_id)
                            if j is not None:
                                j.status = ParseJobStatus.FAILED
                                j.error = "Orphan recovery: could not re-enqueue"
            else:
                # No pool available — mark failed to prevent stuck state
                async with bypass_tenant_context():
                    async with async_session() as db:
                        j = await db.get(ParseJob, job.job_id)
                        if j is not None:
                            j.status = ParseJobStatus.FAILED
                            j.error = "Orphan recovery: worker restarted"
                logger.warning(
                    "worker.on_startup: marked orphan job=%s as FAILED (no pool)",
                    job.job_id,
                )
    except Exception:
        logger.error("worker.on_startup: orphan recovery failed", exc_info=True)


async def on_job_abort(ctx: dict, job_id: str) -> None:
    """DLQ handler: called by arq when max_tries is exhausted.

    # @MX:NOTE: [AUTO] DLQ path — terminal FAILED state after max_tries=3 (AC-004).
    #           ParseJob.status is set to FAILED and error is recorded.
    #           This is the only path that creates a terminal FAILED without re-enqueue.

    AC-004: Jobs exceeding max_tries=3 reach terminal failed state.
    """
    from app.database import async_session
    from app.db.tenant_context import bypass_tenant_context
    from app.models.parse_job import ParseJob, ParseJobStatus

    logger.error("worker.on_job_abort: job=%s exhausted max_tries — marking FAILED", job_id)

    try:
        async with bypass_tenant_context():
            async with async_session() as db:
                job = await db.get(ParseJob, job_id)
                if job is not None:
                    job.status = ParseJobStatus.FAILED
                    job.error = f"Job aborted after {WorkerSettings.max_tries} attempts (DLQ)"
    except Exception:
        logger.error(
            "worker.on_job_abort: failed to mark job=%s as FAILED", job_id, exc_info=True
        )


async def health_check(ctx: dict) -> None:
    """Emit Redis heartbeat key to signal worker liveness (AC-008)."""
    redis = ctx.get("redis")
    if redis is None:
        return
    try:
        await redis.set(HEARTBEAT_KEY, "1", ex=HEARTBEAT_TTL_SECONDS)
    except Exception:
        logger.warning("worker.health_check: failed to write heartbeat key", exc_info=True)


def _get_redis_settings() -> RedisSettings:
    """Lazy-load RedisSettings to avoid Settings() import-time evaluation in tests."""
    from app.config import Settings
    return RedisSettings.from_dsn(Settings().redis_url)


class WorkerSettings:
    """arq WorkerSettings for the parse job worker.

    AC-003: max_tries=3 with arq's built-in exponential backoff.
    AC-005: Runs as a separate process — not inside FastAPI.
    """

    functions = [run_parse_job]
    redis_settings = RedisSettings.from_dsn("redis://localhost:6379")  # overridden at runtime
    max_tries = 3
    keep_result = 3600  # retain job results in Redis for 1 hour

    on_startup = staticmethod(on_startup)
    on_job_abort = staticmethod(on_job_abort)
    health_check = staticmethod(health_check)
    health_check_interval = 30  # seconds
