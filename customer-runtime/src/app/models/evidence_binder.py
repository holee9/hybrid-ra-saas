"""EvidenceBinder ORM model — SPEC-EVIDENCE-001."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceBinder(Base, TimestampMixin):
    """Top-level evidence container tied to a product profile."""

    __tablename__ = "evidence_binders"

    binder_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    product_profile_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    pack_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    created_by: Mapped[str] = mapped_column(String(128), nullable=False, default="system")
    sealed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Relationships
    links: Mapped[list["EvidenceLink"]] = relationship(  # noqa: F821
        "EvidenceLink",
        back_populates="binder",
        cascade="all, delete-orphan",
    )
    files: Mapped[list["EvidenceFile"]] = relationship(  # noqa: F821
        "EvidenceFile",
        back_populates="binder",
        cascade="all, delete-orphan",
    )
    gaps: Mapped[list["EvidenceGap"]] = relationship(  # noqa: F821
        "EvidenceGap",
        back_populates="binder",
        cascade="all, delete-orphan",
    )
