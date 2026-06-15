"""AuthoringSession ORM model — SPEC-AUTHORING-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthoringSession(Base):
    """Represents a single authoring workspace for a pack+product combo."""

    __tablename__ = "authoring_sessions"

    session_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_profile_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pack_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=_now, onupdate=_now)

    # Relationship to section entries
    entries: Mapped[list["AuthoringSectionEntry"]] = relationship(  # noqa: F821
        "AuthoringSectionEntry",
        back_populates="session",
        cascade="all, delete-orphan",
    )
