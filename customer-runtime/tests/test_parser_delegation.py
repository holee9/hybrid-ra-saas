"""T-009: EngineParserService delegation + compat 테스트."""
import io
import pytest
from unittest.mock import AsyncMock, MagicMock


def _make_docx_bytes(text: str = "Device Name: Test") -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_parsed_fields(overall_confidence: float = 0.75):
    from app.schemas.parse import ExtractionStage, FieldExtraction, IFU_FIELD_NAMES, ParsedFields
    fe = FieldExtraction(value="test", confidence=overall_confidence, stage=ExtractionStage.RULE)
    kwargs = {name: fe for name in IFU_FIELD_NAMES}
    return ParsedFields(overall_confidence=overall_confidence, **kwargs)


@pytest.mark.asyncio
async def test_engine_parser_service_returns_parse_result():
    from app.services.parser import EngineParserService

    mock_engine = MagicMock()
    mock_engine.parse = AsyncMock(return_value=_make_parsed_fields(0.75))

    service = EngineParserService(engine=mock_engine)
    docx_bytes = _make_docx_bytes()
    result = await service.parse(docx_bytes, "docx")

    from app.services.parser import ParseResult
    assert isinstance(result, ParseResult)


@pytest.mark.asyncio
async def test_engine_parser_service_confidence_matches():
    from app.services.parser import EngineParserService

    parsed = _make_parsed_fields(0.82)
    mock_engine = MagicMock()
    mock_engine.parse = AsyncMock(return_value=parsed)

    service = EngineParserService(engine=mock_engine)
    result = await service.parse(b"fake", "docx")

    assert result.confidence == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_engine_parser_service_field_candidates_contains_all_fields():
    from app.schemas.parse import IFU_FIELD_NAMES
    from app.services.parser import EngineParserService

    parsed = _make_parsed_fields(0.7)
    mock_engine = MagicMock()
    mock_engine.parse = AsyncMock(return_value=parsed)

    service = EngineParserService(engine=mock_engine)
    result = await service.parse(b"fake", "docx")

    for name in IFU_FIELD_NAMES:
        assert name in result.field_candidates


def test_stub_parser_service_still_importable_and_works():
    """Backward compat: StubParserService must still work."""
    from app.services.parser import ParseResult, StubParserService

    stub_result = ParseResult(
        confidence=0.9,
        field_candidates={"device_name": "Test"},
        required_missing=[],
    )
    stub = StubParserService(result=stub_result)
    assert stub._result is stub_result


@pytest.mark.asyncio
async def test_stub_parser_service_returns_configured_result():
    from app.services.parser import ParseResult, StubParserService

    expected = ParseResult(
        confidence=0.5,
        field_candidates={"device_name": "X"},
        required_missing=["indications"],
    )
    stub = StubParserService(result=expected)
    result = await stub.parse(b"bytes", "docx")
    assert result is expected


def test_parse_result_dataclass_is_unchanged():
    """ParseResult dataclass signature must remain stable."""
    from app.services.parser import ParseResult
    import dataclasses

    fields = {f.name for f in dataclasses.fields(ParseResult)}
    assert "confidence" in fields
    assert "field_candidates" in fields
    assert "required_missing" in fields
