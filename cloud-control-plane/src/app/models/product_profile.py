"""ProductProfile ORM model — device/product metadata for pathway resolution."""

import uuid

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ProductProfile(TimestampMixin, Base):
    """Represents a single medical device product registered by a tenant."""

    __tablename__ = "product_profiles"

    product_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    classification: Mapped[str | None] = mapped_column(String(32), nullable=True)
    intended_use: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_market: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    technology_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device_family: Mapped[str | None] = mapped_column(String(64), nullable=True)
    software_in_device: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
