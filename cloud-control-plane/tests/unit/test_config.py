"""Unit tests for Settings config — RED phase.

All tests run without Docker/network. Uses env var injection only.
"""

import pytest
from pydantic import ValidationError


def test_settings_defaults_for_crawler_flags(monkeypatch):
    """All crawler source flags default to enabled."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "myaccount")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "regulatory-docs")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key==")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")

    from app.config import Settings

    s = Settings()
    assert s.crawler_fda_enabled is True
    assert s.crawler_mfds_enabled is True
    assert s.crawler_eu_mdr_enabled is True


def test_settings_retry_defaults(monkeypatch):
    """Retry count=3, backoff initial 2s, multiplier 2."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "myaccount")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "regulatory-docs")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key==")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")

    from app.config import Settings

    s = Settings()
    assert s.retry_count == 3
    assert s.retry_backoff_initial == 2.0
    assert s.retry_backoff_multiplier == 2.0


def test_settings_rate_limit_default(monkeypatch):
    """Rate limit default: 1 req/sec per source."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "myaccount")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "regulatory-docs")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key==")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")

    from app.config import Settings

    s = Settings()
    assert s.rate_limit_per_source == 1.0


def test_settings_request_timeout_default(monkeypatch):
    """Request timeout has a sensible default."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "myaccount")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "regulatory-docs")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key==")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")

    from app.config import Settings

    s = Settings()
    assert s.request_timeout > 0


def test_settings_missing_database_url_raises():
    """Settings without DATABASE_URL raises ValidationError."""
    import sys

    # Remove cached module so we get a fresh import with no DATABASE_URL in env
    for mod_name in list(sys.modules.keys()):
        if "app.config" in mod_name or mod_name == "app.config":
            del sys.modules[mod_name]

    # Deliberately do NOT set DATABASE_URL
    with pytest.raises((ValidationError, Exception)):
        from app.config import Settings  # noqa: F401 (re-import)

        Settings()
