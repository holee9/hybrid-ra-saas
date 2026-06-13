"""Authoring router — SPEC-AUTHORING-001 Guided Authoring Workspace.

# @MX:NOTE: [AUTO] AI draft verified=False until human_edited — REQ-AUTHOR-010
"""
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_api_key
from app.deps import get_db
from app.models.authoring_section_entry import AuthoringSectionEntry
from app.models.authoring_session import AuthoringSession
from app.schemas.authoring import (
    EntryPatch,
    ExportRequest,
    SectionEntryOut,
    SectionWithEntry,
    SessionCreate,
    SessionOut,
)
from app.services import ai_draft as ai_draft_svc
from app.services import authoring_session as session_svc
from app.services import docx_exporter
from app.services.section_state import validate_transition

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/authoring", tags=["authoring"])

# ---------------------------------------------------------------------------
# Template section stub / cloud resolver
# ---------------------------------------------------------------------------

STUB_SECTIONS: list[dict] = [
    {
        "section_id": "SEC-001",
        "section_key": "scope",
        "title": "Scope",
        "required": True,
        "instructions": "Describe scope",
        "placeholder": "Enter scope...",
        "sort_order": 1,
    },
    {
        "section_id": "SEC-002",
        "section_key": "indications",
        "title": "Indications",
        "required": True,
        "instructions": "Describe indications",
        "placeholder": "Enter indications...",
        "sort_order": 2,
    },
    {
        "section_id": "SEC-003",
        "section_key": "warnings",
        "title": "Warnings (Optional)",
        "required": False,
        "instructions": "Optional warnings",
        "placeholder": "Enter warnings...",
        "sort_order": 3,
    },
]


async def _fetch_template_sections(pack_id: str) -> list[dict]:
    """Fetch template sections for the given pack.

    Uses TEMPLATE_API_URL env if set; otherwise returns stub data.
    Returns empty list for unknown pack_id (triggers 404 in caller).
    """
    template_api_url = os.environ.get("TEMPLATE_API_URL", "")

    if not template_api_url:
        # Stub mode for local/test
        if pack_id == "PACK-UNKNOWN":
            return []
        return STUB_SECTIONS

    # Live mode: fetch from cloud control plane
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{template_api_url}/packs/{pack_id}/sections"
            )
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Template API error for pack %s: %s", pack_id, exc)
        raise HTTPException(status_code=502, detail="Template API unavailable") from exc


# ---------------------------------------------------------------------------
# Section metadata lookup (for endpoints needing section metadata)
# ---------------------------------------------------------------------------

_STUB_BY_ID: dict[str, dict] = {s["section_id"]: s for s in STUB_SECTIONS}


