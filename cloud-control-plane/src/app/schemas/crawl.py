"""Pydantic schemas for crawl trigger and status API (T-017, REQ-011/012)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class TriggerResponse(BaseModel):
    """Response body for POST /crawl/trigger."""

    job_id: str


class JobStatusResponse(BaseModel):
    """Response body for GET /crawl/status/{job_id}."""

    job_id: str
    status: str
    document_count: Optional[int] = None
    skipped_count: Optional[int] = None
    failed_count: Optional[int] = None
