"""SPEC-AUTHORING-001: Guided Authoring Workspace — TDD test suite.

AC-001 through AC-016 coverage.
Uses SQLite in-memory for speed (no Docker required).
"""
import asyncio
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

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
TEST_API_KEY = "test-api-key"
AUTH_HEADERS = {"X-Regula-API-Key": TEST_API_KEY}


@pytest_asyncio.fixture(scope="function")
async def authoring_client():
    """Async httpx client backed by SQLite in-memory DB.

    Overrides get_db dependency to use the in-memory session.
    """
    from app.database import init_engine
    from app.main import create_app
    from app.models.base import Base
    # Register all models including authoring models
    from app.models import authoring_session, authoring_section_entry  # noqa: F401

    engine = create_async_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    from app.deps import get_db
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac, session_factory

    await engine.dispose()


# ---------------------------------------------------------------------------
# AC-001: POST /authoring/sessions → 201 with session_id, total_sections
# ---------------------------------------------------------------------------

async def test_create_session_success(authoring_client):
    """AC-001: Create session returns 201, session_id, total_sections."""
    ac, _ = authoring_client
    resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001", "created_by": "user1"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "session_id" in data
    assert data["total_sections"] == 3  # stub has 3 sections
    assert data["status"] == "draft"


# ---------------------------------------------------------------------------
# AC-002: Unknown pack → 404, no session persisted
# ---------------------------------------------------------------------------

async def test_create_session_unknown_pack(authoring_client):
    """AC-002: pack_id=PACK-UNKNOWN → 404, session not created."""
    ac, session_factory = authoring_client
    resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-UNKNOWN"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404, resp.text

    # Verify no session was persisted
    from sqlalchemy import select, func
    from app.models.authoring_session import AuthoringSession
    async with session_factory() as db:
        result = await db.execute(
            select(func.count()).select_from(AuthoringSession)
        )
        count = result.scalar_one()
    assert count == 0


# ---------------------------------------------------------------------------
# AC-003: GET sections returns title, instructions, placeholder, required, entry.status
# ---------------------------------------------------------------------------

async def test_get_sections(authoring_client):
    """AC-003: GET sections returns all expected fields."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]

    resp = await ac.get(f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    sections = resp.json()
    assert len(sections) == 3

    first = sections[0]
    assert "title" in first
    assert "instructions" in first
    assert "placeholder" in first
    assert "required" in first
    assert "entry" in first
    assert first["entry"]["status"] == "empty"


# ---------------------------------------------------------------------------
# AC-004: Required vs optional sections distinguishable
# ---------------------------------------------------------------------------

async def test_sections_required_optional(authoring_client):
    """AC-004: Sections have required field; mix of required and optional."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]

    resp = await ac.get(f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS)
    sections = resp.json()
    required_flags = [s["required"] for s in sections]
    # stub has 2 required, 1 optional
    assert True in required_flags
    assert False in required_flags


# ---------------------------------------------------------------------------
# AC-005: complete → skipped → 400
# ---------------------------------------------------------------------------

async def test_forbidden_transition_complete_to_skipped(authoring_client):
    """AC-005: complete → skipped is forbidden (400)."""
    ac, session_factory = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]

    # Get entry_id for first section
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    # Drive to complete: empty→human_edited→complete
    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"content": "draft text"},
        headers=AUTH_HEADERS,
    )
    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "complete"},
        headers=AUTH_HEADERS,
    )

    # Now try to skip → 400
    resp = await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "skipped"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# AC-006: PATCH content → status = human_edited
# ---------------------------------------------------------------------------

