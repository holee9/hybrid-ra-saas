"""Ollama availability circuit breaker — REQ-API-009.

Provides health check and circuit breaker state for all Ollama callers
(RagService, llm_fallback).

# @MX:WARN: [AUTO] Circuit breaker state is process-local, not distributed.
# @MX:REASON: Single process per container on Azure Container Apps — acceptable for MVP.
# Multi-instance deployments need Redis-backed state.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

# Circuit breaker globals — process-local, intentional for MVP (see @MX:WARN above)
_ollama_circuit_open: bool = False
_ollama_fail_count: int = 0

CIRCUIT_BREAKER_THRESHOLD: int = 3


class OllamaUnavailableError(RuntimeError):
    """Raised when the Ollama circuit breaker is open."""


async def check_ollama_health(base_url: str, timeout: float = 5.0) -> bool:
    """Return True if Ollama /api/tags responds with HTTP 200.

    # @MX:ANCHOR: [AUTO] check_ollama_health — public API for /health/ollama + circuit probe
    # @MX:REASON: fan_in >= 2 (health router, tests); contract must be stable
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{base_url}/api/tags")
            return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def record_ollama_failure() -> None:
    """Increment failure counter; open circuit when threshold reached."""
    global _ollama_fail_count, _ollama_circuit_open  # noqa: PLW0603
    _ollama_fail_count += 1
    if _ollama_fail_count >= CIRCUIT_BREAKER_THRESHOLD:
        if not _ollama_circuit_open:
            logger.warning(
                "Ollama circuit breaker OPEN after %d consecutive failures",
                _ollama_fail_count,
            )
        _ollama_circuit_open = True


def record_ollama_success() -> None:
    """Reset failure counter and close circuit on success."""
    global _ollama_fail_count, _ollama_circuit_open  # noqa: PLW0603
    if _ollama_circuit_open:
        logger.info("Ollama circuit breaker CLOSED — service recovered")
    _ollama_fail_count = 0
    _ollama_circuit_open = False


def is_circuit_open() -> bool:
    """Return True when the circuit breaker is open (Ollama presumed down)."""
    return _ollama_circuit_open
