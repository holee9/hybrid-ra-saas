"""LLM-based semantic mismatch detector — SPEC-TRACEABILITY-002.

Replaces the stub with a real Ollama/LLM call in production.
In CI/test environments (TESTING=1), returns a deterministic stub result.

# @MX:ANCHOR: [AUTO] detect_semantic_mismatches — LLM integration entry point for traceability
# @MX:REASON: fan_in >= 3 (scan router, test suite, future async job); external network I/O
# @MX:WARN: [AUTO] Network I/O with degraded fallback — LLM unavailable returns degraded=True result
# @MX:REASON: Ollama may be unreachable in CI or during outages; callers must check degraded flag
"""
import json
import logging
import os

import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_edge import TraceabilityEdge
from app.models.traceability_node import TraceabilityNode

logger = logging.getLogger(__name__)

LLM_ENDPOINT_URL = os.getenv("LLM_ENDPOINT_URL", os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434"))
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", os.getenv("OLLAMA_MODEL", "llama3.1:8b"))
LLM_DETECTOR_TIMEOUT = float(os.getenv("LLM_DETECTOR_TIMEOUT", "20.0"))
LLM_DETECTOR_MAX_RETRIES = int(os.getenv("LLM_DETECTOR_MAX_RETRIES", "2"))

# CI/test stub mode — set TESTING=1 to bypass real LLM calls (REQ-TRACEABILITY-002-004)
_TESTING = os.getenv("TESTING", "").strip() in ("1", "true", "yes")

_MISMATCH_PROMPT = """Analyze semantic mismatch between a requirement and its implementation.

Requirement: {req_text}
Implementation: {impl_text}

Respond ONLY with valid JSON — no markdown, no explanation outside JSON:
{{"mismatch_type": "semantic|structural|none", "confidence": 0.0, "rationale": "..."}}

- mismatch_type: "semantic" if meaning differs, "structural" if structure/format differs, "none" if aligned
- confidence: float 0.0-1.0 indicating certainty of the assessment
- rationale: one sentence explanation"""


class MismatchResult(BaseModel):
    """Semantic mismatch detection result — REQ-TRACEABILITY-002-006."""

    mismatch_type: str  # "semantic" | "structural" | "none" | "unknown"
    confidence: float  # 0.0-1.0
    rationale: str  # human-readable explanation
    degraded: bool = False  # True when LLM was unavailable


def _stub_result() -> MismatchResult:
    """Deterministic stub for CI/test environments (REQ-TRACEABILITY-002-004)."""
    return MismatchResult(
        mismatch_type="none",
        confidence=1.0,
        rationale="Stub result: TESTING=1 mode, no real LLM call made.",
        degraded=False,
    )


async def _call_llm(req_text: str, impl_text: str) -> MismatchResult:
    """POST to LLM /api/generate endpoint with retry.

    Returns degraded result on timeout or unavailability (REQ-TRACEABILITY-002-002, -008).
    """
    prompt = _MISMATCH_PROMPT.format(req_text=req_text, impl_text=impl_text)
    last_exc: Exception | None = None

    for attempt in range(LLM_DETECTOR_MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=LLM_DETECTOR_TIMEOUT) as client:
                resp = await client.post(
                    f"{LLM_ENDPOINT_URL}/api/generate",
                    json={"model": LLM_MODEL_NAME, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                raw = resp.json().get("response", "")
                try:
                    parsed = json.loads(raw)
                    return MismatchResult(
                        mismatch_type=parsed.get("mismatch_type", "unknown"),
                        confidence=float(parsed.get("confidence", 0.0)),
                        rationale=str(parsed.get("rationale", "")),
                        degraded=False,
                    )
                except (json.JSONDecodeError, ValueError, TypeError) as exc:
                    logger.warning("LLM response parse error: %s", exc)
                    return MismatchResult(
                        mismatch_type="unknown",
                        confidence=0.0,
                        rationale="LLM response parse error",
                        degraded=True,
                    )
        except httpx.TimeoutException as exc:
            logger.warning(
                "LLM detector timeout (attempt %d/%d)", attempt + 1, LLM_DETECTOR_MAX_RETRIES
            )
            last_exc = exc
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM detector error: %s", exc)
            last_exc = exc

    logger.error("LLM detector failed after %d attempts: %s", LLM_DETECTOR_MAX_RETRIES, last_exc)
    return MismatchResult(
        mismatch_type="unknown",
        confidence=0.0,
        rationale="LLM unavailable",
        degraded=True,
    )


async def detect_semantic_mismatches(
    edges: list[TraceabilityEdge],
    nodes: dict[str, TraceabilityNode],
    db: AsyncSession,
) -> list[ConsistencyFinding]:
    """Detect semantic mismatches between linked nodes using LLM.

    In TESTING=1 mode: returns empty list without calling LLM (REQ-TRACEABILITY-002-004).
    In production: calls real Ollama endpoint (REQ-TRACEABILITY-002-001).
    On LLM unavailability: returns degraded result (REQ-TRACEABILITY-002-002).
    """
    # CI stub — no network calls in test environments
    if _TESTING:
        return []

    findings: list[ConsistencyFinding] = []

    for edge in edges:
        source = nodes.get(str(edge.source_node_id))
        target = nodes.get(str(edge.target_node_id))
        if source is None or target is None:
            continue

        result = await _call_llm(
            req_text=f"[{source.node_type}] {source.content_hash}",
            impl_text=f"[{target.node_type}] {target.content_hash}",
        )

        if result.mismatch_type not in ("none",) or result.degraded:
            finding = ConsistencyFinding(
                finding_type="semantic_mismatch" if not result.degraded else "degraded_check",
                severity="medium" if result.confidence >= 0.7 else "low",
                source_node_id=str(edge.source_node_id),
                target_node_id=str(edge.target_node_id),
                description=result.rationale,
                confidence=result.confidence,
            )
            db.add(finding)
            findings.append(finding)

    if findings:
        await db.flush()

    return findings
