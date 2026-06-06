"""Risk model."""
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Risk(Base, TenantMixin, TimestampMixin):
    __tablename__ = "risks"

    risk_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.product_id"), nullable=False
    )
    hazard: Mapped[str] = mapped_column(Text, nullable=False)
    hazardous_situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    harm: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    control_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("controls.control_id"), nullable=True
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="risks")  # noqa: F821
    control: Mapped["Control | None"] = relationship(back_populates="risks")  # noqa: F821
