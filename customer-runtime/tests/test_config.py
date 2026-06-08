"""T-001: Settings loads from env, missing JWT_SECRET raises ValidationError."""
import pytest
from pydantic import ValidationError


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "this-is-a-32-byte-minimum-secret!!")
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_BUCKET", "ra-documents")
    monkeypatch.setenv("MINIO_USER", "minioadmin")
    monkeypatch.setenv("MINIO_PASSWORD", "minioadmin")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080")

    from app.config import Settings
    s = Settings()
    assert s.database_url == "postgresql+asyncpg://u:p@localhost:5432/db"
    assert s.jwt_ttl_min == 60
    assert s.rate_limit_per_min == 100
    assert s.api_workers == 2


def test_missing_jwt_secret_raises(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_BUCKET", "ra-documents")
    monkeypatch.setenv("MINIO_USER", "minioadmin")
    monkeypatch.setenv("MINIO_PASSWORD", "minioadmin")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080")

    # Force reimport to avoid cached Settings
    import importlib
    import app.config as cfg_mod
    importlib.reload(cfg_mod)
    from app.config import Settings

    with pytest.raises((ValidationError, Exception)):
        Settings()


def test_jwt_secret_min_length(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
    monkeypatch.setenv("JWT_SECRET", "tooshort")
    monkeypatch.setenv("MINIO_ENDPOINT", "http://minio:9000")
    monkeypatch.setenv("MINIO_BUCKET", "ra-documents")
    monkeypatch.setenv("MINIO_USER", "minioadmin")
    monkeypatch.setenv("MINIO_PASSWORD", "minioadmin")
    monkeypatch.setenv("OLLAMA_ENDPOINT", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.1:8b")
    monkeypatch.setenv("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8080")

    import importlib
    import app.config as cfg_mod
    importlib.reload(cfg_mod)
    from app.config import Settings

    with pytest.raises((ValidationError, Exception)):
        Settings()