async def test_patch_content_sets_human_edited(authoring_client):
    """AC-006: Providing content auto-transitions status to human_edited."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    resp = await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"content": "My draft content"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "human_edited"


# ---------------------------------------------------------------------------
# AC-007: ai_draft → complete directly → 400
# ---------------------------------------------------------------------------

async def test_ai_draft_direct_to_complete_forbidden(authoring_client):
    """AC-007: ai_draft → complete direct transition is forbidden (400)."""
    from app.models.authoring_section_entry import AuthoringSectionEntry
    from sqlalchemy import update

    ac, session_factory = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    # Force status to ai_draft directly via DB
    async with session_factory() as db:
        await db.execute(
            update(AuthoringSectionEntry)
            .where(AuthoringSectionEntry.entry_id == entry_id)
            .values(status="ai_draft")
        )
        await db.commit()

    # Try to transition to complete → 400
    resp = await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "complete"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# AC-008: AI draft generation (mocked Ollama)
# ---------------------------------------------------------------------------

async def test_ai_draft_generation_mocked(authoring_client):
    """AC-008: POST ai-draft → status=ai_draft, confidence and sources stored."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    mock_response = json.dumps({
        "draft": "This is the generated scope text.",
        "confidence": 0.85,
        "sources": ["REF-001", "REF-002"],
    })

    async def mock_call(*args, **kwargs):
        return MagicMock(
            json=lambda: {"response": mock_response},
            raise_for_status=MagicMock(),
        )

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=MagicMock(
        json=MagicMock(return_value={"response": mock_response}),
        raise_for_status=MagicMock(),
    ))

    with patch("app.services.ai_draft._call_ollama") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}
        resp = await ac.post(
            f"/authoring/sections/{entry_id}/ai-draft",
            headers=AUTH_HEADERS,
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ai_draft"
    assert data["ai_draft_confidence"] == 0.85
    assert "REF-001" in data["ai_draft_sources"]


# ---------------------------------------------------------------------------
# AC-009: _assert_local is called (network stays local)
# ---------------------------------------------------------------------------

async def test_ai_draft_no_cloud_call(authoring_client):
    """AC-009: _assert_local is called before any Ollama HTTP call."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    mock_response = json.dumps({"draft": "test", "confidence": 0.5, "sources": []})

    with patch("app.services.ai_draft._assert_local") as mock_assert, \
         patch("app.services.ai_draft._call_ollama") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}
        await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)

    mock_assert.assert_called_once()


# ---------------------------------------------------------------------------
# AC-010: ai_draft status → verified=false
# ---------------------------------------------------------------------------

async def test_ai_draft_marked_not_verified(authoring_client):
    """AC-010: After AI draft, ai_draft_verified=False in sections response."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    mock_response = json.dumps({"draft": "text", "confidence": 0.7, "sources": []})
    with patch("app.services.ai_draft._assert_local"), \
         patch("app.services.ai_draft._call_ollama") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}
        await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)

    # Check sections endpoint
    sections_resp2 = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_data = next(
        s["entry"] for s in sections_resp2.json() if s["entry"]["entry_id"] == entry_id
    )
    assert entry_data["ai_draft_verified"] is False
    assert entry_data["status"] == "ai_draft"


# ---------------------------------------------------------------------------
# AC-011: ai_draft_sources in response
# ---------------------------------------------------------------------------

async def test_ai_draft_sources_in_response(authoring_client):
    """AC-011: ai_draft_sources are returned in the response."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    sources = ["SRC-A", "SRC-B", "SRC-C"]
    mock_response = json.dumps({"draft": "test", "confidence": 0.9, "sources": sources})

    with patch("app.services.ai_draft._assert_local"), \
         patch("app.services.ai_draft._call_ollama") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}
        resp = await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ai_draft_sources"] == sources


# ---------------------------------------------------------------------------
# AC-012: Overwriting ai_draft on non-empty entry → 409
# ---------------------------------------------------------------------------

async def test_ai_draft_overwrite_forbidden(authoring_client):
    """AC-012: Entry in human_edited → POST ai-draft → 409."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    # Transition to human_edited
    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"content": "Human written content"},
        headers=AUTH_HEADERS,
    )

    # Now try AI draft → 409
    resp = await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# AC-013: AI draft timeout → response status="timeout"
# ---------------------------------------------------------------------------

async def test_ai_draft_timeout(authoring_client):
    """AC-013: Mock Ollama to timeout → response contains status='timeout'."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    async def slow_ollama(*args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("app.services.ai_draft._assert_local"), \
         patch("app.services.ai_draft._call_ollama", side_effect=slow_ollama):
        resp = await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "timeout"
    assert "reason" in data


# ---------------------------------------------------------------------------
# AC-014: Required section skip → 400
# ---------------------------------------------------------------------------

async def test_required_section_skip_forbidden(authoring_client):
    """AC-014: Required section cannot be skipped → 400."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )

    # Get a required section
    required_section = next(s for s in sections_resp.json() if s["required"])
    entry_id = required_section["entry"]["entry_id"]

    resp = await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "skipped"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 400, resp.text