def _get_section_meta(section_id: str, sections: list[dict]) -> dict:
    for s in sections:
        if s["section_id"] == section_id:
            return s
    return {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> SessionOut:
    """POST /authoring/sessions — Create a new authoring session.

    Returns 404 if pack not found or has no sections.
    """
    template_sections = await _fetch_template_sections(body.pack_id)

    if not template_sections:
        raise HTTPException(
            status_code=404,
            detail=f"Pack '{body.pack_id}' not found or has no sections.",
        )

    try:
        session = await session_svc.create_session(
            product_profile_id=body.product_profile_id,
            pack_id=body.pack_id,
            created_by=body.created_by,
            db=db,
            template_sections=template_sections,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return SessionOut(
        session_id=session.session_id,
        status=session.status,
        total_sections=len(template_sections),
        created_at=session.created_at,
    )


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict:
    """GET /authoring/sessions/{session_id} — Session + progress summary."""
    data = await session_svc.get_session_with_progress(session_id, db)
    if data is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return data


@router.get("/sessions/{session_id}/sections")
async def get_sections(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> list[SectionWithEntry]:
    """GET /authoring/sessions/{session_id}/sections — Section list with entries."""
    result = await db.execute(
        select(AuthoringSession)
        .options(selectinload(AuthoringSession.entries))
        .where(AuthoringSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    # Fetch template sections for metadata
    template_sections = await _fetch_template_sections(session.pack_id)
    sections_by_id = {s["section_id"]: s for s in template_sections}

    def sort_key(entry: AuthoringSectionEntry) -> int:
        meta = sections_by_id.get(entry.section_id, {})
        return meta.get("sort_order", 999)

    sorted_entries = sorted(session.entries, key=sort_key)

    response: list[SectionWithEntry] = []
    for entry in sorted_entries:
        meta = sections_by_id.get(entry.section_id, {})
        verified = entry.status in ("human_edited", "complete")
        entry_out = SectionEntryOut(
            entry_id=entry.entry_id,
            status=entry.status,
            content=entry.content,
            ai_draft=entry.ai_draft,
            ai_draft_confidence=entry.ai_draft_confidence,
            ai_draft_sources=entry.ai_draft_sources,
            ai_draft_verified=verified,
        )
        response.append(
            SectionWithEntry(
                section_id=entry.section_id,
                section_key=meta.get("section_key", entry.section_id),
                title=meta.get("title", entry.section_id),
                required=meta.get("required", True),
                instructions=meta.get("instructions"),
                placeholder=meta.get("placeholder"),
                sort_order=meta.get("sort_order", 0),
                entry=entry_out,
            )
        )
    return response


@router.patch("/sections/{entry_id}")
async def patch_section(
    entry_id: str,
    body: EntryPatch,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict:
    """PATCH /authoring/sections/{entry_id} — Update section content/status."""
    result = await db.execute(
        select(AuthoringSectionEntry).where(AuthoringSectionEntry.entry_id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Section entry not found.")

    # Determine target status
    new_status = body.status

    if body.content is not None and new_status is None:
        # Auto-transition: content provided without explicit status → human_edited
        new_status = "human_edited"

    if new_status is not None and new_status != entry.status:
        # Need section metadata to check is_required
        session_result = await db.execute(
            select(AuthoringSession).where(
                AuthoringSession.session_id == entry.session_id
            )
        )
        session = session_result.scalar_one_or_none()
        template_sections = []
        if session:
            template_sections = await _fetch_template_sections(session.pack_id)

        is_required = True
        for sec in template_sections:
            if sec["section_id"] == entry.section_id:
                is_required = sec.get("required", True)
                break

        validate_transition(entry.status, new_status, is_required)
        entry.status = new_status

    if body.content is not None:
        entry.content = body.content

    if body.skip_reason is not None:
        entry.skip_reason = body.skip_reason

    entry.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(entry)

    return {
        "entry_id": entry.entry_id,
        "status": entry.status,
        "updated_at": entry.updated_at,
    }


@router.post("/sections/{entry_id}/ai-draft")
async def generate_ai_draft(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> dict:
    """POST /authoring/sections/{entry_id}/ai-draft — Generate AI draft.

    # @MX:ANCHOR: [AUTO] POST /authoring/sections/{entry_id}/ai-draft — AI draft generation entry point
    # @MX:REASON: [AUTO] FR-210: _assert_local() must fire before any Ollama call

    Entry must be in 'empty' status. Returns 409 otherwise.
    """
    result = await db.execute(
        select(AuthoringSectionEntry).where(AuthoringSectionEntry.entry_id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Section entry not found.")

    if entry.status != "empty":
        raise HTTPException(
            status_code=409,
            detail=f"AI draft requires entry status 'empty', got '{entry.status}'.",
        )

    # Fetch section metadata
    session_result = await db.execute(
        select(AuthoringSession).where(AuthoringSession.session_id == entry.session_id)
    )
    session = session_result.scalar_one_or_none()
    template_sections = []
    if session:
        template_sections = await _fetch_template_sections(session.pack_id)

    section_instructions = ""
    product_context = ""
    if session:
        product_context = session.product_profile_id
    for sec in template_sections:
        if sec["section_id"] == entry.section_id:
            section_instructions = sec.get("instructions", "")
            break

    draft_result = await ai_draft_svc.generate_draft(
        entry=entry,
        section_instructions=section_instructions,
        product_context=product_context,
        db=db,
    )

    if draft_result.get("status") == "timeout":
        return draft_result

    if draft_result.get("status") == "error":
        raise HTTPException(status_code=500, detail=draft_result.get("reason", "AI error"))

    # Persist draft and transition status
    entry.ai_draft = draft_result.get("ai_draft")
    entry.ai_draft_confidence = draft_result.get("ai_draft_confidence")
    entry.ai_draft_sources = draft_result.get("ai_draft_sources", [])
    entry.status = "ai_draft"
    entry.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(entry)

    return {
        "entry_id": entry.entry_id,
        "ai_draft": entry.ai_draft,
        "ai_draft_confidence": entry.ai_draft_confidence,
        "ai_draft_sources": entry.ai_draft_sources,
        "status": "ai_draft",
        "verified": False,
    }


@router.post("/sessions/{session_id}/export")
async def export_session(
    session_id: str,
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_api_key),
) -> Any:
    """POST /authoring/sessions/{session_id}/export — Export session as DOCX or JSON."""
    if body.format not in ("docx", "json"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {body.format!r}. Use 'docx' or 'json'.",
        )

    # Fetch template sections for ordering metadata
    result = await db.execute(
        select(AuthoringSession).where(AuthoringSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    template_sections = await _fetch_template_sections(session.pack_id)

    try:
        output = await docx_exporter.export_session(
            session_id=session_id,
            fmt=body.format,
            db=db,
            template_sections=template_sections,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if body.format == "docx":
        return Response(
            content=output,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="session-{session_id}.docx"'},
        )

    return output
