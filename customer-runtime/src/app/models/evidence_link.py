"""EvidenceLink ORM model — SPEC-EVIDENCE-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceLink(Base):
    """Directed link from a source entity to a target reference."""

    __tablename__ = "evidence_links"

    link_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    binder_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("evidence_binders.binder_id"), nullable=False, index=True
    )
    source_entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    target_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    link_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    # Relationships
    binder: Mapped["EvidenceBinder"] = relationship(  # noqa: F821
        "EvidenceBinder", back_populates="links"
    )
