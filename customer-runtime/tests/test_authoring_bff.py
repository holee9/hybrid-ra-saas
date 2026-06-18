"""T-021: Authoring BFF router — draft, get, patch, review, export endpoints.

Unit tests only — mocks DB and authoring service.
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


def _make_entry(section_id: str, content: str | None = None) -> MagicMock:
    e = MagicMock()
    e.section_id = section_id
    e.content = content
    e.ai_draft = None
    e.status = "empty" if content is None else "in_progress"
    e.entry_id = f"entry-{section_id}"
    return e


def _make_session(session_id: str = "test-draft-id", sections: list | None = None) -> MagicMock:
    s = MagicMock()
    s.session_id = session_id
    s.pack_id = "template-001"
    s.product_profile_id = "profile-001"
    s.status = "draft"
    s.created_by = "tenant-1"
    s.created_at = datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)
    s.updated_at = datetime(2026, 6, 18, 0, 0, 0, tzinfo=timezone.utc)
    s.entries = sections or [
        _make_entry("intro"),
        _make_entry("scope"),
    ]
    return s


class TestCreateDraft:
    """POST /api/v1/authoring/draft"""

    async def test_create_draft_returns_201(self):
        """Happy path: creates AuthoringSession and returns draft_id."""
        from app.routers.authoring_bff import create_draft, DraftRequest

        mock_db = AsyncMock()
        mock_session = _make_session()

        with patch("app.services.authoring_session.create_session", new=AsyncMock(return_value=mock_session)):
            # Mock the second select (reload with entries)
            mock_result = MagicMock()
            mock_result.scalar_one.return_value = mock_session
            mock_db.execute = AsyncMock(return_value=mock_result)

            result = await create_draft(
                body=DraftRequest(
                    template_id="template-001",
                    document_type="clinical_evaluation",
                    context={"product_profile_id": "profile-001"},
                    sections=["intro", "scope"],
                ),
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.draft_id == "test-draft-id"
        assert result.status == "draft"
        assert result.document_type == "clinical_evaluation"
        assert len(result.sections) == 2

    async def test_create_draft_empty_sections_raises_value_error(self):
        """Empty sections list -> ValueError from create_session."""
        from app.routers.authoring_bff import create_draft, DraftRequest

        mock_db = AsyncMock()

        async def _raise(*args, **kwargs):
            raise ValueError("Template sections must not be empty.")

        with patch("app.services.authoring_session.create_session", side_effect=_raise):
            with pytest.raises(ValueError):
                await create_draft(
                    body=DraftRequest(
                        template_id="t1",
                        document_type="doc",
                        context={},
                        sections=[],
                    ),
                    tenant_id="tenant-1",
                    db=mock_db,
                )


class TestGetDraft:
    """GET /api/v1/authoring/{draft_id}"""

    async def test_get_existing_draft(self):
        """Returns session data when draft_id found."""
        from app.routers.authoring_bff import get_draft

        mock_db = AsyncMock()
        mock_session = _make_session()

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            result = await get_draft(
                draft_id="test-draft-id",
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.draft_id == "test-draft-id"
        assert len(result.sections) == 2

    async def test_get_nonexistent_draft_raises_404(self):
        """Returns 404 when draft_id not found."""
        from app.routers.authoring_bff import get_draft
        from fastapi import HTTPException

        mock_db = AsyncMock()

        async def _raise_404(*args, **kwargs):
            raise HTTPException(status_code=404, detail="draft_id not found")

        with patch("app.routers.authoring_bff._get_session_or_404", side_effect=_raise_404):
            with pytest.raises(HTTPException) as exc_info:
                await get_draft(
                    draft_id="nonexistent",
                    tenant_id="tenant-1",
                    db=mock_db,
                )
        assert exc_info.value.status_code == 404


class TestPatchDraft:
    """PATCH /api/v1/authoring/{draft_id}"""

    async def test_patch_section_updates_content(self):
        """Updates entry content and status."""
        from app.routers.authoring_bff import update_draft_section, PatchRequest

        mock_db = AsyncMock()
        intro_entry = _make_entry("intro")
        mock_session = _make_session(sections=[intro_entry, _make_entry("scope")])

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock(side_effect=lambda e: None)

            result = await update_draft_section(
                draft_id="test-draft-id",
                body=PatchRequest(section_id="intro", content="Updated content", status="in_progress"),
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert intro_entry.content == "Updated content"
        assert intro_entry.status == "in_progress"

    async def test_patch_nonexistent_section_raises_404(self):
        """Section not in session -> 404."""
        from app.routers.authoring_bff import update_draft_section, PatchRequest
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_session = _make_session(sections=[_make_entry("intro")])

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            with pytest.raises(HTTPException) as exc_info:
                await update_draft_section(
                    draft_id="test-draft-id",
                    body=PatchRequest(section_id="nonexistent", content="x"),
                    tenant_id="tenant-1",
                    db=mock_db,
                )
        assert exc_info.value.status_code == 404


class TestReviewDraft:
    """POST /api/v1/authoring/{draft_id}/review"""

    async def test_review_returns_items_for_sections_with_content(self):
        """Sections with content get LLM review."""
        import json
        from app.routers.authoring_bff import review_draft

        mock_db = AsyncMock()
        entry_with_content = _make_entry("intro", content="Some regulatory content")
        entry_empty = _make_entry("scope")
        mock_session = _make_session(sections=[entry_with_content, entry_empty])

        llm_response = json.dumps({
            "issue": "Missing reference to ISO 14971",
            "severity": "high",
            "suggestion": "Add reference to ISO 14971 risk management standard",
        })

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            with patch("app.routers.authoring_bff._call_ollama_simple", new=AsyncMock(return_value=llm_response)):
                result = await review_draft(
                    draft_id="test-draft-id",
                    tenant_id="tenant-1",
                    db=mock_db,
                )

        # Only entry with content gets reviewed
        assert len(result.review_items) == 1
        assert result.review_items[0].section_id == "intro"
        assert result.review_items[0].severity == "high"

    async def test_review_no_content_returns_empty_list(self):
        """No sections with content -> empty review_items."""
        from app.routers.authoring_bff import review_draft

        mock_db = AsyncMock()
        mock_session = _make_session(sections=[_make_entry("intro"), _make_entry("scope")])

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            result = await review_draft(
                draft_id="test-draft-id",
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.review_items == []

    async def test_review_ollama_503_propagates(self):
        """LLM 503 propagates from _call_ollama_simple."""
        from app.routers.authoring_bff import review_draft
        from fastapi import HTTPException

        mock_db = AsyncMock()
        entry_with_content = _make_entry("intro", content="Content here")
        mock_session = _make_session(sections=[entry_with_content])

        def _raise_503(*args, **kwargs):
            raise HTTPException(status_code=503, detail="LLM service unavailable")

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            with patch("app.routers.authoring_bff._call_ollama_simple", new=AsyncMock(side_effect=_raise_503)):
                with pytest.raises(HTTPException) as exc_info:
                    await review_draft(
                        draft_id="test-draft-id",
                        tenant_id="tenant-1",
                        db=mock_db,
                    )
        assert exc_info.value.status_code == 503


class TestExportDraft:
    """POST /api/v1/authoring/{draft_id}/export"""

    async def test_export_json_format(self):
        """JSON export returns all sections."""
        from app.routers.authoring_bff import export_draft, ExportRequest

        mock_db = AsyncMock()
        mock_session = _make_session()

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            result = await export_draft(
                draft_id="test-draft-id",
                body=ExportRequest(format="json"),
                tenant_id="tenant-1",
                db=mock_db,
            )

        assert result.draft_id == "test-draft-id"
        assert len(result.sections) == 2
        assert result.exported_at is not None

    async def test_export_unsupported_format_raises_422(self):
        """Non-json format -> 422."""
        from app.routers.authoring_bff import export_draft, ExportRequest
        from fastapi import HTTPException

        mock_db = AsyncMock()
        mock_session = _make_session()

        with patch("app.routers.authoring_bff._get_session_or_404", new=AsyncMock(return_value=mock_session)):
            with pytest.raises(HTTPException) as exc_info:
                await export_draft(
                    draft_id="test-draft-id",
                    body=ExportRequest(format="docx"),
                    tenant_id="tenant-1",
                    db=mock_db,
                )
        assert exc_info.value.status_code == 422
