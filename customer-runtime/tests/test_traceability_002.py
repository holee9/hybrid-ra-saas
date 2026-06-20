"""SPEC-TRACEABILITY-002 — Semantic Mismatch Detector production implementation tests.

REQ-TRACEABILITY-002-001 through -008.
"""
import os

# Set env before any app import
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
os.environ.setdefault("MINIO_BUCKET", "ra-documents")
os.environ.setdefault("MINIO_USER", "minioadmin")
os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")
os.environ.setdefault("REGULA_API_KEY", "test-api-key")

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


# ---------------------------------------------------------------------------
# Unit tests for MismatchResult schema — REQ-TRACEABILITY-002-006
# ---------------------------------------------------------------------------


def test_mismatch_result_schema_all_fields():
    """MismatchResult must expose mismatch_type, confidence, rationale, degraded."""
    from app.services.traceability.llm_detector import MismatchResult

    result = MismatchResult(
        mismatch_type="semantic",
        confidence=0.85,
        rationale="Requirement specifies isolation but implementation lacks it.",
        degraded=False,
    )
    assert result.mismatch_type == "semantic"
    assert result.confidence == 0.85
    assert result.rationale != ""
    assert result.degraded is False


def test_mismatch_result_defaults():
    """degraded defaults to False — must be explicitly set on failure."""
    from app.services.traceability.llm_detector import MismatchResult

    result = MismatchResult(mismatch_type="none", confidence=1.0, rationale="ok")
    assert result.degraded is False


# ---------------------------------------------------------------------------
# REQ-TRACEABILITY-002-004 — TESTING=1 stub mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_stub_in_testing(monkeypatch):
    """TESTING=1 → detect_semantic_mismatches returns [] without LLM call."""
    monkeypatch.setenv("TESTING", "1")

    # Re-import module to pick up env change
    import importlib
    import app.services.traceability.llm_detector as mod

    importlib.reload(mod)

    edges: list = []
    nodes: dict = {}
    db = AsyncMock()

    result = await mod.detect_semantic_mismatches(edges, nodes, db)
    assert result == []

    # Restore
    monkeypatch.delenv("TESTING", raising=False)
    importlib.reload(mod)


# ---------------------------------------------------------------------------
# REQ-TRACEABILITY-002-001 — real LLM call in production
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_real_llm():
    """_call_llm: mock httpx POST → MismatchResult fields populated correctly."""
    from app.services.traceability.llm_detector import _call_llm

    llm_response = json.dumps({
        "mismatch_type": "semantic",
        "confidence": 0.9,
        "rationale": "The requirement mandates isolation but the implementation does not enforce it.",
    })
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": llm_response}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await _call_llm("System shall isolate power.", "power = connect()")

    assert result.mismatch_type == "semantic"
    assert result.confidence == pytest.approx(0.9)
    assert "isolation" in result.rationale or len(result.rationale) > 0
    assert result.degraded is False


# ---------------------------------------------------------------------------
# REQ-TRACEABILITY-002-002 — LLM unavailable → degraded=True
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_llm_unavailable():
    """When httpx raises ConnectError, result has degraded=True."""
    from app.services.traceability.llm_detector import _call_llm

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client_cls.return_value = mock_client

        result = await _call_llm("req", "impl")

    assert result.degraded is True
    assert result.mismatch_type == "unknown"
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# REQ-TRACEABILITY-002-008 — LLM timeout → degraded result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_llm_timeout():
    """On TimeoutException (all retries), result has degraded=True."""
    from app.services.traceability.llm_detector import _call_llm

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(
            side_effect=httpx.TimeoutException("read timeout")
        )
        mock_client_cls.return_value = mock_client

        result = await _call_llm("req", "impl")

    assert result.degraded is True
    assert result.mismatch_type == "unknown"


# ---------------------------------------------------------------------------
# REQ-TRACEABILITY-002-003 — mismatch result includes confidence + rationale
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_result_includes_confidence_and_rationale():
    """On successful LLM call, result includes non-empty confidence and rationale."""
    from app.services.traceability.llm_detector import _call_llm

    llm_payload = {
        "mismatch_type": "structural",
        "confidence": 0.75,
        "rationale": "Format differs from specification.",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": json.dumps(llm_payload)}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await _call_llm("req", "impl")

    assert isinstance(result.confidence, float)
    assert isinstance(result.rationale, str)
    assert len(result.rationale) > 0


# ---------------------------------------------------------------------------
# LLM non-JSON response → graceful degraded result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detect_mismatch_llm_non_json_response():
    """LLM returns non-JSON → degraded=True, no exception raised."""
    from app.services.traceability.llm_detector import _call_llm

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": "Sorry, I cannot analyze this."}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await _call_llm("req", "impl")

    assert result.degraded is True
    assert result.mismatch_type == "unknown"
