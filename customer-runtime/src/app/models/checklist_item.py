"""ChecklistItem ORM model — SPEC-CHECKLIST-001."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChecklistItem(Base, TimestampMixin):
    """Per-section checklist item within a snapshot."""

    __tablename__ = "checklist_items"

    checklist_item_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("checklist_snapshots.snapshot_id"), nullable=False, index=True
    )
    section_id: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_satisfied: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    waiver_justification: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    snapshot: Mapped["ChecklistSnapshot"] = relationship(  # noqa: F821
        "ChecklistSnapshot", back_populates="items"
    )
