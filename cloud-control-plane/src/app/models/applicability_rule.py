"""ApplicabilityRule ORM model — conditional section inclusion rules."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApplicabilityRule(Base):
    """Defines a condition that determines whether a TemplateSection applies to a product."""

    __tablename__ = "applicability_rules"

    rule_id: Mapped[str] = mapped_column(String(48), primary_key=True)
    condition_field: Mapped[str] = mapped_column(String(64), nullable=False)
    condition_value: Mapped[str] = mapped_column(String(255), nullable=False)
    template_pack_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("template_packs.pack_id"), nullable=False
    )
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
