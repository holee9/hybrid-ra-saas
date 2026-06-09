"""T-006: spacy_ner.py — injectable NER + graceful ImportError degrade 테스트."""
import pytest


EN_IFU_TEXT = """
Device Name: CardioScan Pro 3000
Intended Use: The CardioScan Pro 3000 is intended for cardiac monitoring.
Product Code: CSP-3000-US
Software Version: v2.3.1
"""


def _make_fake_loader(entities: list[tuple[str, str]]):
    """Return a loader function that yields a fake spaCy-like model."""

    class FakeSpan:
        def __init__(self, text: str, label: str):
            self.text = text
            self.label_ = label

    class FakeDoc:
        def __init__(self, text: str):
            self.ents = [FakeSpan(t, l) for t, l in entities]

    class FakeNLP:
        def __call__(self, text: str) -> FakeDoc:
            return FakeDoc(text)

    def loader() -> FakeNLP:
        return FakeNLP()

    return loader


def test_unit_inject_fake_loader_returns_ner_extraction():
    from app.schemas.parse import ExtractionStage
    from app.services.parser_engine.spacy_ner import extract

    fake_loader = _make_fake_loader([
        ("CardioScan Pro 3000", "PRODUCT"),
        ("cardiac monitoring", "CONCEPT"),
    ])
    result = extract(EN_IFU_TEXT, ["device_name", "intended_use"], model_loader=fake_loader)

    assert "device_name" in result
    assert "intended_use" in result
    # With fake NER results, stage should be NER
    for field, fe in result.items():
        assert fe.stage == ExtractionStage.NER
        assert 0.0 <= fe.confidence <= 1.0


def test_unit_import_error_returns_empty_dict():
    """B1: When spaCy is not installed, extract() returns {} gracefully."""
    from app.services.parser_engine.spacy_ner import extract

    def failing_loader():
        raise ImportError("No module named 'spacy'")

    result = extract(EN_IFU_TEXT, ["device_name"], model_loader=failing_loader)
    assert result == {}


def test_unit_runtime_error_returns_empty_dict():
    """Loader runtime error should also degrade gracefully."""
    from app.services.parser_engine.spacy_ner import extract

    def broken_loader():
        raise RuntimeError("Model not found")

    result = extract(EN_IFU_TEXT, ["device_name"], model_loader=broken_loader)
    assert result == {}


def test_unit_empty_fields_list_returns_empty():
    from app.services.parser_engine.spacy_ner import extract

    fake_loader = _make_fake_loader([("CardioScan Pro 3000", "PRODUCT")])
    result = extract(EN_IFU_TEXT, [], model_loader=fake_loader)
    assert result == {}


@pytest.mark.integration
def test_integration_real_spacy_model(skip_no_spacy):
    """Integration test: uses real spaCy model. Skipped if spaCy not installed."""
    from app.services.parser_engine.spacy_ner import extract, default_model_loader

    result = extract(EN_IFU_TEXT, ["device_name", "product_code"], model_loader=default_model_loader)
    # Just verify structure — real model may or may not find entities
    for field, fe in result.items():
        assert 0.0 <= fe.confidence <= 1.0
