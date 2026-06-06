"""Parse job schemas."""
from typing import Any
from pydantic import BaseModel


class ParseJobResponse(BaseModel):
    job_id: str
    status: str
    field_candidates: dict[str, Any] | None = None
    confidence: float | None = None
    required_missing: list[str] | None = None
