"""Unit tests for health endpoint — RED phase.

No Docker or DB required — uses TestClient with mocked DB init.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def patch_db_init(monkeypatch):
    """Prevent actual DB initialization during health tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("BLOB_ACCOUNT_NAME", "myaccount")
    monkeypatch.setenv("BLOB_CONTAINER_NAME", "regulatory-docs")
    monkeypatch.setenv("BLOB_ACCOUNT_KEY", "key==")
    monkeypatch.setenv("APPINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test")


def test_health_returns_200():
    """GET /health returns 200 OK."""
    with patch("app.database.init_engine"):
        from fastapi.testclient import TestClient
        from app.main import create_app

        app = create_app()
        client = TestClient(app, raise_server_exceptions=True)
        # Skip lifespan by not using context manager
        response = client.get("/health")
        assert response.status_code == 200


def test_health_returns_ok_body():
    """GET /health body contains status: ok."""
    with patch("app.database.init_engine"):
        from fastapi.testclient import TestClient
        from app.main import create_app

        app = create_app()
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert data.get("status") == "ok"
