"""RegulatoryPathway ORM model — static reference data for market/authority combos."""

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RegulatoryPathway(Base):
    """Static reference data — no timestamps, seeded at deploy time."""

    __tablename__ = "regulatory_pathways"

    pathway_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    submission_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    device_class: Mapped[str | None] = mapped_column(String(16), nullable=True)
    applicable_standards: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
