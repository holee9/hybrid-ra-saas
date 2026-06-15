"""TraceabilityEdge ORM model — SPEC-TRACEABILITY-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TraceabilityEdge(Base):
    """Directed relationship between two TraceabilityNodes."""

    __tablename__ = "traceability_edges"

    edge_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traceability_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traceability_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # satisfies|mitigates|verifies|warns_about|references
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # 0.0~1.0 for LLM-derived, NULL for rules
    created_by: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # rule|llm|human
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
