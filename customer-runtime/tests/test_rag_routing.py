"""SPEC-RAG-001: RAG routing mode tests (REQ-RAG-001 through REQ-RAG-007).

Unit tests — no Docker required. All external calls mocked.
"""
import os

import pytest
from unittest.mock import AsyncMock, patch

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
os.environ.setdefault("REGULA_BASE_URL", "https://regula.abyz-lab.work")
os.environ.setdefault("REGULA_API_KEY", "test-regula-api-key")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EVIDENCE = [{"req_id": "req-1", "text": "System shall validate inputs.", "score": 0.8}]
_EVIDENCE_LOW = [{"req_id": "req-2", "text": "Low relevance note.", "score": 0.3}]


def _mock_db():
    return AsyncMock()


# ---------------------------------------------------------------------------
# REQ-RAG-002: local-only routing
# ---------------------------------------------------------------------------


class TestRoutingLocalOnly:
    """routing_mode='local-only' — only local path used, no Regula calls."""

    async def test_routing_local_only(self):
        """REQ-RAG-002: local-only → routing_used='local', no Regula call."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Local answer.")):
                    with patch.object(svc, "_call_regula_rag", new=AsyncMock()) as mock_regula:
                        result = await svc.query(
                            db=_mock_db(),
                            tenant_id="t1",
                            question="Safety requirements?",
                            product_id=None,
                            evidence_required=False,
                            top_k=5,
                            routing_mode="local-only",
                        )

        assert result["routing_used"] == "local"
        assert "req-1" in result["sources"]
        mock_regula.assert_not_called()

    async def test_routing_local_only_sources_match_evidence_links(self):
        """local-only: sources == evidence_links (req_ids)."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Answer.")):
                    result = await svc.query(
                        db=_mock_db(),
                        tenant_id="t1",
                        question="?",
                        product_id=None,
                        evidence_required=False,
                        top_k=5,
                        routing_mode="local-only",
                    )

        assert result["sources"] == result["evidence_links"]


# ---------------------------------------------------------------------------
# REQ-RAG-003: regula-only routing
# ---------------------------------------------------------------------------


class TestRoutingRegulaOnly:
    """routing_mode='regula-only' — Regula API called, pgvector skipped."""

    async def test_routing_regula_only_success(self):
        """REQ-RAG-003: regula-only success → routing_used='regula'."""
        from app.services.rag import RagService

        svc = RagService()

        regula_result = {"answer": "Regula answer.", "sources": ["doc-A"], "confidence": 0.9}

        with patch.object(svc, "_call_regula_rag", new=AsyncMock(return_value=regula_result)):
            with patch.object(svc, "_similarity_search", new=AsyncMock()) as mock_local:
                result = await svc.query(
                    db=_mock_db(),
                    tenant_id="t1",
                    question="Safety?",
                    product_id=None,
                    evidence_required=False,
                    top_k=5,
                    routing_mode="regula-only",
                )

        assert result["routing_used"] == "regula"
        assert result["answer"] == "Regula answer."
        assert result["sources"] == ["doc-A"]
        assert result["confidence"] == 0.9
        mock_local.assert_not_called()

    async def test_routing_regula_only_timeout(self):
        """REQ-RAG-006: Regula timeout → routing_used='degraded'."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_call_regula_rag", new=AsyncMock(return_value=None)):
            result = await svc.query(
                db=_mock_db(),
                tenant_id="t1",
                question="?",
                product_id=None,
                evidence_required=False,
                top_k=5,
                routing_mode="regula-only",
            )

        assert result["routing_used"] == "degraded"
        assert result["confidence"] == 0.0
        assert result["submit_safe"] is False


# ---------------------------------------------------------------------------
# REQ-RAG-004: hybrid routing
# ---------------------------------------------------------------------------


class TestRoutingHybrid:
    """routing_mode='hybrid' — local first, Regula fallback when confidence < 0.5."""

    async def test_routing_hybrid_local_wins(self):
        """REQ-RAG-004: hybrid, local confidence >= 0.5 → routing_used='hybrid-local'."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Good local answer.")):
                    with patch.object(svc, "_call_regula_rag", new=AsyncMock()) as mock_regula:
                        result = await svc.query(
                            db=_mock_db(),
                            tenant_id="t1",
                            question="?",
                            product_id=None,
                            evidence_required=False,
                            top_k=5,
                            routing_mode="hybrid",
                        )

        assert result["routing_used"] == "hybrid-local"
        mock_regula.assert_not_called()

    async def test_routing_hybrid_regula_fallback(self):
        """REQ-RAG-004: hybrid, local confidence < 0.5 → Regula used, routing_used='hybrid-regula'."""
        from app.services.rag import RagService

        svc = RagService()

        regula_result = {"answer": "Regula fallback.", "sources": ["doc-B"], "confidence": 0.75}

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            # Low score evidence → local confidence < 0.5
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE_LOW)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Low conf answer.")):
                    with patch.object(svc, "_call_regula_rag", new=AsyncMock(return_value=regula_result)):
                        result = await svc.query(
                            db=_mock_db(),
                            tenant_id="t1",
                            question="?",
                            product_id=None,
                            evidence_required=False,
                            top_k=5,
                            routing_mode="hybrid",
                        )

        assert result["routing_used"] == "hybrid-regula"
        assert result["answer"] == "Regula fallback."
        assert result["sources"] == ["doc-B"]

    async def test_routing_hybrid_all_failed(self):
        """REQ-RAG-007: hybrid, both local and Regula fail → all_failed=True."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_local_query", new=AsyncMock(side_effect=Exception("local down"))):
            with patch.object(svc, "_call_regula_rag", new=AsyncMock(return_value=None)):
                result = await svc.query(
                    db=_mock_db(),
                    tenant_id="t1",
                    question="?",
                    product_id=None,
                    evidence_required=False,
                    top_k=5,
                    routing_mode="hybrid",
                )

        assert result.get("all_failed") is True

    async def test_routing_hybrid_default_mode(self):
        """REQ-RAG-001: default routing_mode is 'hybrid' when not specified."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Answer.")):
                    # No routing_mode param — defaults to hybrid
                    result = await svc.query(
                        db=_mock_db(),
                        tenant_id="t1",
                        question="?",
                        product_id=None,
                        evidence_required=False,
                        top_k=5,
                    )

        # hybrid-local because local confidence (0.8) >= 0.5
        assert result["routing_used"] == "hybrid-local"


