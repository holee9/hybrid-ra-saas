"""GapFinding ORM model — SPEC-CHECKLIST-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapFinding(Base):
    """Represents a compliance gap found during checklist evaluation."""

    __tablename__ = "gap_findings"

    gap_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("checklist_snapshots.snapshot_id"), nullable=False, index=True
    )
    section_id: Mapped[str] = mapped_column(String(48), nullable=False)
    gap_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationship
    snapshot: Mapped["ChecklistSnapshot"] = relationship(  # noqa: F821
        "ChecklistSnapshot", back_populates="gaps"
    )
