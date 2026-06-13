"""LLM-based semantic mismatch detector (Ollama stub).

# @MX:ANCHOR: [AUTO] detect_semantic_mismatches — local-only LLM integration point
# @MX:REASON: [AUTO] External system integration: calls Ollama endpoint; NEVER external APIs
# @MX:WARN: [AUTO] Network I/O with graceful fallback — test environments skip Ollama
# @MX:REASON: [AUTO] Ollama unreachable in CI/test; stub returns [] to keep tests deterministic
"""
import os

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_edge import TraceabilityEdge
from app.models.traceability_node import TraceabilityNode

OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


async def detect_semantic_mismatches(
    edges: list[TraceabilityEdge],
    nodes: dict[str, TraceabilityNode],
    db: AsyncSession,
) -> list[ConsistencyFinding]:
    """Detect semantic mismatches between linked nodes using Ollama.

    In test/CI mode: if Ollama is not reachable, returns [] safely.
    """
    # Stub: try Ollama health check; if unreachable return empty list
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_ENDPOINT}/api/tags")
            if resp.status_code != 200:
                return []
    except Exception:
        return []

    # Real implementation would iterate edges and call /api/generate per edge
    # Stub body — no real Ollama available in test
    return []
