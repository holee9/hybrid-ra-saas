"""T-002: confidence.py — calculate(), THRESHOLDS, overall() 테스트."""
import pytest


def test_calculate_weighted_formula():
    from app.services.parser_engine.confidence import calculate

    # 0.50*0.8 + 0.30*0.9 + 0.20*0.7 = 0.40+0.27+0.14 = 0.81
    result = calculate(field_completeness=0.8, rule_match=0.9, semantic_similarity=0.7)
    assert result == pytest.approx(0.81, abs=1e-9)


def test_calculate_all_zero():
    from app.services.parser_engine.confidence import calculate

    assert calculate(0.0, 0.0, 0.0) == pytest.approx(0.0)


def test_calculate_all_one():
    from app.services.parser_engine.confidence import calculate

    assert calculate(1.0, 1.0, 1.0) == pytest.approx(1.0)


def test_correction_ui_threshold_default():
    from app.services.parser_engine.confidence import CORRECTION_UI_THRESHOLD

    assert CORRECTION_UI_THRESHOLD == pytest.approx(0.85)


def test_reject_threshold_default():
    from app.services.parser_engine.confidence import REJECT_THRESHOLD

    assert REJECT_THRESHOLD == pytest.approx(0.50)


def test_correction_ui_threshold_env_override(monkeypatch):
    monkeypatch.setenv("PARSER_CORRECTION_THRESHOLD", "0.90")
    # Re-import to pick up the env override
    import importlib
    import app.services.parser_engine.confidence as conf_module
    importlib.reload(conf_module)
    assert conf_module.CORRECTION_UI_THRESHOLD == pytest.approx(0.90)
    # Restore
    monkeypatch.delenv("PARSER_CORRECTION_THRESHOLD", raising=False)
    importlib.reload(conf_module)


def test_reject_threshold_env_override(monkeypatch):
    monkeypatch.setenv("PARSER_REJECT_THRESHOLD", "0.40")
    import importlib
    import app.services.parser_engine.confidence as conf_module
    importlib.reload(conf_module)
    assert conf_module.REJECT_THRESHOLD == pytest.approx(0.40)
    monkeypatch.delenv("PARSER_REJECT_THRESHOLD", raising=False)
    importlib.reload(conf_module)


def test_overall_returns_weighted_average_over_required_fields():
    """overall() uses only the required fields for confidence calculation."""
    from app.schemas.parse import ExtractionStage, FieldExtraction, IFU_FIELD_NAMES, ParsedFields
    from app.services.parser_engine.confidence import overall

    fe_high = FieldExtraction(value="x", confidence=1.0, stage=ExtractionStage.RULE)
    fe_low = FieldExtraction(value=None, confidence=0.0, stage=ExtractionStage.NONE)

    # Build ParsedFields with all required fields = 1.0, optional = 0.0
    required_fields = {
        "device_name", "intended_use", "indications", "contraindications",
        "warnings", "device_classification", "region_targets",
        "cybersecurity_requirements",
    }
    kwargs: dict = {}
    for name in IFU_FIELD_NAMES:
        kwargs[name] = fe_high if name in required_fields else fe_low

    pf = ParsedFields(overall_confidence=0.5, **kwargs)
    score = overall(pf)
    # All 8 required fields at 1.0 → overall should be 1.0
    assert score == pytest.approx(1.0)


def test_overall_mixed_required_fields():
    from app.schemas.parse import ExtractionStage, FieldExtraction, IFU_FIELD_NAMES, ParsedFields
    from app.services.parser_engine.confidence import overall

    required_fields = {
        "device_name", "intended_use", "indications", "contraindications",
        "warnings", "device_classification", "region_targets",
        "cybersecurity_requirements",
    }
    # Half required at 1.0, half at 0.0
    sorted_req = sorted(required_fields)
    half = len(sorted_req) // 2  # 4

    kwargs: dict = {}
    for name in IFU_FIELD_NAMES:
        if name in sorted_req[:half]:
            kwargs[name] = FieldExtraction(value="x", confidence=1.0, stage=ExtractionStage.RULE)
        else:
            kwargs[name] = FieldExtraction(value=None, confidence=0.0, stage=ExtractionStage.NONE)

    pf = ParsedFields(overall_confidence=0.5, **kwargs)
    score = overall(pf)
    # 4/8 required at 1.0, 4/8 at 0.0 → average ~0.5
    assert score == pytest.approx(0.5, abs=0.01)
