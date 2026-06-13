"""AuthoringSession service — SPEC-AUTHORING-001."""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.authoring_section_entry import AuthoringSectionEntry
from app.models.authoring_session import AuthoringSession


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(
    product_profile_id: str,
    pack_id: str,
    created_by: str | None,
    db: AsyncSession,
    template_sections: list[dict],
) -> AuthoringSession:
    """Create a new AuthoringSession with one empty entry per template section.

    Args:
        product_profile_id: ID of the product profile.
        pack_id: The template pack ID.
        created_by: Optional creator identifier.
        db: Async database session.
        template_sections: List of section dicts from the template API.

    Returns:
        Persisted AuthoringSession.

    Raises:
        ValueError: If template_sections is empty.
    """
    if not template_sections:
        raise ValueError("Template sections must not be empty. Pack has no sections.")

    session = AuthoringSession(
        session_id=str(uuid.uuid4()),
        product_profile_id=product_profile_id,
        pack_id=pack_id,
        status="draft",
        created_by=created_by,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(session)
    await db.flush()  # ensure session_id is available

    for sec in template_sections:
        entry = AuthoringSectionEntry(
            entry_id=str(uuid.uuid4()),
            session_id=session.session_id,
            section_id=sec["section_id"],
            status="empty",
            updated_at=_now(),
        )
        db.add(entry)

    await db.commit()
    await db.refresh(session)
    return session


async def get_session_with_progress(
    session_id: str,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Fetch session + compute progress summary.

    Returns:
        Dict with session data and progress, or None if not found.
    """
    result = await db.execute(
        select(AuthoringSession)
        .options(selectinload(AuthoringSession.entries))
        .where(AuthoringSession.session_id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        return None

    entries = session.entries
    total_required = sum(1 for e in entries if e.status != "skipped")
    completed = sum(1 for e in entries if e.status in ("complete",))
    # blocking_gaps: required sections not yet complete (not skipped, not complete)
    blocking_gaps = [
        e.section_id
        for e in entries
        if e.status not in ("complete", "skipped")
    ]
    completion_pct = (completed / total_required * 100.0) if total_required > 0 else 0.0

    return {
        "session_id": session.session_id,
        "product_profile_id": session.product_profile_id,
        "pack_id": session.pack_id,
        "status": session.status,
        "created_by": session.created_by,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "progress": {
            "total_required": total_required,
            "completed": completed,
            "blocking_gaps": blocking_gaps,
            "completion_pct": round(completion_pct, 1),
        },
    }
