"""Finding model."""
from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Finding(Base, TenantMixin, TimestampMixin):
    __tablename__ = "findings"

    finding_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.product_id"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_links: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewer_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="findings")  # noqa: F821
