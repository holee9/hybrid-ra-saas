"""TraceabilityNode ORM model — SPEC-TRACEABILITY-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TraceabilityNode(Base):
    """Represents a traceable element extracted from a regulatory document."""

    __tablename__ = "traceability_nodes"

    node_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    section_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    node_type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # requirement|risk_control|test|ifu_warning|hazard
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 of content for change detection
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
