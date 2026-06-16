"""Unit tests for tenant isolation: ContextVar propagation and ORM listener logic.

All tests are self-contained with mocks — no real database connection required.
Tests cover:
  - REQ-TI-001: ContextVar set/get/clear
  - REQ-TI-002: bypass context manager
  - REQ-TI-004: auto-set tenant_id on INSERT
  - REQ-TI-005: cross-tenant write rejection (spoofing prevention)
  - REQ-TI-010: explicit_tenant_context for background tasks
"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is on the path (mirrors conftest.py pattern)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.db.tenant_context import (
    TenantContextError,
    bypass_tenant_context,
    clear_tenant_context,
    explicit_tenant_context,
    get_tenant_context,
    is_bypass_active,
    set_tenant_context,
)


# ---------------------------------------------------------------------------
# Helpers — extract the inner listener functions without mutating global state
# ---------------------------------------------------------------------------

def _make_listeners() -> tuple:
    """Call register_tenant_filter with a dummy factory and capture the two
    inner listener functions by intercepting sqlalchemy.event.listens_for.

    Returns (do_orm_execute_fn, before_flush_fn).
    """
    captured: list = []

    def fake_listens_for(target, identifier):
        def decorator(fn):
            captured.append((identifier, fn))
            return fn
        return decorator

    with patch("app.db.tenant_filter.event.listens_for", side_effect=fake_listens_for):
        from app.db import tenant_filter  # noqa: F401 — side-effect import triggers registration
        import importlib
        # Re-import to trigger register path with our patched event
        import app.db.tenant_filter as tf_mod
        importlib.reload(tf_mod)  # triggers module-level code (no register call here)

    # The listeners are defined inside register_tenant_filter; we need to call it.
    with patch("app.db.tenant_filter.event.listens_for", side_effect=fake_listens_for):
        tf_mod.register_tenant_filter(MagicMock())

    assert len(captured) == 2, f"Expected 2 listeners, got {len(captured)}: {captured}"
    # Order is do_orm_execute first, before_flush second (matches source order)
    listeners = {name: fn for name, fn in captured}
    return listeners["do_orm_execute"], listeners["before_flush"]


# Module-level: capture listener functions once for the whole test session.
# Uses patching so we never touch the real SQLAlchemy Session class.
_DO_ORM_EXECUTE, _BEFORE_FLUSH = _make_listeners()


# ---------------------------------------------------------------------------
# Test Group 1: ContextVar set / get / clear
# ---------------------------------------------------------------------------

class TestTenantContextVar:
    """Tests for set_tenant_context / get_tenant_context / clear_tenant_context."""

    def test_set_and_get_tenant_context(self) -> None:
        """set_tenant_context stores value; get_tenant_context retrieves it."""
        token = set_tenant_context("tenant-abc")
        try:
            assert get_tenant_context() == "tenant-abc"
        finally:
            clear_tenant_context(token)

    def test_clear_tenant_context(self) -> None:
        """clear_tenant_context restores previous value (None when not set before)."""
        token = set_tenant_context("tenant-xyz")
        clear_tenant_context(token)
        assert get_tenant_context() is None

    def test_is_bypass_active_false_by_default(self) -> None:
        """is_bypass_active() returns False when no context is set."""
        token = set_tenant_context("tenant-regular")
        try:
            assert is_bypass_active() is False
        finally:
            clear_tenant_context(token)

    async def test_bypass_context_manager_activates_sentinel(self) -> None:
        """async with bypass_tenant_context() sets BYPASS_SENTINEL."""
        async with bypass_tenant_context():
            assert is_bypass_active() is True

    async def test_bypass_context_manager_restores_after_exit(self) -> None:
        """is_bypass_active() returns False after exiting bypass_tenant_context."""
        async with bypass_tenant_context():
            pass
        assert is_bypass_active() is False


# ---------------------------------------------------------------------------
# Test Group 2: explicit_tenant_context (REQ-TI-010)
# ---------------------------------------------------------------------------

class TestExplicitTenantContext:
    """Tests for explicit_tenant_context — background task tenant propagation."""

    async def test_explicit_tenant_context_sets_tenant(self) -> None:
        """async with explicit_tenant_context sets the tenant_id during the block."""
        async with explicit_tenant_context("tenant-X"):
            assert get_tenant_context() == "tenant-X"

    async def test_explicit_tenant_context_restores_after_exit(self) -> None:
        """get_tenant_context() returns None after explicit_tenant_context exits."""
        async with explicit_tenant_context("tenant-X"):
            pass
        assert get_tenant_context() is None

    async def test_explicit_tenant_context_nesting(self) -> None:
        """Nested explicit contexts restore outer context on exit."""
        async with explicit_tenant_context("outer"):
            async with explicit_tenant_context("inner"):
                assert get_tenant_context() == "inner"
            assert get_tenant_context() == "outer"


# ---------------------------------------------------------------------------
# Test Group 3: do_orm_execute listener (tenant filter injection)
# ---------------------------------------------------------------------------

class TestDoOrmExecuteListener:
    """Tests for the _do_orm_execute listener captured from register_tenant_filter."""

    def _make_execute_state(self, *, is_column_load: bool = False) -> MagicMock:
        """Build a minimal mock execute_state for the listener."""
        state = MagicMock()
        state.is_column_load = is_column_load
        return state

    def test_no_context_raises_error(self) -> None:
        """Listener raises TenantContextError when no tenant context is set."""
        assert get_tenant_context() is None  # pre-condition
        execute_state = self._make_execute_state()
        with pytest.raises(TenantContextError):
            _DO_ORM_EXECUTE(execute_state)

    async def test_bypass_skips_filter(self) -> None:
        """Listener returns early (no filter) when bypass is active."""
        async with bypass_tenant_context():
            execute_state = self._make_execute_state()
            _DO_ORM_EXECUTE(execute_state)
            # with_loader_criteria should NOT have been called on statement
            execute_state.statement.options.assert_not_called()

    def test_with_context_adds_filter(self) -> None:
        """Listener adds with_loader_criteria option when tenant context is set."""
        token = set_tenant_context("tenant-filter-test")
        try:
            execute_state = self._make_execute_state(is_column_load=False)
            _DO_ORM_EXECUTE(execute_state)
            execute_state.statement.options.assert_called_once()
        finally:
            clear_tenant_context(token)

    def test_column_load_skips_filter_injection(self) -> None:
        """Listener skips statement mutation when is_column_load is True."""
        token = set_tenant_context("tenant-colload")
        try:
            execute_state = self._make_execute_state(is_column_load=True)
            _DO_ORM_EXECUTE(execute_state)
            execute_state.statement.options.assert_not_called()
        finally:
            clear_tenant_context(token)


# ---------------------------------------------------------------------------
# Test Group 4: before_flush listener — auto-set (REQ-TI-004)
# ---------------------------------------------------------------------------

class TestBeforeFlushAutoSet:
    """Tests for the _before_flush listener: auto-assigning tenant_id on INSERT."""

    def _make_session(self, new_instances: list, dirty_instances: list) -> MagicMock:
        """Build a minimal mock Session."""
        session = MagicMock()
        session.new = new_instances
        session.dirty = dirty_instances
        return session

    def test_auto_set_tenant_id_on_new_instance(self) -> None:
        """New TenantMixin instance with tenant_id=None gets tenant_id assigned (REQ-TI-004)."""
        from app.models.base import TenantMixin

        instance = MagicMock(spec=TenantMixin)
        instance.tenant_id = None

        session = self._make_session(new_instances=[instance], dirty_instances=[])
        token = set_tenant_context("tenant-A")
        try:
            _BEFORE_FLUSH(session, MagicMock(), None)
        finally:
            clear_tenant_context(token)

        assert instance.tenant_id == "tenant-A"

    def test_no_context_during_flush_raises_error(self) -> None:
        """Listener raises TenantContextError when no context is set during flush."""
        from app.models.base import TenantMixin

        instance = MagicMock(spec=TenantMixin)
        instance.tenant_id = None

        session = self._make_session(new_instances=[instance], dirty_instances=[])
        assert get_tenant_context() is None
        with pytest.raises(TenantContextError):
            _BEFORE_FLUSH(session, MagicMock(), None)


# ---------------------------------------------------------------------------
# Test Group 5: before_flush listener — spoofing rejection (REQ-TI-005)
# ---------------------------------------------------------------------------

class TestBeforeFlushSpoofingRejection:
    """Tests for the _before_flush listener: cross-tenant write prevention."""

    def _make_session(self, new_instances: list, dirty_instances: list) -> MagicMock:
        session = MagicMock()
        session.new = new_instances
        session.dirty = dirty_instances
        return session

    def test_cross_tenant_write_raises_violation(self) -> None:
        """Instance with tenant_id='tenant-B' in context 'tenant-A' raises TenantWriteViolation (REQ-TI-005)."""
        from app.db.tenant_filter import TenantWriteViolation
        from app.models.base import TenantMixin

        instance = MagicMock(spec=TenantMixin)
        instance.tenant_id = "tenant-B"  # belongs to different tenant

        session = self._make_session(new_instances=[instance], dirty_instances=[])
        token = set_tenant_context("tenant-A")
        try:
            with pytest.raises(TenantWriteViolation):
                _BEFORE_FLUSH(session, MagicMock(), None)
        finally:
            clear_tenant_context(token)

    def test_same_tenant_write_succeeds(self) -> None:
        """Instance whose tenant_id matches active context is accepted without error."""
        from app.models.base import TenantMixin

        instance = MagicMock(spec=TenantMixin)
        instance.tenant_id = "tenant-A"

        session = self._make_session(new_instances=[instance], dirty_instances=[])
        token = set_tenant_context("tenant-A")
        try:
            # Should not raise
            _BEFORE_FLUSH(session, MagicMock(), None)
        finally:
            clear_tenant_context(token)

    async def test_bypass_skips_flush_validation(self) -> None:
        """bypass_tenant_context disables all flush validation."""
        from app.models.base import TenantMixin

        instance = MagicMock(spec=TenantMixin)
        instance.tenant_id = "any-tenant"

        session = MagicMock()
        session.new = [instance]
        session.dirty = []

        async with bypass_tenant_context():
            # Should not raise even though tenant_id doesn't match bypass sentinel
            _BEFORE_FLUSH(session, MagicMock(), None)


# ---------------------------------------------------------------------------
# Test Group 6: non-TenantMixin model skip
# ---------------------------------------------------------------------------

class TestBeforeFlushNonTenantMixinSkip:
    """Listener must skip models that do not inherit TenantMixin."""

    def test_non_tenant_mixin_instance_is_skipped(self) -> None:
        """before_flush skips instances that are not TenantMixin subclasses."""
        # A plain object — not a TenantMixin subclass
        plain_instance = MagicMock(spec=object)  # does NOT spec TenantMixin
        # Ensure isinstance(plain_instance, TenantMixin) returns False
        # MagicMock(spec=object) won't pass isinstance check for TenantMixin

        session = MagicMock()
        session.new = [plain_instance]
        session.dirty = []

        token = set_tenant_context("tenant-A")
        try:
            # Should not raise — non-TenantMixin instances are silently skipped
            _BEFORE_FLUSH(session, MagicMock(), None)
        finally:
            clear_tenant_context(token)
