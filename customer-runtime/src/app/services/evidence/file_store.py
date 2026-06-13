"""File upload and integrity service — SPEC-EVIDENCE-001."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_file import EvidenceFile

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/csv",
    "image/png",
    "image/jpeg",
}

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


class FileValidationError(ValueError):
    """Raised when a file fails content-type or size validation."""


async def store_evidence_file(
    binder_id: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    db: AsyncSession,
) -> EvidenceFile:
    """Validate, hash, and persist an evidence file record.

    Raises:
        FileValidationError: if content_type is not allowed or file exceeds 50 MB.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise FileValidationError(
            f"Content type '{content_type}' is not allowed. "
            f"Allowed types: {sorted(ALLOWED_CONTENT_TYPES)}."
        )
    if len(file_bytes) > MAX_SIZE_BYTES:
        raise FileValidationError(
            f"File size {len(file_bytes)} bytes exceeds maximum of {MAX_SIZE_BYTES} bytes (50 MB)."
        )

    sha256 = hashlib.sha256(file_bytes).hexdigest()
    storage_ref = f"local/evidence/{binder_id}/{uuid.uuid4()}/{filename}"

    evidence_file = EvidenceFile(
        file_id=str(uuid.uuid4()),
        binder_id=binder_id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(file_bytes),
        storage_ref=storage_ref,
        sha256=sha256,
        uploaded_at=datetime.now(timezone.utc),
        uploaded_by="system",
    )
    db.add(evidence_file)
    await db.flush()
    await db.refresh(evidence_file)
    return evidence_file
