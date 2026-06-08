"""T-013: RAG service + POST /rag/query (REQ-API-008, REQ-API-009).

Unit tests only — no Docker required.
Integration test marked with @skip_no_docker.
"""
import os

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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

from tests.conftest import skip_no_docker


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestRagService:
    """Test RagService query logic with mocked embeddings and Ollama."""

    async def test_evidence_required_no_evidence_submit_safe_false(self):
        """REQ-API-008: evidence_required=True + no evidence -> submit_safe=False."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.0] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=[])):
                result = await svc.query(
                    db=AsyncMock(),
                    tenant_id="tenant-1",
                    question="What is the risk coverage?",
                    product_id=None,
                    evidence_required=True,
                    top_k=5,
                )

        assert result["submit_safe"] is False
        assert result["evidence_links"] == []

    async def test_evidence_found_submit_safe_true(self):
        """Evidence found -> evidence_links populated, submit_safe=True."""
        from app.services.rag import RagService

        svc = RagService()

        evidence = [{"req_id": "req-1", "text": "System shall validate inputs", "score": 0.9}]

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=evidence)):
                with patch.object(
                    svc,
                    "_call_ollama",
                    new=AsyncMock(return_value="Based on evidence, the system validates inputs."),
                ):
                    result = await svc.query(
                        db=AsyncMock(),
                        tenant_id="tenant-1",
                        question="Does the system validate inputs?",
                        product_id=None,
                        evidence_required=False,
                        top_k=5,
                    )

        assert result["submit_safe"] is True
        assert len(result["evidence_links"]) > 0

    async def test_ollama_timeout_graceful_fallback(self):
        """Ollama timeout -> returns response with confidence=0.0, no exception raised."""
        from app.services.rag import RagService

        svc = RagService()

        evidence = [{"req_id": "req-2", "text": "Some requirement", "score": 0.8}]

        async def slow_ollama(*args, **kwargs):
            raise TimeoutError("Ollama timeout")

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.1] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=evidence)):
                with patch.object(svc, "_call_ollama", new=slow_ollama):
                    result = await svc.query(
                        db=AsyncMock(),
                        tenant_id="tenant-1",
                        question="What requirements apply?",
                        product_id=None,
                        evidence_required=False,
                        top_k=5,
                    )

        # Should not raise — returns degraded response
        assert "answer" in result
        assert result["confidence"] == 0.0

    async def test_no_evidence_required_false_still_returns_response(self):
        """evidence_required=False + no evidence -> submit_safe=False but response returned."""
        from app.services.rag import RagService

        svc = RagService()

        with patch.object(svc, "_embed_question", new=AsyncMock(return_value=[0.0] * 384)):
            with patch.object(svc, "_similarity_search", new=AsyncMock(return_value=[])):
                result = await svc.query(
                    db=AsyncMock(),
                    tenant_id="tenant-1",
                    question="Any question",
                    product_id=None,
                    evidence_required=False,
                    top_k=5,
                )

        assert "answer" in result
        assert result["submit_safe"] is False  # no evidence -> False

    async def test_embed_question_fallback_when_sentence_transformers_missing(self):
        """ImportError on sentence_transformers -> zero vector returned gracefully."""
        from app.services.rag import RagService

        svc = RagService()

        with patch("app.services.rag.SentenceTransformer", side_effect=ImportError):
            vec = await svc._embed_question("test question")

        assert isinstance(vec, list)
        assert all(v == 0.0 for v in vec)


class TestRagEndpoint:
    """Test POST /rag/query endpoint."""

    async def test_endpoint_requires_auth(self):
        """No auth header -> 401."""
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.deps import get_db

        app = create_app()

        async def mock_db():
            yield MagicMock()

        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/rag/query", json={"question": "test"})
        assert resp.status_code == 401

    async def test_endpoint_returns_200_with_valid_request(self):
        """Valid request -> 200 with answer, evidence_links, confidence, submit_safe."""
        from httpx import ASGITransport, AsyncClient
        from app.main import create_app
        from app.core.security import create_token
        from app.deps import get_db
        from app.services.rag import RagService

        app = create_app()

        mock_result = {
            "answer": "The system validates all inputs per requirement REQ-001.",
            "evidence_links": ["req-1"],
            "confidence": 0.85,
            "submit_safe": True,
        }

        with patch.object(
            RagService,
            "query",
            new=AsyncMock(return_value=mock_result),
        ):
            async def mock_db():
                yield MagicMock()

            app.dependency_overrides[get_db] = mock_db
            token = create_token("user-1", "tenant-1")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as ac:
                resp = await ac.post(
                    "/rag/query",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Tenant-ID": "tenant-1",
                    },
                    json={"question": "What are the safety requirements?"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "evidence_links" in body
        assert "confidence" in body
        assert "submit_safe" in body


# ---------------------------------------------------------------------------
# Integration test (requires Docker)
# ---------------------------------------------------------------------------


@skip_no_docker
@pytest.mark.integration
async def test_rag_endpoint_integration(client):
    """Full endpoint: RAG query returns correct shape."""
    from app.core.security import create_token

    token = create_token("user-1", "tenant-1")
    resp = await client.post(
        "/rag/query",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-ID": "tenant-1"},
        json={
            "question": "What safety requirements apply?",
            "evidence_required": True,
            "top_k": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body
    assert "submit_safe" in body
