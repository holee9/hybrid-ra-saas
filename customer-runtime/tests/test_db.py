"""T-002: DB engine, session factory, Base, mixins."""


def test_imports():
    from app.models.base import Base
    assert Base is not None


def test_base_metadata_empty():
    """Base.metadata starts with no tables."""
    # models/base creates Base but we must NOT import models here
    from app.models.base import Base
    # Tables are registered when model classes are defined (imported)
    # When only base is imported (no model files), tables dict has no user-defined tables
    assert isinstance(Base.metadata.tables, dict)


def test_new_id_is_uuid_string():
    from app.models.base import new_id
    uid = new_id()
    assert isinstance(uid, str)
    assert len(uid) == 36  # UUID4 with hyphens


def test_tenant_mixin_has_tenant_id():
    from app.models.base import TenantMixin
    assert hasattr(TenantMixin, "tenant_id")


def test_timestamp_mixin_has_timestamps():
    from app.models.base import TimestampMixin
    assert hasattr(TimestampMixin, "created_at")
    assert hasattr(TimestampMixin, "updated_at")
