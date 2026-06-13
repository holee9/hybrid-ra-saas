"""ImpactAnalysis ORM model — SPEC-TRACEABILITY-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ImpactAnalysis(Base):
    """Records the downstream impact of a node change."""

    __tablename__ = "impact_analyses"

    analysis_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trigger_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traceability_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    # [{node_id: str, reason: str}, ...] — JSON for SQLite compatibility
    affected_nodes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
