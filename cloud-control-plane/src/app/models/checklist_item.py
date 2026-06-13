"""ChecklistItem ORM model — per-section compliance checklist entry."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

VALID_STATUSES = frozenset({
    "not_started",
    "drafted",
    "evidence_attached",
    "needs_review",
    "approved",
    "not_applicable",
    "blocked",
})


class ChecklistItem(Base):
    """One checklist item per TemplateSection per product/pack review cycle."""

    __tablename__ = "checklist_items"

    checklist_item_id: Mapped[str] = mapped_column(
        String(48), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    section_id: Mapped[str] = mapped_column(
        String(48), ForeignKey("template_sections.section_id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="not_started")
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewer_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
