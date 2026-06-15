"""ConsistencyFinding ORM model — SPEC-TRACEABILITY-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ConsistencyFinding(Base):
    """Records a consistency issue found during traceability analysis."""

    __tablename__ = "consistency_findings"

    finding_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    finding_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # missing_link|broken_link|semantic_mismatch|orphan_node
    severity: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # high|medium|low
    source_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traceability_nodes.node_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("traceability_nodes.node_id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open"
    )  # open|resolved|exception_approved
    justification: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # required for exception_approved
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
