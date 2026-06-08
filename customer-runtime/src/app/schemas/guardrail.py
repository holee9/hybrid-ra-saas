"""Guardrail schemas — request/response models for POST /guardrail/run."""
from pydantic import BaseModel, Field


class GuardrailRunRequest(BaseModel):
    product_id: str
    doc_set_ids: list[str]
    rule_set_version: str = "1.0"


class FindingOut(BaseModel):
    finding_id: str
    severity: str
    message: str
    evidence_links: list[str]


class GuardrailRunResponse(BaseModel):
    findings: list[FindingOut]
    run_id: str = Field(..., description="UUID for this guardrail run")
    documents_flagged: list[str] = Field(
        ..., description="doc_ids whose status changed to finding_open"
    )
