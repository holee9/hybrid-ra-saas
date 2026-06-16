"""
Tenant context propagation via ContextVar.

Provides request-scoped tenant isolation for all ORM operations.
All filter listeners read this module as the single source of truth (REQ-TI-001).
"""

from __future__ import annotations

from contextvars import ContextVar, Token

# @MX:ANCHOR: [AUTO] Single ContextVar for request-scoped tenant propagation.
# @MX:REASON: All ORM filter listeners read this; must be the single source of truth per REQ-TI-001.

BYPASS_SENTINEL = "__bypass__"
"""Sentinel value that activates admin bypass mode — skips all tenant filters."""

_current_tenant: ContextVar[str | None] = ContextVar("current_tenant", default=None)


class TenantContextError(Exception):
    """Raised when a tenant-scoped ORM operation is attempted without an active tenant context."""


def set_tenant_context(tenant_id: str) -> Token:
    """Set the current tenant context for this async task.

    Args:
        tenant_id: The tenant identifier to activate. Use BYPASS_SENTINEL for admin bypass.

    Returns:
        A reset token that can be passed to clear_tenant_context to restore the previous value.
    """
    return _current_tenant.set(tenant_id)


def get_tenant_context() -> str | None:
    """Return the active tenant_id or BYPASS_SENTINEL, or None if no context is set.

    Returns:
        The current tenant_id string, BYPASS_SENTINEL if bypass is active, or None.
    """
    return _current_tenant.get()


def clear_tenant_context(token: Token) -> None:
    """Reset the tenant context to its previous value using the token from set_tenant_context.

    Args:
        token: The Token returned by a prior set_tenant_context call.
    """
    _current_tenant.reset(token)


def is_bypass_active() -> bool:
    """Return True if the admin bypass sentinel is currently active.

    Returns:
        True if bypass mode is active (BYPASS_SENTINEL is the current context value).
    """
    return _current_tenant.get() == BYPASS_SENTINEL


class bypass_tenant_context:
    """Async context manager that activates admin bypass mode for the duration of the block.

    Usage::

        async with bypass_tenant_context():
            # All ORM operations skip tenant filters here
            result = await session.execute(select(AnyModel))
    """

    def __init__(self) -> None:
        self._token: Token | None = None

    async def __aenter__(self) -> "bypass_tenant_context":
        """Activate bypass sentinel."""
        self._token = set_tenant_context(BYPASS_SENTINEL)
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Restore previous tenant context."""
        if self._token is not None:
            clear_tenant_context(self._token)
            self._token = None


class explicit_tenant_context:
    """Async context manager for background tasks that need to specify tenant_id explicitly.

    Implements REQ-TI-010: background tasks must explicitly set tenant context since
    they do not participate in the request/response middleware lifecycle.

    Usage::

        async with explicit_tenant_context(tenant_id="acme-corp"):
            await process_tenant_job(session)
    """

    def __init__(self, tenant_id: str) -> None:
        """
        Args:
            tenant_id: The tenant identifier to activate for this block.
        """
        self._tenant_id = tenant_id
        self._token: Token | None = None

    async def __aenter__(self) -> "explicit_tenant_context":
        """Activate the specified tenant context."""
        self._token = set_tenant_context(self._tenant_id)
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Restore previous tenant context."""
        if self._token is not None:
            clear_tenant_context(self._token)
            self._token = None