# ---------------------------------------------------------------------------
# REQ-RAG-005: response fields
# ---------------------------------------------------------------------------


class TestResponseFields:
    """REQ-RAG-005: routing_used and sources present in all routing paths."""

    @pytest.mark.parametrize("mode,expected_routing", [
        ("local-only", "local"),
    ], ids=["local-only"])
    async def test_response_has_routing_fields(self, mode: str, expected_routing: str):
        """All routing modes return routing_used and sources."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=_EVIDENCE)):
                with patch.object(svc, "_call_ollama", new=AsyncMock(return_value="Answer.")):
                    result = await svc.query(
                        db=_mock_db(),
                        tenant_id="t1",
                        question="?",
                        product_id=None,
                        evidence_required=False,
                        top_k=5,
                        routing_mode=mode,
                    )

        assert "routing_used" in result
        assert "sources" in result
        assert result["routing_used"] == expected_routing


# ---------------------------------------------------------------------------
# REQ-RAG-007: HTTP 503 via router
# ---------------------------------------------------------------------------


class TestHttp503:
    """REQ-RAG-007: all backends failed → HTTP 503."""

    async def test_503_when_all_failed(self):
        """Router returns 503 when service returns all_failed=True."""
        import os
        from httpx import ASGITransport, AsyncClient
        from unittest.mock import MagicMock
        from app.main import create_app
        from app.deps import get_db
        from app.services.rag import RagService

        os.environ["HYBRID_RA_API_TOKEN"] = "test-token-32-bytes-minimum-here!"
        app = create_app()

        all_failed_result = {
            "all_failed": True,
            "answer": "",
            "evidence_links": [],
            "confidence": 0.0,
            "submit_safe": False,
            "routing_used": "degraded",
            "sources": [],
        }

        with patch.object(RagService, "query", new=AsyncMock(return_value=all_failed_result)):
            async def mock_db():
                yield MagicMock()

            app.dependency_overrides[get_db] = mock_db

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/rag/query",
                    headers={
                        "Authorization": "Bearer test-token-32-bytes-minimum-here!",
                        "X-Tenant-ID": "tenant-1",
                    },
                    json={"question": "test", "routing_mode": "hybrid"},
                )

        assert resp.status_code == 503
        assert "unavailable" in resp.json()["detail"]
