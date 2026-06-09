"""Integration test fixtures: testcontainers PostgreSQL + async httpx client.

Integration tests require a Docker daemon. They are designed to run in CI (GitHub Actions)
where Docker is available. On local machines without Docker, these tests are skipped
automatically — only unit tests run locally.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _ollama_available() -> bool:
    """Return True if Ollama endpoint is reachable."""
    try:
        import httpx
        httpx.get(os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434"), timeout=1)
        return True
    except Exception:
        return False


def _spacy_available() -> bool:
    """Return True if spaCy is installed."""
    try:
        import spacy  # noqa: F401
        return True
    except ImportError:
        return False


skip_no_ollama = pytest.mark.skipif(
    not _ollama_available(),
    reason="Ollama not available — integration tests only",
)

skip_no_spacy = pytest.mark.skipif(
    not _spacy_available(),
    reason="spaCy not installed — integration tests only",
)

_GOLDEN_DIR = Path(__file__).parent / "fixtures" / "parser" / "golden"
_HAS_GOLDEN = _GOLDEN_DIR.exists() and bool(list(_GOLDEN_DIR.glob("*.docx")))

skip_no_golden = pytest.mark.skipif(
    not _HAS_GOLDEN,
    reason="Golden dataset not available",
)


@pytest.fixture
def skip_no_spacy(request):
    """Fixture: skip test if spaCy is not installed."""
    if not _spacy_available():
        pytest.skip("spaCy not installed")


@pytest.fixture
def skip_no_ollama(request):
    """Fixture: skip test if Ollama is not reachable."""
    if not _ollama_available():
        pytest.skip("Ollama not available")


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable."""
    try:
        import docker
        docker.from_env(timeout=3)
        return True
    except Exception:
        return False


# Skip entire session if Docker is unavailable (local dev without Docker)
_DOCKER_UP = _docker_available()
skip_no_docker = pytest.mark.skipif(
    not _DOCKER_UP,
    reason="Docker daemon not available — integration tests run in CI only",
)


@pytest.fixture(scope="session")
def pg_container():
    """Start pgvector/pgvector:pg16 container for the test session."""
    if not _DOCKER_UP:
        pytest.skip("Docker not available")
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
