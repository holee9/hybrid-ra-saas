"""Background job: parse a document and update status.

Migrated to arq (SPEC-JOBQUEUE-001): ctx is always the first arg.
ParserService removed from signature — not Redis-serializable.
"""
from __future__ import annotations

import logging

import httpx

from app.core.state_machine import validate_transition
from app.database import async_session
from app.db.tenant_context import explicit_tenant_context
from app.models.document import Document, DocumentStatus
from app.models.parse_job import ParseJob, ParseJobStatus
from app.services.parser import ParseResult, StubParserService

logger = logging.getLogger(__name__)

# Confidence threshold: above this -> ready_for_check, below -> needs_correction
CONFIDENCE_THRESHOLD = 0.8


async def _post_to_regula(
    url: str,
    payload: dict,
    job_id: str,
    label: str,
    *,
    api_key: str = "",
) -> None:
    """Generic fire-and-forget POST to a Regula SaaS endpoint. Never raises."""
    if not url:
        return
    headers: dict[str, str] = {}
    if api_key:
        headers["X-Regula-API-Key"] = api_key
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("%s push OK: job=%s status=%s", label, job_id, resp.status_code)
    except Exception:
        logger.warning("%s push failed for job=%s (non-fatal)", label, job_id, exc_info=True)


# @MX:ANCHOR: [AUTO] Outbound IFU parse result push to Regula SaaS (GAP-07).
# @MX:REASON: External integration boundary; fire-and-forget — failure does not affect job status.
async def _push_ifu_result_to_regula(
    job_id: str,
    doc_id: str,
    tenant: str,
    doc_type: str,
    result: ParseResult,
) -> None:
    """Push IFU parse result to Regula (ra-med-bot) webhook URL. Fire-and-forget."""
    from app.config import Settings
    settings = Settings()
    await _post_to_regula(
        url=settings.regula_ifu_webhook_url,
        payload={
            "tenant_id": tenant,
            "job_id": job_id,
            "doc_id": doc_id,
            "doc_type": doc_type,
            "confidence": result.confidence,
            "field_candidates": result.field_candidates,
            "required_missing": result.required_missing,
        },
        job_id=job_id,
        label="IFU",
        api_key=settings.regula_api_key,
    )


# @MX:ANCHOR: [AUTO] Outbound knowledge sync trigger to Regula SaaS (GAP-08).
# @MX:REASON: External integration boundary; fire-and-forget — failure does not affect job status.
async def _push_knowledge_sync_to_regula(
    job_id: str,
    tenant: str,
) -> None:
    """Notify Regula (ra-med-bot) to re-sync the knowledge base. Fire-and-forget."""
    from app.config import Settings
    settings = Settings()
    await _post_to_regula(
        url=settings.regula_knowledge_push_url,
        payload={"tenant_id": tenant, "trigger": "parse_completed", "job_id": job_id},
        job_id=job_id,
        label="knowledge-sync",
        api_key=settings.regula_api_key,
    )


async def run_parse_job(
    ctx: dict,
    job_id: str,
    doc_id: str,
    tenant: str,
    *,
    file_bytes: bytes = b"",
) -> None:
    """Execute a parse job: fetch doc, parse, update status.

    # @MX:ANCHOR: [AUTO] arq task entry point — enqueued by POST /documents/upload
    # @MX:REASON: fan_in >= 3: upload endpoint, worker, orphan recovery on_startup

    Args:
        ctx: arq worker context (MUST be first arg for arq tasks).
        job_id: ParseJob primary key.
        doc_id: Document primary key.
        tenant: Tenant identifier — used to set explicit tenant context (REQ-JQ-005).
        file_bytes: Raw file content to parse (keyword-only, default empty).
    """
    # REQ-JQ-005: background tasks must set explicit tenant context
    async with explicit_tenant_context(tenant):
        knowledge_sync_requested = False
        async with async_session() as db:
            job = await db.get(ParseJob, job_id)
            doc = await db.get(Document, doc_id)

            if job is None or doc is None:
                logger.error("Job %s or Document %s not found", job_id, doc_id)
                return

            # Transition job: pending -> running
            job.status = ParseJobStatus.RUNNING
            await db.flush()

            # Transition document: uploaded -> parsing
            try:
                validate_transition(doc.status, DocumentStatus.PARSING)
                doc.status = DocumentStatus.PARSING
                await db.flush()
            except ValueError as e:
                logger.error("State machine error: %s", e)
                job.status = ParseJobStatus.FAILED
                job.error = str(e)
                return

            try:
                default_result = ParseResult(
                    confidence=0.9, field_candidates={}, required_missing=[]
                )
                parser = StubParserService(default_result)
                result = await parser.parse(file_bytes, doc.doc_type)

                # Determine next document status based on confidence
                if result.confidence >= CONFIDENCE_THRESHOLD:
                    next_status = DocumentStatus.READY_FOR_CHECK
                else:
                    next_status = DocumentStatus.NEEDS_CORRECTION

                validate_transition(doc.status, next_status)
                doc.status = next_status

                # Store result in job
                job.result_json = {
                    "confidence": result.confidence,
                    "field_candidates": result.field_candidates,
                    "required_missing": result.required_missing,
                }
                job.status = ParseJobStatus.DONE

                # Push IFU result to Regula on successful parse (GAP-07, AC-009, fire-and-forget)
                await _push_ifu_result_to_regula(
                    job_id=job_id,
                    doc_id=doc_id,
                    tenant=tenant,
                    doc_type=doc.doc_type,
                    result=result,
                )

                knowledge_sync_requested = True

            except Exception as exc:
                logger.exception("Parse job %s failed", job_id)
                job.status = ParseJobStatus.FAILED
                job.error = str(exc)

        # Notify Regula after the parse result transaction commits (GAP-08, fire-and-forget).
        if knowledge_sync_requested:
            await _push_knowledge_sync_to_regula(job_id=job_id, tenant=tenant)
