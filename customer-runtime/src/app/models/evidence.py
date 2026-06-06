"""Evidence model."""
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class Evidence(Base, TenantMixin, TimestampMixin):
    __tablename__ = "evidences"

    evidence_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    test_report_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    result_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
