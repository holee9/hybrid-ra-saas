"""Integration test fixtures: testcontainers PostgreSQL + async httpx client."""
import asyncio
import os
import subprocess
import sys

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture(scope="session")
def pg_container():
    """Start pgvector/pgvector:pg16 container for the test session."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(
        image="pgvector/pgvector:pg16",
        username="ra_user",
        password="test_pass",
        dbname="ra_test",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(pg_container):
    """asyncpg URL from the test container."""
    raw = pg_container.get_connection_url()
    return raw.replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
def run_alembic(db_url):
    """Run alembic upgrade head once per session."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    project_root = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-x",
            f"url={db_url}",
            "upgrade",
            "head",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic failed:\nSTDOUT:{result.stdout}\nSTDERR:{result.stderr}")
    return db_url


@pytest_asyncio.fixture(scope="function")
async def client(run_alembic, db_url):
    """Async httpx client connected to the test FastAPI app."""
    from app.database import init_engine
    from app.main import create_app

    # Reinitialize engine to test DB URL
    os.environ.setdefault("DATABASE_URL", db_url)
    os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_BUCKET", "ra-documents")
    os.environ.setdefault("MINIO_USER", "minioadmin")
    os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
    os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

    init_engine(db_url)
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
