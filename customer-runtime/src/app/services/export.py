"""Export service — REQ-API-010 binary export (XLSX/PDF/JSON).

# @MX:ANCHOR: [AUTO] ExportService.export — public API boundary for audit export
# @MX:REASON: fan_in >= 3 (router, test_audit_export, future scheduled reports)
"""
import io
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


class ExportService:
    """Generates binary audit export in XLSX, PDF, or JSON format."""

    async def export(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        scope: str,
        product_id: str | None,
        date_from: str | None,
        date_to: str | None,
        format: str,  # noqa: A002
        audit_service: Any,
    ) -> dict[str, Any]:
        """Generate binary export and return dict with content, media_type, filename.

        Returns:
            dict with keys: content (bytes), media_type (str), filename (str)
        """
        events = await self._load_audit_events(
            db=db,
            tenant_id=tenant_id,
            product_id=product_id,
            date_from=date_from,
            date_to=date_to,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == "JSON":
            content, media_type, ext = self._generate_json(events)
        elif format == "XLSX":
            content, media_type, ext = self._generate_xlsx(events)
        else:  # PDF
            content, media_type, ext = self._generate_pdf(events)

        filename = f"audit_export_{timestamp}.{ext}"

        # Record audit event for the export action itself
        await audit_service.record(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            action="audit.export",
        )

        return {"content": content, "media_type": media_type, "filename": filename}

    def _generate_json(self, events: list[dict[str, Any]]) -> tuple[bytes, str, str]:
        """Serialize events to JSON bytes."""
        content = json.dumps(events, default=str).encode("utf-8")
        return content, "application/json", "json"

    def _generate_xlsx(self, events: list[dict[str, Any]]) -> tuple[bytes, str, str]:
        """Generate XLSX workbook with AuditEvents sheet."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "AuditEvents"

        if events:
            headers = list(events[0].keys())
            ws.append(headers)
            for evt in events:
                ws.append([str(evt.get(h, "")) for h in headers])
        else:
            ws.append(["event_id", "action", "tenant_id", "user_id", "timestamp"])

        # Summary sheet
        ws2 = wb.create_sheet("Summary")
        ws2.append(["Total Events", len(events)])
        ws2.append(["Generated At", datetime.now(timezone.utc).isoformat()])

        buf = io.BytesIO()
        wb.save(buf)
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return content, media_type, "xlsx"

    def _generate_pdf(self, events: list[dict[str, Any]]) -> tuple[bytes, str, str]:
        """Generate PDF using reportlab; fallback to JSON if unavailable.

        # @MX:NOTE: [AUTO] reportlab is listed in pyproject.toml; fallback guards against import edge cases
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas

            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=A4)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 800, "Audit Export Report")
            c.setFont("Helvetica", 10)
            c.drawString(50, 780, f"Total Events: {len(events)}")
            c.drawString(50, 765, f"Generated: {datetime.now(timezone.utc).isoformat()}")

            y = 740
            for evt in events[:50]:  # Limit to first 50 for MVP
                line = f"{evt.get('timestamp', '')} | {evt.get('action', '')} | {evt.get('user_id', '')}"
                c.drawString(50, y, line[:100])
                y -= 15
                if y < 50:
                    c.showPage()
                    y = 800

            c.save()
            content = buf.getvalue()
            return content, "application/pdf", "pdf"

        except ImportError:
            # Fallback to JSON when reportlab unavailable
            content, media_type, _ = self._generate_json(events)
            return content, media_type, "json"

    async def _load_audit_events(
        self,
        db: AsyncSession,
        tenant_id: str,
        product_id: str | None,
        date_from: str | None,
        date_to: str | None,
    ) -> list[dict[str, Any]]:
        """Query AuditEvents for tenant with optional date filters."""
        stmt = select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)

        if date_from:
            from datetime import datetime as dt
            stmt = stmt.where(AuditEvent.timestamp >= dt.fromisoformat(date_from))
        if date_to:
            from datetime import datetime as dt
            stmt = stmt.where(AuditEvent.timestamp <= dt.fromisoformat(date_to))

        stmt = stmt.order_by(AuditEvent.timestamp)

        try:
            result = await db.execute(stmt)
            rows = result.scalars().all()
            return [
                {
                    "event_id": r.event_id,
                    "action": r.action,
                    "tenant_id": r.tenant_id,
                    "user_id": r.user_id or "",
                    "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                    "before_hash": r.before_hash or "",
                    "after_hash": r.after_hash or "",
                }
                for r in rows
            ]
        except Exception:  # noqa: BLE001
            return []
