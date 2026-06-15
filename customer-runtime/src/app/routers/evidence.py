"""Evidence Binder router — SPEC-EVIDENCE-001.

# @MX:NOTE: [AUTO] 9 endpoints; sealed binders reject file/link mutations with 409
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.evidence_binder import EvidenceBinder
from app.models.evidence_gap import EvidenceGap
from app.schemas.evidence import (
    BinderCreate,
    BinderDetailOut,
    BinderOut,
    ExportOut,
    FileOut,
    GapOut,
    LinkCreate,
    LinkOut,
)
from app.services.evidence.binder import (
    BinderSealedError,
    assert_not_sealed,
    create_binder,
    get_binder,
    seal_binder,
)
from app.services.evidence.exporter import export_zip
from app.services.evidence.file_store import FileValidationError, store_evidence_file
from app.services.evidence.gap_engine import evaluate_gaps
from app.services.evidence.linker import create_link, delete_link

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evidence-binders", tags=["evidence"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _get_binder_or_404(binder_id: str, db: AsyncSession) -> EvidenceBinder:
    binder = await get_binder(binder_id, db)
    if binder is None:
        raise HTTPException(status_code=404, detail="Binder not found.")
    return binder


def _gaps_summary(gaps: list[EvidenceGap]) -> dict:
    summary: dict[str, int] = {"critical": 0, "high": 0, "medium": 0}
    for g in gaps:
        if g.severity in summary:
            summary[g.severity] += 1
    return summary


# ---------------------------------------------------------------------------
# 1. POST /evidence-binders → 201
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_evidence_binder(
    body: BinderCreate,
    db: AsyncSession = Depends(get_db),
) -> BinderOut:
    """Create a new evidence binder in draft status."""
    binder = await create_binder(
        product_profile_id=body.product_profile_id,
        name=body.name,
        pack_id=body.pack_id,
        db=db,
    )
    return BinderOut.model_validate(binder)


# ---------------------------------------------------------------------------
# 2. GET /evidence-binders/{binder_id} → 200 (detail + auto gap computation)
# ---------------------------------------------------------------------------


@router.get("/{binder_id}")
async def get_evidence_binder(
    binder_id: str,
    db: AsyncSession = Depends(get_db),
) -> BinderDetailOut:
    """Return binder detail with links, files, and freshly computed gaps."""
    binder = await _get_binder_or_404(binder_id, db)
    gaps = await evaluate_gaps(binder, binder.links, db)
    # Refresh gaps relationship after evaluate_gaps mutated the table
    await db.refresh(binder)
    return BinderDetailOut(
        **BinderOut.model_validate(binder).model_dump(),
        links=[LinkOut.model_validate(lnk) for lnk in binder.links],
        files=[FileOut.model_validate(f) for f in binder.files],
        gaps=[GapOut.model_validate(g) for g in gaps],
        gaps_summary=_gaps_summary(gaps),
    )


# ---------------------------------------------------------------------------
# 3. POST /evidence-binders/{binder_id}/files → 201
# ---------------------------------------------------------------------------


@router.post("/{binder_id}/files", status_code=201)
async def upload_evidence_file(
    binder_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> FileOut:
    """Upload a file to the evidence binder."""
    binder = await _get_binder_or_404(binder_id, db)
    try:
        assert_not_sealed(binder)
    except BinderSealedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    file_bytes = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        evidence_file = await store_evidence_file(
            binder_id=binder_id,
            filename=file.filename or "unknown",
            content_type=content_type,
            file_bytes=file_bytes,
            db=db,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Recompute gaps after mutation
    await db.refresh(binder)
    await evaluate_gaps(binder, binder.links, db)

    return FileOut.model_validate(evidence_file)


# ---------------------------------------------------------------------------
# 4. GET /evidence-binders/{binder_id}/files → 200
# ---------------------------------------------------------------------------


@router.get("/{binder_id}/files")
async def list_evidence_files(
    binder_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[FileOut]:
    """List all files attached to the binder."""
    binder = await _get_binder_or_404(binder_id, db)
    return [FileOut.model_validate(f) for f in binder.files]


# ---------------------------------------------------------------------------
# 5. POST /evidence-binders/{binder_id}/links → 201
# ---------------------------------------------------------------------------


@router.post("/{binder_id}/links", status_code=201)
async def create_evidence_link(
    binder_id: str,
    body: LinkCreate,
    db: AsyncSession = Depends(get_db),
) -> LinkOut:
    """Add an evidence link to the binder."""
    binder = await _get_binder_or_404(binder_id, db)
    try:
        assert_not_sealed(binder)
    except BinderSealedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        link = await create_link(
            binder_id=binder_id,
            source_entity_type=body.source_entity_type,
            source_entity_id=body.source_entity_id,
            target_entity_type=body.target_entity_type,
            target_ref=body.target_ref,
            link_type=body.link_type,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Recompute gaps after mutation
    await db.refresh(binder)
    await evaluate_gaps(binder, binder.links, db)

    return LinkOut.model_validate(link)


# ---------------------------------------------------------------------------
# 6. DELETE /evidence-binders/{binder_id}/links/{link_id} → 204
# ---------------------------------------------------------------------------


@router.delete("/{binder_id}/links/{link_id}", status_code=204)
async def delete_evidence_link(
    binder_id: str,
    link_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove an evidence link from the binder."""
    binder = await _get_binder_or_404(binder_id, db)
    try:
        assert_not_sealed(binder)
    except BinderSealedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    await delete_link(binder_id=binder_id, link_id=link_id, db=db)

    # Recompute gaps after mutation
    await db.refresh(binder)
    await evaluate_gaps(binder, binder.links, db)


# ---------------------------------------------------------------------------
# 7. GET /evidence-binders/{binder_id}/gaps → 200
# ---------------------------------------------------------------------------


@router.get("/{binder_id}/gaps")
async def list_evidence_gaps(
    binder_id: str,
    severity: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[GapOut]:
    """Return computed gaps, optionally filtered by severity."""
    binder = await _get_binder_or_404(binder_id, db)
    gaps = await evaluate_gaps(binder, binder.links, db)

    if severity is not None:
        gaps = [g for g in gaps if g.severity == severity]

    return [GapOut.model_validate(g) for g in gaps]


# ---------------------------------------------------------------------------
# 8. POST /evidence-binders/{binder_id}/seal → 200
# ---------------------------------------------------------------------------


@router.post("/{binder_id}/seal")
async def seal_evidence_binder(
    binder_id: str,
    db: AsyncSession = Depends(get_db),
) -> BinderOut:
    """Seal the binder, making it immutable."""
    # Verify exists
    await _get_binder_or_404(binder_id, db)
    binder = await seal_binder(binder_id=binder_id, db=db)
    return BinderOut.model_validate(binder)


# ---------------------------------------------------------------------------
# 9. POST /evidence-binders/{binder_id}/export → 200
# ---------------------------------------------------------------------------


@router.post("/{binder_id}/export")
async def export_evidence_binder(
    binder_id: str,
    db: AsyncSession = Depends(get_db),
) -> ExportOut:
    """Generate a ZIP export of the binder and return metadata."""
    binder = await _get_binder_or_404(binder_id, db)

    zip_bytes = await export_zip(
        binder=binder,
        links=binder.links,
        files=binder.files,
    )
    filename = f"evidence_binder_{binder_id}.zip"

    return ExportOut(
        binder_id=binder_id,
        filename=filename,
        size_bytes=len(zip_bytes),
    )
