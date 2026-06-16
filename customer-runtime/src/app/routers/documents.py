"""Document endpoints: POST /documents/upload, PATCH /documents/{doc_id}/fields."""
import hashlib
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_hybrid_bearer_token
from app.deps import get_current_tenant, get_db
from app.models.base import new_id
from app.models.document import Document, DocumentStatus
from app.models.parse_job import ParseJob, ParseJobStatus
from app.schemas.document import UploadResponse
from app.services.audit import AuditService
from app.services.storage import StorageService

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
}
ALLOWED_EXTENSIONS = {".docx", ".xlsx"}

_audit_service = AuditService()


# ---------------------------------------------------------------------------
# Schema models for field correction
# ---------------------------------------------------------------------------


class FieldCorrection(BaseModel):
    field_name: str
    before_value: str
    after_value: str


class FieldCorrectionRequest(BaseModel):
    field_corrections: list[FieldCorrection]
    user_id: str


class FieldCorrectionResponse(BaseModel):
    doc_id: str
    corrections_applied: int
    audit_event_id: str


# ---------------------------------------------------------------------------
# Helper functions (importable for unit tests)
# ---------------------------------------------------------------------------


def compute_correction_hashes(
    corrections: list[dict[str, Any]],
) -> tuple[str, str]:
    """Compute SHA-256 hashes for before and after correction values.

    # @MX:ANCHOR: [AUTO] Called by apply_field_correction and test_field_correction
    # @MX:REASON: stable hash contract must not change without migration
    """
    before_values = sorted(c["before_value"] for c in corrections)
    after_values = sorted(c["after_value"] for c in corrections)
    before_hash = hashlib.sha256(
        json.dumps(before_values, sort_keys=True).encode("utf-8")
    ).hexdigest()
    after_hash = hashlib.sha256(
        json.dumps(after_values, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return before_hash, after_hash


async def _get_document_or_404(
    db: AsyncSession,
    doc_id: str,
    tenant_id: str,
) -> Document:
    """Fetch Document by id and tenant, raise 404 if not found."""
    result = await db.execute(
        select(Document).where(
            Document.doc_id == doc_id,
            Document.tenant_id == tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Document {doc_id!r} not found")
    return doc


async def apply_field_correction(
    db: AsyncSession,
    doc_id: str,
    tenant_id: str,
    user_id: str,
    field_corrections: list[dict[str, Any]],
    audit_service: Any,
) -> dict[str, Any]:
    """Apply field corrections: hash before/after, record AuditEvent, transition status.

    # @MX:ANCHOR: [AUTO] apply_field_correction — called by PATCH endpoint and test suite
    # @MX:REASON: fan_in >= 3 (endpoint, test, future batch processor)
    """
    doc = await _get_document_or_404(db=db, doc_id=doc_id, tenant_id=tenant_id)

    before_hash, after_hash = compute_correction_hashes(field_corrections)

    # Record AuditEvent with before/after hashes
    event = await audit_service.record(
        db=db,
        tenant_id=tenant_id,
        user_id=user_id,
        action="document.field_correction",
        before_hash=before_hash,
        after_hash=after_hash,
    )

    # Status transition: needs_correction -> ready_for_check if all after_values non-empty
    all_after_non_empty = all(c["after_value"].strip() for c in field_corrections)
    if doc.status == "needs_correction" and all_after_non_empty:
        doc.status = "ready_for_check"  # type: ignore[assignment]

    await db.flush()

    return {
        "doc_id": doc_id,
        "corrections_applied": len(field_corrections),
        "audit_event_id": event.event_id,
    }

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_storage() -> StorageService:
    """Lazy import to allow test injection."""
    from app.services.storage import create_storage_service
    return create_storage_service()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    tenant: str = Depends(verify_hybrid_bearer_token),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(_get_storage),
):
    """Accept DOCX/XLSX, compute SHA-256, upload to MinIO, enqueue parse job."""
    # Validate extension
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Only DOCX and XLSX are accepted.",
        )

    file_bytes = await file.read()

    # SHA-256 hash
    source_file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Upload to storage
    doc_id = new_id()
    storage_key = storage.upload_file(tenant, f"{doc_id}{ext}", file_bytes)

    # Determine doc_type from extension
    doc_type = "srs" if ext == ".docx" else "test_report"

    # Infer a product_id — for upload we require X-Product-ID or use a placeholder
    # For MVP: product_id is passed as query param or defaults to "default"
    product_id = "default"

    # Create Document row
    doc = Document(
        doc_id=doc_id,
        tenant_id=tenant,
        product_id=product_id,
        doc_type=doc_type,
        source_file_hash=source_file_hash,
        storage_key=storage_key,
        status=DocumentStatus.UPLOADED,
    )
    db.add(doc)

    # Create ParseJob row
    job_id = new_id()
    parse_job = ParseJob(
        job_id=job_id,
        tenant_id=tenant,
        doc_id=doc_id,
        status=ParseJobStatus.PENDING,
    )
    db.add(parse_job)
    await db.flush()

    # Enqueue background task
    from app.jobs.parse_job import run_parse_job
    background_tasks.add_task(
        run_parse_job,
        job_id=job_id,
        doc_id=doc_id,
        tenant=tenant,
        file_bytes=file_bytes,
    )

    return UploadResponse(doc_id=doc_id, parse_job_id=job_id)


@router.patch("/{doc_id}/fields", response_model=FieldCorrectionResponse)
async def patch_document_fields(
    doc_id: str,
    payload: FieldCorrectionRequest,
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Apply operator field corrections with before/after audit trail.

    REQ-API-006: Records before/after values and operator/timestamp in AuditEvent.
    REQ-API-011: Appends AuditEvent with before_hash/after_hash.
    """
    result = await apply_field_correction(
        db=db,
        doc_id=doc_id,
        tenant_id=tenant,
        user_id=payload.user_id,
        field_corrections=[c.model_dump() for c in payload.field_corrections],
        audit_service=_audit_service,
    )
    return FieldCorrectionResponse(**result)
