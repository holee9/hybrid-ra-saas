"""ChecklistExport ORM model — SPEC-CHECKLIST-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChecklistExport(Base):
    """Records an export artifact generated from a checklist snapshot."""

    __tablename__ = "checklist_exports"

    export_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("checklist_snapshots.snapshot_id"), nullable=False, index=True
    )
    format: Mapped[str] = mapped_column(String(8), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now)
    file_ref: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relationship
    snapshot: Mapped["ChecklistSnapshot"] = relationship(  # noqa: F821
        "ChecklistSnapshot", back_populates="exports"
    )
