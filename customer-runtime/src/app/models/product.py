"""Product model."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Product(Base, TenantMixin, TimestampMixin):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="product")  # noqa: F821
    risks: Mapped[list["Risk"]] = relationship(back_populates="product")  # noqa: F821
    findings: Mapped[list["Finding"]] = relationship(back_populates="product")  # noqa: F821
