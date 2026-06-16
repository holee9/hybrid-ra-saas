"""
SQLAlchemy ORM event listeners for automatic tenant isolation.

Registers do_orm_execute and before_flush listeners that inject tenant_id
filters on all reads and enforce tenant ownership on all writes.

Security gates: REQ-TI-002 (read isolation), REQ-TI-004 (auto-set on insert),
REQ-TI-005 (reject cross-tenant writes).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.db.tenant_context import (
    TenantContextError,
    get_tenant_context,
    is_bypass_active,
)
from app.models.base import TenantMixin

# @MX:ANCHOR: [AUTO] ORM event listener for automatic tenant filter injection.
# @MX:REASON: Core security gate for REQ-TI-002/REQ-TI-004/REQ-TI-005; all DB reads/writes pass through this.

_security_log = logging.getLogger("security")


class TenantWriteViolation(ValueError):
    """Raised when a flush attempts to write a TenantMixin row whose tenant_id
    does not match the active tenant context (tenant spoofing attempt)."""


# @MX:WARN: [AUTO] Tenant bypass path — ensure only admin deps can activate.
# @MX:REASON: bypass_tenant_context is a security-sensitive escape hatch.


def register_tenant_filter(session_factory: Any) -> None:
    """Register ORM event listeners on *session_factory* to enforce tenant isolation.

    Attaches two listeners:

    * ``do_orm_execute`` — injects a ``with_loader_criteria`` option on every
      SELECT so that only rows belonging to the active tenant are returned.
    * ``before_flush`` — validates/auto-sets ``tenant_id`` on new and dirty
      TenantMixin instances before they are flushed to the database.

    Args:
        session_factory: A SQLAlchemy ``sessionmaker`` or ``async_sessionmaker``
            whose sessions should be tenant-filtered.
    """

    @event.listens_for(Session, "do_orm_execute")
    def _do_orm_execute(execute_state: Any) -> None:
        """Inject tenant filter on every ORM SELECT statement.

        Skips filtering when admin bypass is active. Raises TenantContextError
        when no tenant context has been established (defensive guard).
        """
        if is_bypass_active():
            return

        tenant_id = get_tenant_context()
        if tenant_id is None:
            raise TenantContextError(
                "No tenant context set. Use set_tenant_context() or a middleware that "
                "establishes the context before executing ORM queries."
            )

        if not execute_state.is_column_load:
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    TenantMixin,
                    lambda cls: cls.tenant_id == tenant_id,
                    include_aliases=True,
                )
            )

    @event.listens_for(Session, "before_flush")
    def _before_flush(session: Session, flush_context: Any, instances: Any) -> None:
        """Validate and auto-set tenant_id on all TenantMixin rows before flush.

        For new instances (INSERT): sets tenant_id if not already set (REQ-TI-004).
        For dirty instances (UPDATE): rejects any attempt to write a tenant_id
        that differs from the active context (REQ-TI-005 — spoofing prevention).

        Bypass mode skips all validation.
        """
        if is_bypass_active():
            return

        tenant_id = get_tenant_context()
        if tenant_id is None:
            raise TenantContextError(
                "No tenant context set during flush. All write operations require "
                "an active tenant context."
            )

        for instance in list(session.new) + list(session.dirty):
            if not isinstance(instance, TenantMixin):
                continue

            if not instance.tenant_id:
                # Auto-assign tenant_id on INSERT (REQ-TI-004)
                instance.tenant_id = tenant_id
            elif instance.tenant_id != tenant_id:
                # Cross-tenant write attempt — log as security event and abort
                _security_log.warning(
                    "Tenant spoofing attempt: instance %r has tenant_id=%r but "
                    "active context is tenant_id=%r",
                    instance,
                    instance.tenant_id,
                    tenant_id,
                )
                raise TenantWriteViolation(
                    f"Cannot write tenant {instance.tenant_id!r} in context {tenant_id!r}"
                )
