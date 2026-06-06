"""Control model."""
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Control(Base, TenantMixin, TimestampMixin):
    __tablename__ = "controls"

    control_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    control_type: Mapped[str] = mapped_column(String(100), nullable=False)
    linked_srs: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_ifu_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("evidences.evidence_id"), nullable=True
    )

    # Relationships
    verification: Mapped["Evidence | None"] = relationship()  # noqa: F821
    risks: Mapped[list["Risk"]] = relationship(back_populates="control")  # noqa: F821
