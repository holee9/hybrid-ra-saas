"""Background job: parse a document and update status."""
import logging

import httpx

from app.core.state_machine import validate_transition
from app.database import async_session
from app.models.document import Document, DocumentStatus
from app.models.parse_job import ParseJob, ParseJobStatus
from app.services.parser import ParserService, StubParserService, ParseResult

logger = logging.getLogger(__name__)

# Confidence threshold: above this -> ready_for_check, below -> needs_correction
CONFIDENCE_THRESHOLD = 0.8


async def _push_ifu_result_to_regula(
    job_id: str,
    doc_id: str,
    tenant: str,
    doc_type: str,
    result: ParseResult,
) -> None:
    """Push IFU parse result to Regula (ra-med-bot) webhook URL.

    # @MX:ANCHOR: [AUTO] Outbound IFU parse result push to Regula SaaS (GAP-07).
    # @MX:REASON: External integration boundary; fire-and-forget — failure does not affect job status.

    Fire-and-forget: logs on failure, never raises.
    """
    from app.config import Settings
    settings = Settings()
    webhook_url = settings.regula_ifu_webhook_url
    if not webhook_url:
        return

    headers: dict[str, str] = {}
    if settings.regula_api_key:
        headers["X-Regula-API-Key"] = settings.regula_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                json={
                    "tenant_id": tenant,
                    "job_id": job_id,
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "confidence": result.confidence,
                    "field_candidates": result.field_candidates,
                    "required_missing": result.required_missing,
                },
                headers=headers,
            )
            resp.raise_for_status()
            logger.info("IFU push OK: job=%s status=%s", job_id, resp.status_code)
    except Exception:
        logger.warning("IFU push failed for job=%s (non-fatal)", job_id, exc_info=True)


async def run_parse_job(
    job_id: str,
    doc_id: str,
    tenant: str,
    parser: ParserService | None = None,
    file_bytes: bytes = b"",
) -> None:
    """Execute a parse job: fetch doc, parse, update status."""
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
            if parser is None:
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

            # Push IFU result to Regula on successful parse (GAP-07, fire-and-forget)
            await _push_ifu_result_to_regula(
                job_id=job_id,
                doc_id=doc_id,
                tenant=tenant,
                doc_type=doc.doc_type,
                result=result,
            )

        except Exception as exc:
            logger.exception("Parse job %s failed", job_id)
            job.status = ParseJobStatus.FAILED
            job.error = str(exc)
