"""ParseJob model — tracks background parsing tasks."""
import enum

from sqlalchemy import Enum, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class ParseJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ParseJob(Base, TenantMixin, TimestampMixin):
    __tablename__ = "parse_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.doc_id"), nullable=False
    )
    status: Mapped[ParseJobStatus] = mapped_column(
        Enum(ParseJobStatus), nullable=False, default=ParseJobStatus.PENDING
    )
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="parse_jobs")  # noqa: F821
