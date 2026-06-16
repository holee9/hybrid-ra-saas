"""Sync router — REQ-API-012: GET /sync/manifest.

# @MX:NOTE: [AUTO] get_tenant_id is the rate-limit key — see app.core.ratelimit
"""
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_hybrid_bearer_token
from app.deps import get_db
from app.schemas.sync import ManifestResponse
from app.services.airgap import AirGapService
from app.services.sync import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])

_sync_service = SyncService()
_airgap_service = AirGapService()


@router.get("/manifest", response_model=ManifestResponse)
async def get_sync_manifest(
    since: str | None = Query(
        default=None,
        description="ISO 8601 timestamp; return only entities updated after this time",
    ),
    tenant: str = Depends(verify_hybrid_bearer_token),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return delta manifest for cloud sync (REQ-API-012).

    Manifest MUST NOT contain customer document content or sensitive data (FR-210).
    """
    manifest = await _sync_service.build_manifest(
        db=db,
        tenant_id=tenant,
        since=since,
    )

    # Air-gap validation: raise AirGapViolation if sensitive data detected (FR-210)
    _airgap_service.validate_outbound(manifest)

    return manifest
