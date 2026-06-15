"""TemplatePack ORM model — versioned regulatory template package."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TemplatePack(TimestampMixin, Base):
    """A versioned set of template documents for a specific regulatory pathway + device family."""

    __tablename__ = "template_packs"

    pack_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    pathway_id: Mapped[str] = mapped_column(
        String(48), ForeignKey("regulatory_pathways.pathway_id"), nullable=False
    )
    device_family: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    source_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
