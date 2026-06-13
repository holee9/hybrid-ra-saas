"""AuthoringSectionEntry ORM model — SPEC-AUTHORING-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthoringSectionEntry(Base):
    """Stores per-section content and AI draft for an AuthoringSession."""

    __tablename__ = "authoring_section_entries"

    entry_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("authoring_sessions.session_id"), nullable=False, index=True
    )
    section_id: Mapped[str] = mapped_column(String(48), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_draft_confidence: Mapped[float | None] = mapped_column(nullable=True)
    # JSON column for SQLite test compatibility (not ARRAY)
    ai_draft_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="empty")
    skip_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now, onupdate=_now)

    # Back-reference to session
    session: Mapped["AuthoringSession"] = relationship(  # noqa: F821
        "AuthoringSession", back_populates="entries"
    )
