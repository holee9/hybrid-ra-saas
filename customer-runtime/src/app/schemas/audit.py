"""Audit schemas — request/response models for POST /audit/export."""
from typing import Literal

from pydantic import BaseModel


class AuditExportRequest(BaseModel):
    scope: Literal["full", "product", "document"] = "full"
    product_id: str | None = None
    date_from: str | None = None  # ISO 8601
    date_to: str | None = None  # ISO 8601
    format: Literal["XLSX", "PDF", "JSON"] = "JSON"
