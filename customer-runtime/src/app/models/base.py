"""SQLAlchemy declarative base and shared mixins."""
import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Project-wide declarative base."""


class TenantMixin:
    """Adds tenant_id column with index.

    # @MX:ANCHOR: [AUTO] Marker mixin — all subclasses are subject to automatic tenant filtering.
    # @MX:REASON: do_orm_execute listener uses isinstance(TenantMixin) to determine filter applicability.
    """
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


def is_tenant_scoped(model_class) -> bool:
    """Return True if model_class inherits TenantMixin (tenant-isolated)."""
    return issubclass(model_class, TenantMixin)


class TimestampMixin:
    """Adds created_at and updated_at columns."""
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
