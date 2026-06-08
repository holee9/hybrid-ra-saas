"""POST /audit/export router — REQ-API-010."""
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_tenant, get_db
from app.schemas.audit import AuditExportRequest
from app.services.audit import AuditService
from app.services.export import ExportService

router = APIRouter(prefix="/audit", tags=["audit"])

_audit_service = AuditService()
_export_service = ExportService()


@router.post("/export")
async def audit_export(
    payload: AuditExportRequest,
    tenant: str = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Generate binary audit export (XLSX/PDF/JSON) and stream to client.

    REQ-API-010: includes operator, timestamp, evidence, change_history.
    """
    result = await _export_service.export(
        db=db,
        tenant_id=tenant,
        user_id="system",
        scope=payload.scope,
        product_id=payload.product_id,
        date_from=payload.date_from,
        date_to=payload.date_to,
        format=payload.format,
        audit_service=_audit_service,
    )

    return StreamingResponse(
        io.BytesIO(result["content"]),
        media_type=result["media_type"],
        headers={
            "Content-Disposition": f'attachment; filename="{result["filename"]}"',
        },
    )
