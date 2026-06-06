"""Background job: parse a document and update status."""
import logging


from app.core.state_machine import validate_transition
from app.database import async_session
from app.models.document import Document, DocumentStatus
from app.models.parse_job import ParseJob, ParseJobStatus
from app.services.parser import ParserService, StubParserService, ParseResult

logger = logging.getLogger(__name__)

# Confidence threshold: above this -> ready_for_check, below -> needs_correction
CONFIDENCE_THRESHOLD = 0.8


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

        except Exception as exc:
            logger.exception("Parse job %s failed", job_id)
            job.status = ParseJobStatus.FAILED
            job.error = str(exc)
