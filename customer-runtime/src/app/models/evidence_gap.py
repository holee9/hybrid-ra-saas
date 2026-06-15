"""EvidenceGap ORM model — SPEC-EVIDENCE-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceGap(Base):
    """Auto-surfaced gap in evidence coverage."""

    __tablename__ = "evidence_gaps"

    gap_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    binder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_binders.binder_id"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    surfaced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    binder: Mapped["EvidenceBinder"] = relationship(  # noqa: F821
        "EvidenceBinder", back_populates="gaps"
    )
