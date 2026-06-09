"""Parse job schemas — IFU 15-field extraction models."""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# @MX:ANCHOR: [AUTO] IFU 15-field canonical list — single source of truth
# @MX:REASON: 3+ callers: rule_based, CorrectionsRequest whitelist, ParsedFields model
IFU_FIELD_NAMES: tuple[str, ...] = (
    "device_name",
    "intended_use",
    "indications",
    "contraindications",
    "warnings",
    "device_classification",
    "region_targets",
    "cybersecurity_requirements",
    "precautions",
    "product_code",
    "maintenance_interval",
    "cleaning_disinfection",
    "software_version",
    "accessories",
    "disposal_instructions",
)

# Required fields for overall confidence calculation (8 fields)
_REQUIRED_FIELDS: frozenset[str] = frozenset({
    "device_name",
    "intended_use",
    "indications",
    "contraindications",
    "warnings",
    "device_classification",
    "region_targets",
    "cybersecurity_requirements",
})


class ExtractionStage(str, Enum):
    RULE = "rule_based"
    NER = "spacy_ner"
    LLM = "llm_fallback"
    NONE = "none"


class FieldExtraction(BaseModel):
    value: str | list[str] | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    stage: ExtractionStage
    needs_correction: bool = False


class ParsedFields(BaseModel):
    device_name: FieldExtraction
    intended_use: FieldExtraction
    indications: FieldExtraction
    contraindications: FieldExtraction
    warnings: FieldExtraction
    device_classification: FieldExtraction
    region_targets: FieldExtraction
    cybersecurity_requirements: FieldExtraction
    precautions: FieldExtraction
    product_code: FieldExtraction
    maintenance_interval: FieldExtraction
    cleaning_disinfection: FieldExtraction
    software_version: FieldExtraction
    accessories: FieldExtraction
    disposal_instructions: FieldExtraction
    overall_confidence: float = Field(ge=0.0, le=1.0)
    requires_correction: bool = False
    rejected: bool = False


class ParseJobResponse(BaseModel):
    job_id: str
    status: str
    field_candidates: dict[str, Any] | None = None
    confidence: float | None = None
    required_missing: list[str] | None = None
    parsed_fields: ParsedFields | None = None


class CorrectionsRequest(BaseModel):
    """Request body for PATCH /parse/{job_id}/corrections.

    Only IFU_FIELD_NAMES keys are allowed.
    """

    corrections: dict[str, str]

    @model_validator(mode="after")
    def validate_field_names(self) -> "CorrectionsRequest":
        invalid = set(self.corrections.keys()) - set(IFU_FIELD_NAMES)
        if invalid:
            raise ValueError(
                f"Unknown field(s): {invalid}. Allowed: {list(IFU_FIELD_NAMES)}"
            )
        return self
