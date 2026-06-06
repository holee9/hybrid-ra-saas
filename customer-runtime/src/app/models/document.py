"""Document model with status enum."""
import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    NEEDS_CORRECTION = "needs_correction"
    READY_FOR_CHECK = "ready_for_check"
    APPROVED = "approved"
    REJECTED = "rejected"


class Document(Base, TenantMixin, TimestampMixin):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("products.product_id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.UPLOADED
    )

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="documents")  # noqa: F821
    parse_jobs: Mapped[list["ParseJob"]] = relationship(back_populates="document")  # noqa: F821
