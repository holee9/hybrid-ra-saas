"""POST /audit/export and /audit/webhook routers — REQ-API-010, GAP-06."""
import io

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.security import verify_hybrid_bearer_token
from app.deps import get_current_tenant, get_db
from app.schemas.audit import AuditExportRequest, AuditWebhookRequest, AuditWebhookResponse
from app.services.audit import AuditService
from app.services.export import ExportService

router = APIRouter(prefix="/audit", tags=["audit"])

_audit_service = AuditService()
_export_service = ExportService()


@router.post("/export")
async def audit_export(
    payload: AuditExportRequest,
    tenant: str = Depends(verify_hybrid_bearer_token),
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


@router.post("/webhook", response_model=AuditWebhookResponse, status_code=202)
async def audit_webhook(
    payload: AuditWebhookRequest,
    tenant: str = Depends(get_current_tenant),
):
    """Push an audit event to Regula (ra-med-bot) webhook URL.

    # @MX:ANCHOR: [AUTO] Outbound audit event push to Regula SaaS (GAP-06).
    # @MX:REASON: External integration boundary; REGULA_AUDIT_WEBHOOK_URL must be set in production.

    If REGULA_AUDIT_WEBHOOK_URL is not configured, returns 202 with status=skipped (no-op).
    """
    settings = Settings()
    webhook_url = settings.regula_audit_webhook_url
    if not webhook_url:
        return AuditWebhookResponse(status="skipped", reason="REGULA_AUDIT_WEBHOOK_URL not configured")

    headers: dict[str, str] = {}
    if settings.regula_api_key:
        headers["X-Regula-API-Key"] = settings.regula_api_key

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                webhook_url,
                json={
                    "tenant_id": tenant,
                    "event_type": payload.event_type,
                    "product_id": payload.product_id,
                    "data": payload.data,
                },
                headers=headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Webhook delivery failed: HTTP {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Webhook request error: {exc}")

    return AuditWebhookResponse(status="sent")
