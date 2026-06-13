"""ChecklistSnapshot ORM model — SPEC-CHECKLIST-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChecklistSnapshot(Base, TimestampMixin):
    """Represents a point-in-time checklist for a pack+session combo."""

    __tablename__ = "checklist_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    pack_id: Mapped[str] = mapped_column(String(48), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now)
    total_items: Mapped[int] = mapped_column(nullable=False, default=0)
    complete_items: Mapped[int] = mapped_column(nullable=False, default=0)
    blocking_gaps_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")

    # Relationships
    items: Mapped[list["ChecklistItem"]] = relationship(  # noqa: F821
        "ChecklistItem",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
    gaps: Mapped[list["GapFinding"]] = relationship(  # noqa: F821
        "GapFinding",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
    exports: Mapped[list["ChecklistExport"]] = relationship(  # noqa: F821
        "ChecklistExport",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )
