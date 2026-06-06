"""POST /documents/upload endpoint."""
import hashlib

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.models.base import new_id
from app.models.document import Document, DocumentStatus
from app.models.parse_job import ParseJob, ParseJobStatus
from app.schemas.document import UploadResponse
from app.services.storage import StorageService

ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
}
ALLOWED_EXTENSIONS = {".docx", ".xlsx"}

router = APIRouter(prefix="/documents", tags=["documents"])


def _get_storage() -> StorageService:
    """Lazy import to allow test injection."""
    from app.services.storage import create_storage_service
    return create_storage_service()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    tenant: str = Depends(get_current_tenant),
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
