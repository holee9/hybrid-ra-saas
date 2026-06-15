"""SourceReference ORM model — regulatory document/article references."""

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SourceReference(Base):
    """Static reference data linking to official regulatory documents."""

    __tablename__ = "source_references"

    ref_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    regulation_name: Mapped[str] = mapped_column(String(255), nullable=False)
    article: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    effective_date: Mapped[str | None] = mapped_column(Date, nullable=True)
