"""Authoring BFF router — Issue #48.

Thin BFF wrapper over AuthoringSession for ra-med-bot draft creation and review.

# @MX:ANCHOR: [AUTO] Authoring BFF public API boundary — 5 endpoints consumed by ra-med-bot.
# @MX:REASON: fan_in >= 3 (ra-med-bot client, test_authoring_bff, future async worker)
"""
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import verify_hybrid_bearer_token
from app.deps import get_db
from app.models.authoring_section_entry import AuthoringSectionEntry
from app.models.authoring_session import AuthoringSession
from app.routers.evidence_bff import _call_ollama_simple

router = APIRouter(prefix="/authoring", tags=["authoring-bff"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class DraftRequest(BaseModel):
    template_id: str
    document_type: str
    context: dict[str, Any]
    sections: list[str]


class SectionOut(BaseModel):
    section_id: str
    content: str | None
    ai_draft: str | None
    status: str


class DraftResponse(BaseModel):
    draft_id: str
    status: str
    document_type: str
    sections: list[SectionOut]
    created_at: datetime


class PatchRequest(BaseModel):
    section_id: str
    content: str
    status: str | None = None


class ReviewItem(BaseModel):
    section_id: str
    issue: str
    severity: str
    suggestion: str


class ReviewResponse(BaseModel):
    draft_id: str
    review_items: list[ReviewItem]
    reviewed_at: datetime


class ExportRequest(BaseModel):
    format: str = "json"


class ExportResponse(BaseModel):
    draft_id: str
    document_type: str
    sections: list[SectionOut]
    exported_at: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_session_or_404(draft_id: str, db: AsyncSession) -> AuthoringSession:
    result = await db.execute(
        select(AuthoringSession)
        .options(selectinload(AuthoringSession.entries))
        .where(AuthoringSession.session_id == draft_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="draft_id not found")
    return session


def _entries_to_sections(entries: list[AuthoringSectionEntry]) -> list[SectionOut]:
    return [
        SectionOut(
            section_id=e.section_id,
            content=e.content,
            ai_draft=e.ai_draft,
            status=e.status,
        )
        for e in entries
    ]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/draft", response_model=DraftResponse, status_code=status.HTTP_201_CREATED)
async def create_draft(
    body: DraftRequest,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> DraftResponse:
    """Create a draft document via AuthoringSession and trigger AI drafts per section."""
    from app.services.authoring_session import create_session

    template_sections = [{"section_id": s} for s in body.sections]

    session = await create_session(
        product_profile_id=body.context.get("product_profile_id", "unknown"),
        pack_id=body.template_id,
        created_by=tenant_id,
        db=db,
        template_sections=template_sections,
    )

    # Re-load with entries after commit
    result = await db.execute(
        select(AuthoringSession)
        .options(selectinload(AuthoringSession.entries))
        .where(AuthoringSession.session_id == session.session_id)
    )
    session = result.scalar_one()

    return DraftResponse(
        draft_id=session.session_id,
        status=session.status,
        document_type=body.document_type,
        sections=_entries_to_sections(session.entries),
        created_at=session.created_at,
    )


@router.get("/{draft_id}", response_model=DraftResponse)
async def get_draft(
    draft_id: str,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> DraftResponse:
    """Retrieve draft status and sections."""
    session = await _get_session_or_404(draft_id, db)
    return DraftResponse(
        draft_id=session.session_id,
        status=session.status,
        document_type=session.pack_id,
        sections=_entries_to_sections(session.entries),
        created_at=session.created_at,
    )


@router.patch("/{draft_id}", response_model=SectionOut)
async def update_draft_section(
    draft_id: str,
    body: PatchRequest,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> SectionOut:
    """Update a single section's content and status."""
    session = await _get_session_or_404(draft_id, db)

    entry = next(
        (e for e in session.entries if e.section_id == body.section_id),
        None,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"section_id '{body.section_id}' not found in draft",
        )

    entry.content = body.content
    if body.status is not None:
        entry.status = body.status

    await db.commit()
    await db.refresh(entry)

    return SectionOut(
        section_id=entry.section_id,
        content=entry.content,
        ai_draft=entry.ai_draft,
        status=entry.status,
    )


@router.post("/{draft_id}/review", response_model=ReviewResponse)
async def review_draft(
    draft_id: str,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """AI regulatory compliance review for each section with content.

    # @MX:NOTE: [AUTO] LLM is called once per section with content; 503 on Ollama failure.
    """
    session = await _get_session_or_404(draft_id, db)

    sections_with_content = [e for e in session.entries if e.content]
    if not sections_with_content:
        return ReviewResponse(
            draft_id=draft_id,
            review_items=[],
            reviewed_at=_now(),
        )

    review_items: list[ReviewItem] = []
    for entry in sections_with_content:
        prompt = (
            f"Section ID: {entry.section_id}\n"
            f"Content:\n{entry.content}\n\n"
            "Analyze the above section for regulatory compliance issues. "
            "Respond in JSON with keys: issue, severity (low|medium|high), suggestion. "
            "If no issues found, respond with: {\"issue\": \"none\", \"severity\": \"low\", \"suggestion\": \"none\"}"
        )
        try:
            raw = await _call_ollama_simple(prompt)
            parsed = json.loads(raw)
            review_items.append(
                ReviewItem(
                    section_id=entry.section_id,
                    issue=parsed.get("issue", ""),
                    severity=parsed.get("severity", "low"),
                    suggestion=parsed.get("suggestion", ""),
                )
            )
        except (ValueError, KeyError, json.JSONDecodeError):
            # LLM returned non-JSON — record as unparseable
            review_items.append(
                ReviewItem(
                    section_id=entry.section_id,
                    issue="Review response could not be parsed",
                    severity="low",
                    suggestion="Please review manually",
                )
            )

    return ReviewResponse(
        draft_id=draft_id,
        review_items=review_items,
        reviewed_at=_now(),
    )


@router.post("/{draft_id}/export", response_model=ExportResponse)
async def export_draft(
    draft_id: str,
    body: ExportRequest,
    tenant_id: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> ExportResponse:
    """Export draft as JSON (format=json only; docx reserved for future)."""
    if body.format != "json":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only 'json' format is supported currently",
        )

    session = await _get_session_or_404(draft_id, db)

    return ExportResponse(
        draft_id=session.session_id,
        document_type=session.pack_id,
        sections=_entries_to_sections(session.entries),
        exported_at=_now(),
    )
