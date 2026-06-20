"""Root conftest: add src to sys.path."""
import sys
import os
import pytest

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


@pytest.fixture
def skip_no_spacy():
    try:
        import spacy
        spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        pytest.skip("spaCy en_core_web_sm not installed")


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable."""
    try:
        import docker

        docker.from_env(timeout=3)
        return True
    except Exception:
        return False


skip_no_docker = pytest.mark.skipif(
    not _docker_available(),
    reason="Docker daemon not available - integration tests run in CI only",
)
