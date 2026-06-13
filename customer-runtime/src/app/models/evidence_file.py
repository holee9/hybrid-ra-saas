"""EvidenceFile ORM model — SPEC-EVIDENCE-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceFile(Base):
    """File artifact attached to an evidence binder."""

    __tablename__ = "evidence_files"

    file_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    binder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_binders.binder_id"), nullable=False, index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_ref: Mapped[str] = mapped_column(String(512), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    uploaded_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")

    # Relationships
    binder: Mapped["EvidenceBinder"] = relationship(  # noqa: F821
        "EvidenceBinder", back_populates="files"
    )
