"""Tests for Docker configuration — T-019 (REQ-API-015).

Validates docker-compose.yml YAML structure without running Docker.
"""
import pathlib

import pytest


def load_compose():
    import yaml

    compose_file = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
    return compose_file, yaml.safe_load(compose_file.read_text(encoding="utf-8"))


def test_docker_compose_valid_yaml():
    """docker-compose.yml is valid YAML with at least 5 services."""
    compose_file = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
    assert compose_file.exists(), "docker-compose.yml must exist"

    _, data = load_compose()

    assert "services" in data, "docker-compose.yml must have a 'services' key"
    assert len(data["services"]) >= 5, (
        f"Expected >= 5 services, got {len(data['services'])}: {list(data['services'].keys())}"
    )


def test_docker_compose_has_required_services():
    """docker-compose.yml defines api, postgres, minio, ollama, redis services."""
    compose_file = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not yet created")

    _, data = load_compose()

    services = data.get("services", {})
    required = {"api", "postgres", "minio", "ollama", "redis"}
    missing = required - set(services.keys())
    assert not missing, f"Missing required services: {missing}"


def test_dockerfile_exists():
    """docker/Dockerfile exists."""
    dockerfile = pathlib.Path(__file__).parent.parent / "docker" / "Dockerfile"
    assert dockerfile.exists(), "docker/Dockerfile must exist"


def test_entrypoint_exists():
    """docker/entrypoint.sh exists."""
    entrypoint = pathlib.Path(__file__).parent.parent / "docker" / "entrypoint.sh"
    assert entrypoint.exists(), "docker/entrypoint.sh must exist"


def test_docker_compose_api_service_has_depends_on():
    """api service depends_on postgres, minio, ollama."""
    compose_file = pathlib.Path(__file__).parent.parent / "docker-compose.yml"
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not yet created")

    _, data = load_compose()

    api_service = data.get("services", {}).get("api", {})
    depends_on = api_service.get("depends_on", [])

    # depends_on can be list or dict
    if isinstance(depends_on, dict):
        depends_on = list(depends_on.keys())

    for svc in ["postgres", "minio", "ollama"]:
        assert svc in depends_on, f"api service must depend on {svc}"
