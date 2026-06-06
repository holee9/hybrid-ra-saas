"""AuditEvent model — append-only."""
from datetime import datetime

from sqlalchemy import String, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_id


class AuditEvent(Base):
    """Append-only audit log. UPDATE and DELETE are forbidden at the ORM level."""
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    before_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


@event.listens_for(AuditEvent, "before_update")
def _block_update(mapper, connection, target):  # noqa: ARG001
    raise RuntimeError("AuditEvent is append-only")


@event.listens_for(AuditEvent, "before_delete")
def _block_delete(mapper, connection, target):  # noqa: ARG001
    raise RuntimeError("AuditEvent is append-only")
