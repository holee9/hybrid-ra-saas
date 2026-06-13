"""TemplateDocument ORM model — document-level metadata within a TemplatePack."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TemplateDocument(Base):
    """A single document entry within a TemplatePack (e.g., Design History File)."""

    __tablename__ = "template_documents"

    document_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    pack_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("template_packs.pack_id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    export_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
