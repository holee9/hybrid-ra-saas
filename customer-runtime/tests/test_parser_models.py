"""T-001: ExtractionStage, FieldExtraction, ParsedFields, IFU_FIELD_NAMES 모델 테스트."""
import pytest
from pydantic import ValidationError


def test_extraction_stage_has_all_values():
    from app.schemas.parse import ExtractionStage

    assert ExtractionStage.RULE == "rule_based"
    assert ExtractionStage.NER == "spacy_ner"
    assert ExtractionStage.LLM == "llm_fallback"
    assert ExtractionStage.NONE == "none"


def test_field_extraction_rejects_confidence_above_one():
    from app.schemas.parse import ExtractionStage, FieldExtraction

    with pytest.raises(ValidationError):
        FieldExtraction(value="test", confidence=1.1, stage=ExtractionStage.RULE)


def test_field_extraction_rejects_confidence_below_zero():
    from app.schemas.parse import ExtractionStage, FieldExtraction

    with pytest.raises(ValidationError):
        FieldExtraction(value="test", confidence=-0.1, stage=ExtractionStage.RULE)


def test_field_extraction_valid():
    from app.schemas.parse import ExtractionStage, FieldExtraction

    fe = FieldExtraction(value="X-ray Model A", confidence=0.9, stage=ExtractionStage.RULE)
    assert fe.value == "X-ray Model A"
    assert fe.confidence == 0.9
    assert fe.stage == ExtractionStage.RULE
    assert fe.needs_correction is False


def test_ifu_field_names_has_exactly_15_entries():
    from app.schemas.parse import IFU_FIELD_NAMES

    assert len(IFU_FIELD_NAMES) == 15


def test_ifu_field_names_contains_required_fields():
    from app.schemas.parse import IFU_FIELD_NAMES

    required = {
        "device_name", "intended_use", "indications", "contraindications",
        "warnings", "device_classification", "region_targets",
        "cybersecurity_requirements", "precautions", "product_code",
        "maintenance_interval", "cleaning_disinfection", "software_version",
        "accessories", "disposal_instructions",
    }
    assert set(IFU_FIELD_NAMES) == required


def _make_field_extraction(confidence: float = 0.5):
    from app.schemas.parse import ExtractionStage, FieldExtraction
    return FieldExtraction(value=None, confidence=confidence, stage=ExtractionStage.NONE)


def test_parsed_fields_requires_all_15_fields():
    from app.schemas.parse import ParsedFields

    with pytest.raises((ValidationError, TypeError)):
        ParsedFields(overall_confidence=0.5)  # missing all fields


def test_parsed_fields_valid():
    from app.schemas.parse import IFU_FIELD_NAMES, ParsedFields

    fe = _make_field_extraction(0.7)
    kwargs = {name: fe for name in IFU_FIELD_NAMES}
    pf = ParsedFields(overall_confidence=0.7, **kwargs)
    assert pf.overall_confidence == 0.7
    assert pf.requires_correction is False
    assert pf.rejected is False


def test_parse_job_response_still_works():
    """ParseJobResponse backward compat check."""
    from app.schemas.parse import ParseJobResponse

    r = ParseJobResponse(job_id="abc", status="done")
    assert r.job_id == "abc"
    assert r.status == "done"
    assert r.field_candidates is None
    assert r.parsed_fields is None