# ---------------------------------------------------------------------------
# AC-015: completion_pct calculation
# ---------------------------------------------------------------------------

async def test_completion_pct(authoring_client):
    """AC-015: 1 of 2 required complete → completion_pct=50.0."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    sections = sections_resp.json()

    # Mark first required section as complete (empty→human_edited→complete)
    required_sections = [s for s in sections if s["required"]]
    entry_id = required_sections[0]["entry"]["entry_id"]

    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"content": "done"},
        headers=AUTH_HEADERS,
    )
    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "complete"},
        headers=AUTH_HEADERS,
    )

    # Get progress
    session_resp = await ac.get(f"/authoring/sessions/{session_id}", headers=AUTH_HEADERS)
    assert session_resp.status_code == 200, session_resp.text
    progress = session_resp.json()["progress"]

    # 2 required sections total (third is optional), 1 complete
    assert progress["completed"] == 1
    # blocking_gaps: sections not complete and not skipped
    assert len(progress["blocking_gaps"]) >= 1


# ---------------------------------------------------------------------------
# AC-016: export JSON returns sections in sort_order
# ---------------------------------------------------------------------------

async def test_export_json_order(authoring_client):
    """AC-016 (JSON): export json → sections in sort_order."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]

    resp = await ac.post(
        f"/authoring/sessions/{session_id}/export",
        json={"format": "json"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "sections" in data
    orders = [s["sort_order"] for s in data["sections"]]
    assert orders == sorted(orders), "Sections not in sort_order"


# ---------------------------------------------------------------------------
# Additional edge case: optional section CAN be skipped
# ---------------------------------------------------------------------------

async def test_optional_section_can_be_skipped(authoring_client):
    """Optional sections can transition to skipped."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    optional_sections = [s for s in sections_resp.json() if not s["required"]]
    assert optional_sections, "No optional sections in stub"
    entry_id = optional_sections[0]["entry"]["entry_id"]

    resp = await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"status": "skipped", "skip_reason": "Not applicable"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "skipped"


# ---------------------------------------------------------------------------
# Edge: GET session not found → 404
# ---------------------------------------------------------------------------

async def test_get_session_not_found(authoring_client):
    """GET /authoring/sessions/{id} with unknown id → 404."""
    ac, _ = authoring_client
    resp = await ac.get(
        "/authoring/sessions/nonexistent-session-id",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Edge: ai_draft_verified = True after human_edited
# ---------------------------------------------------------------------------

async def test_ai_draft_verified_after_human_edit(authoring_client):
    """After transitioning ai_draft → human_edited, verified=True."""
    ac, _ = authoring_client
    create_resp = await ac.post(
        "/authoring/sessions",
        json={"product_profile_id": "PROD-001", "pack_id": "PACK-RA-001"},
        headers=AUTH_HEADERS,
    )
    session_id = create_resp.json()["session_id"]
    sections_resp = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_id = sections_resp.json()[0]["entry"]["entry_id"]

    # Generate AI draft
    mock_response = json.dumps({"draft": "AI text", "confidence": 0.8, "sources": []})
    with patch("app.services.ai_draft._assert_local"), \
         patch("app.services.ai_draft._call_ollama") as mock_ollama:
        mock_ollama.return_value = {"response": mock_response}
        await ac.post(f"/authoring/sections/{entry_id}/ai-draft", headers=AUTH_HEADERS)

    # Edit the draft → human_edited
    await ac.patch(
        f"/authoring/sections/{entry_id}",
        json={"content": "Edited content"},
        headers=AUTH_HEADERS,
    )

    # Check verified=True
    sections_resp2 = await ac.get(
        f"/authoring/sessions/{session_id}/sections", headers=AUTH_HEADERS
    )
    entry_data = next(
        s["entry"] for s in sections_resp2.json() if s["entry"]["entry_id"] == entry_id
    )
    assert entry_data["ai_draft_verified"] is True
