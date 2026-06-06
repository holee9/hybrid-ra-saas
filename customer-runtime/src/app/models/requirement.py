"""Requirement model with pgvector embedding column."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from pgvector.sqlalchemy import Vector

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Requirement(Base, TenantMixin, TimestampMixin):
    __tablename__ = "requirements"

    req_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clause_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    product_family: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
