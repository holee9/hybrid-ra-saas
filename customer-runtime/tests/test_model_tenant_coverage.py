"""CI audit: every model must be explicitly classified (REQ-TI-011).

Tests run without a database connection — only SQLAlchemy class-level
introspection is used. No fixtures, no async, no Docker required.
"""
import sys
import os

# Ensure src is on path (mirrors conftest.py pattern)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


from app.models.base import Base, is_tenant_scoped  # noqa: E402

# Models intentionally shared across tenants (global / immutable audit tables).
# These do NOT inherit TenantMixin by design. Add new globally-shared models
# here with a comment explaining why they are exempt from tenant isolation.
KNOWN_GLOBAL_MODELS: set[str] = {
    # Append-only audit trail — immutable, cross-tenant by design (SPEC-PERMISSION-001).
    "ReviewDecision",
    # Immutable role-change audit log — stores tenant_id as plain column, not TenantMixin
    # (no automatic ORM filter needed; accessed only by admin queries).
    "RoleAuditLog",
}

# Models that predate SPEC-TENANT-ISOLATION-001 and require a future Alembic
# migration (ADD COLUMN tenant_id + TenantMixin) to become tenant-scoped.
# Remove each entry from this set AFTER the migration is applied and verified.
# Track progress: each model should be migrated in a dedicated SPEC/issue.
MIGRATION_PENDING_MODELS: set[str] = {
    # Checklist domain (SPEC-CHECKLIST-001) — tenant migration pending.
    "ChecklistItem",
    "ChecklistExport",
    "ChecklistSnapshot",
    # Evidence domain (SPEC-EVIDENCE-001) — tenant migration pending.
    "EvidenceBinder",
    "EvidenceCollect",
    "EvidenceFile",
    "EvidenceGap",
    "EvidenceLink",
    "RefreshToken",
    # Traceability domain (SPEC-TRACEABILITY-001) — tenant migration pending.
    "TraceabilityEdge",
    "TraceabilityNode",
    # Analysis domain — tenant migration pending.
    "ConsistencyFinding",
    "GapFinding",
    "ImpactAnalysis",
    # Authoring domain (SPEC-AUTHORING-001) — tenant migration pending.
    "AuthoringSession",
    "AuthoringSectionEntry",
    # Audit domain — tenant migration pending.
    "AuditEvent",
}


def _collect_concrete_model_classes() -> list[type]:
    """Return all non-abstract SQLAlchemy model classes registered with Base."""
    seen: set[type] = set()

    def _recurse(cls: type) -> None:
        for sub in cls.__subclasses__():
            if sub in seen:
                continue
            seen.add(sub)
            _recurse(sub)

    _recurse(Base)

    concrete = [
        cls for cls in seen
        if not getattr(cls, "__abstract__", False)
        and hasattr(cls, "__tablename__")
    ]
    return concrete


def test_all_models_classified() -> None:
    """Every concrete model must either inherit TenantMixin or be in KNOWN_GLOBAL_MODELS.

    Fails immediately when a new model is added that is neither tenant-scoped
    nor explicitly acknowledged as globally shared. Forces the developer to
    make an explicit classification decision (REQ-TI-011).
    """
    model_classes = _collect_concrete_model_classes()
    assert model_classes, "No concrete model classes found — check that app.models imported correctly."

    unclassified: list[str] = []
    for cls in model_classes:
        if is_tenant_scoped(cls):
            continue  # correctly tenant-scoped via TenantMixin
        if cls.__name__ in KNOWN_GLOBAL_MODELS:
            continue  # intentionally global, acknowledged
        if cls.__name__ in MIGRATION_PENDING_MODELS:
            continue  # pre-SPEC-TENANT-ISOLATION-001; awaiting Alembic migration
        unclassified.append(cls.__name__)

    assert unclassified == [], (
        f"Unclassified models detected: {sorted(unclassified)}.\n"
        "Fix: add TenantMixin to make them tenant-scoped, OR add to KNOWN_GLOBAL_MODELS "
        "if intentionally global, OR add to MIGRATION_PENDING_MODELS if it is a "
        "legacy model awaiting a future tenant migration."
    )


def test_tenant_scoped_models_have_tenant_id_column() -> None:
    """All TenantMixin models must expose a tenant_id mapped column.

    Guards against accidental TenantMixin inheritance without the actual
    column being present (e.g. mixin applied but column removed).
    """
    model_classes = _collect_concrete_model_classes()
    missing: list[str] = []

    for cls in model_classes:
        if not is_tenant_scoped(cls):
            continue
        # Check both ORM attribute and table column
        has_attr = hasattr(cls, "tenant_id")
        has_col = "tenant_id" in cls.__table__.columns
        if not (has_attr and has_col):
            missing.append(cls.__name__)

    assert missing == [], (
        f"TenantMixin models missing tenant_id column: {sorted(missing)}."
    )


def test_known_global_models_do_not_inherit_tenant_mixin() -> None:
    """KNOWN_GLOBAL_MODELS must NOT inherit TenantMixin — otherwise the classification is wrong.

    If a model is added to KNOWN_GLOBAL_MODELS but also inherits TenantMixin,
    this test fails to alert the developer to remove it from KNOWN_GLOBAL_MODELS.
    """
    model_classes = _collect_concrete_model_classes()
    model_map = {cls.__name__: cls for cls in model_classes}

    misclassified: list[str] = []
    for name in KNOWN_GLOBAL_MODELS:
        cls = model_map.get(name)
        if cls is None:
            # Model no longer exists — stale entry
            misclassified.append(f"{name} (not found — stale KNOWN_GLOBAL_MODELS entry)")
            continue
        if is_tenant_scoped(cls):
            misclassified.append(
                f"{name} (inherits TenantMixin — remove from KNOWN_GLOBAL_MODELS)"
            )

    assert misclassified == [], (
        f"KNOWN_GLOBAL_MODELS classification errors: {misclassified}."
    )


def test_model_discovery_finds_expected_count() -> None:
    """Sanity check: at least 20 concrete models must be registered.

    Prevents a silent import failure from causing the classification tests
    to pass vacuously (empty model list).
    """
    model_classes = _collect_concrete_model_classes()
    assert len(model_classes) >= 20, (
        f"Expected >= 20 concrete models, found {len(model_classes)}. "
        "Check that app.models was imported successfully."
    )
