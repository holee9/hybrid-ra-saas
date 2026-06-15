"""TemplateSection ORM model — granular section within a TemplateDocument."""

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TemplateSection(Base):
    """A section within a TemplateDocument with optional applicability rule."""

    __tablename__ = "template_sections"

    section_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(48), ForeignKey("template_documents.document_id"), nullable=False
    )
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    placeholder: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference_ids: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    applicability_rule_id: Mapped[str | None] = mapped_column(
        String(48), ForeignKey("applicability_rules.rule_id"), nullable=True
    )
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
