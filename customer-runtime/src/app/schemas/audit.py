"""Audit schemas — request/response models for POST /audit/export and /audit/webhook."""
from typing import Any, Literal

from pydantic import BaseModel


class AuditExportRequest(BaseModel):
    scope: Literal["full", "product", "document"] = "full"
    product_id: str | None = None
    date_from: str | None = None  # ISO 8601
    date_to: str | None = None  # ISO 8601
    format: Literal["XLSX", "PDF", "JSON"] = "JSON"


class AuditWebhookRequest(BaseModel):
    event_type: str  # e.g., "regulation.updated", "audit.flagged"
    product_id: str | None = None
    data: dict[str, Any] = {}


class AuditWebhookResponse(BaseModel):
    status: Literal["sent", "skipped"]
    reason: str | None = None
