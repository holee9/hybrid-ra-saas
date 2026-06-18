"""GET /health — no auth required."""
import os

from fastapi import APIRouter

from app.services.ollama_health import check_ollama_health, is_circuit_open

router = APIRouter()

_OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://ollama:11434")


@router.get("/health")
async def health_check():
    return {"status": "ok"}


@router.get("/health/ollama")
async def ollama_health_check():
    """Check Ollama service availability and circuit breaker state.

    Returns:
        {"status": "ok"} when reachable, {"status": "degraded"} otherwise.
        Also reports circuit_open state for observability.
    """
    reachable = await check_ollama_health(_OLLAMA_ENDPOINT)
    circuit_open = is_circuit_open()
    status = "ok" if reachable else "degraded"
    return {"status": status, "circuit_open": circuit_open}
