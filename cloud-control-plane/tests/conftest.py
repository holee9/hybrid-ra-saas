"""Test fixtures for cloud-control-plane.

Integration tests require a Docker daemon and are CI-only.
Unit tests run without Docker or network — always.
"""
import os
import sys

import pytest

# Ensure src is on path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def _docker_available() -> bool:
    """Return True if a Docker daemon is reachable."""
    try:
        import docker

        docker.from_env(timeout=3)
        return True
    except Exception:
        return False


# Skip marker for tests that need Docker (integration tests, CI-only)
_DOCKER_UP = _docker_available()
skip_no_docker = pytest.mark.skipif(
    not _DOCKER_UP,
    reason="Docker daemon not available — integration tests run in CI only",
)
