"""T-020: Evidence BFF router — POST /api/v1/evidence/collect, GET, synthesize, export.

Unit tests only — mocks DB and RAG service.
"""
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
os.environ.setdefault("REGULA_API_KEY", "test-regula-api-key")
os.environ.setdefault("HYBRID_RA_API_TOKEN", "test-hybrid-token")


def _make_collect(collect_id: str = "test-collect-id") -> MagicMock:
    """Create a mock EvidenceCollect object."""
    obj = MagicMock()
    obj.collect_id = collect_id
    obj.query = "What is the safety requirement?"
    obj.evidence_type = "safety"
    obj.document_ids = ["doc-1"]
    obj.items = [{"req_id": "req-1", "text": "System shall validate", "score": 0.9}]
    obj.synthesis = None
    obj.status = "collected"
    obj.created_at = datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)
    return obj


class TestCollectEndpoint:
    """POST /api/v1/evidence/collect"""

    async def test_collect_returns_201_with_items(self):
        """Happy path: collect stores results and returns 201."""
        from app.routers.evidence_bff import router, collect_evidence
        from app.routers.evidence_bff import CollectRequest

        mock_db = AsyncMock()
        mock_collect = _make_collect()

        rag_result = {
            "answer": "evidence found",
            "evidence_links": ["req-1", "req-2"],
            "confidence": 0.8,
            "submit_safe": True,
        }

        with patch("app.services.rag.RagService") as MockRag:
            mock_svc = MockRag.return_value
            mock_svc.query = AsyncMock(return_value=rag_result)

            with patch("app.routers.evidence_bff.EvidenceCollect") as MockModel:
                MockModel.return_value = mock_collect
                mock_db.add = MagicMock()
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                request = CollectRequest(
                    document_ids=["doc-1"],
                    query="What is the safety requirement?",
                    evidence_type="safety",
                    max_results=10,
                )

                result = await collect_evidence(
                    body=request,
                    tenant_id="tenant-1",
                    db=mock_db,
                )

        assert result.collect_id == "test-collect-id"
        assert result.status == "collected"

    async def test_collect_with_no_rag_results(self):
        """Empty RAG results -> items is empty list, status still collected."""
        from app.routers.evidence_bff import collect_evidence, CollectRequest

        mock_db = AsyncMock()
        mock_collect = _make_collect()
        mock_collect.items = []

        with patch("app.services.rag.RagService") as MockRag:
            mock_svc = MockRag.return_value
            mock_svc.query = AsyncMock(return_value={
                "answer": "no evidence",
                "evidence_links": [],
                "confidence": 0.0,
                "submit_safe": False,
            })

            with patch("app.routers.evidence_bff.EvidenceCollect") as MockModel:
                MockModel.return_value = mock_collect
                mock_db.add = MagicMock()
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                result = await collect_evidence(
                    body=CollectRequest(
                        document_ids=["doc-1"],
                        query="test",
                        evidence_type="general",
                    ),
                    tenant_id="tenant-1",
                    db=mock_db,
                )

        assert result.items == []


class TestGetCollect:
    """GET /api/v1/evidence/{collect_id}"""

    async def test_get_existing_collect(self):
        """Returns stored collect when collect_id exists."""
        from app.routers.evidence_bff import get_collect

        mock_db = AsyncMock()
        mock_collect = _make_collect()

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            result = await get_collect(
                collect_id="test-collect-id",
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.collect_id == "test-collect-id"
        assert result.status == "collected"

    async def test_get_nonexistent_collect_raises_404(self):
        """Returns 404 when collect_id not found."""
        from app.routers.evidence_bff import get_collect
        from fastapi import HTTPException

        mock_db = AsyncMock()

        async def _raise_404(*args, **kwargs):
            raise HTTPException(status_code=404, detail="collect_id not found")

        with patch("app.routers.evidence_bff._get_collect_or_404", side_effect=_raise_404):
            with pytest.raises(HTTPException) as exc_info:
                await get_collect(
                    collect_id="nonexistent",
                    tenant_id="tenant-1",
                    db=mock_db,
                )
        assert exc_info.value.status_code == 404


class TestSynthesizeCollect:
    """POST /api/v1/evidence/{collect_id}/synthesize"""

    async def test_synthesize_calls_ollama_and_updates_status(self):
        """Happy path: Ollama returns synthesis text, status becomes 'synthesized'."""
        from app.routers.evidence_bff import synthesize_collect

        mock_db = AsyncMock()
        mock_collect = _make_collect()

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            with patch("app.routers.evidence_bff._call_ollama_simple", new=AsyncMock(return_value="Summary text")):
                mock_db.commit = AsyncMock()
                mock_db.refresh = AsyncMock()

                result = await synthesize_collect(
                    collect_id="test-collect-id",
                    tenant_id="tenant-1",
                    db=mock_db,
                )

        assert result.synthesis == "Summary text"
        assert result.status == "synthesized"
        assert mock_collect.synthesis == "Summary text"
        assert mock_collect.status == "synthesized"

    async def test_synthesize_empty_items_raises_422(self):
        """No items to synthesize -> 422."""
        from app.routers.evidence_bff import synthesize_collect
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_collect = _make_collect()
        mock_collect.items = []

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            with pytest.raises(HTTPException) as exc_info:
                await synthesize_collect(
                    collect_id="test-collect-id",
                    tenant_id="tenant-1",
                    db=mock_db,
                )
        assert exc_info.value.status_code == 422

    async def test_synthesize_ollama_unavailable_returns_503(self):
        """Ollama failure -> 503."""
        from app.routers.evidence_bff import synthesize_collect
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_collect = _make_collect()

        def _raise_503(*args, **kwargs):
            raise HTTPException(status_code=503, detail="LLM service unavailable")

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            with patch("app.routers.evidence_bff._call_ollama_simple", side_effect=_raise_503):
                with pytest.raises(HTTPException) as exc_info:
                    await synthesize_collect(
                        collect_id="test-collect-id",
                        tenant_id="tenant-1",
                        db=mock_db,
                    )
        assert exc_info.value.status_code == 503


class TestExportCollect:
    """GET /api/v1/evidence/{collect_id}/export"""

    async def test_export_returns_items_and_synthesis(self):
        """Export returns all items and synthesis field."""
        from app.routers.evidence_bff import export_collect

        mock_db = AsyncMock()
        mock_collect = _make_collect()
        mock_collect.synthesis = "Synthesized text"

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            result = await export_collect(
                collect_id="test-collect-id",
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.collect_id == "test-collect-id"
        assert result.synthesis == "Synthesized text"
        assert len(result.items) == 1
        assert result.exported_at is not None

    async def test_export_without_synthesis(self):
        """Export returns None synthesis when not yet synthesized."""
        from app.routers.evidence_bff import export_collect

        mock_db = AsyncMock()
        mock_collect = _make_collect()
        mock_collect.synthesis = None

        with patch("app.routers.evidence_bff._get_collect_or_404", new=AsyncMock(return_value=mock_collect)):
            result = await export_collect(
                collect_id="test-collect-id",
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.synthesis is None
