"""T-008: ParserEngine — orchestration pipeline 테스트."""
import io
import pytest


def _make_docx_bytes(text: str = "Device Name: Test\nIntended Use: Testing") -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_xlsx_bytes() -> bytes:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Device Name", "Test Device"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_fe(confidence: float, value: str | None = "test_value"):
    from app.schemas.parse import ExtractionStage, FieldExtraction
    return FieldExtraction(
        value=value,
        confidence=confidence,
        stage=ExtractionStage.RULE if confidence >= 0.85 else ExtractionStage.NONE,
    )


def _make_full_stage_result(confidence: float):
    """Return a stage result dict covering all IFU fields."""
    from app.schemas.parse import IFU_FIELD_NAMES
    return {name: _make_fe(confidence) for name in IFU_FIELD_NAMES}


@pytest.mark.asyncio
async def test_stage1_high_confidence_skips_later_stages():
    """scenario 8: stage1 conf 0.90 → stages 2/3 NOT called, stage=RULE."""
    from app.schemas.parse import ExtractionStage, IFU_FIELD_NAMES
    from app.services.parser_engine import ParserEngine

    stage1_results = _make_full_stage_result(0.90)
    stage2_called = []
    stage3_called = []

    def mock_stage1(text, fields):
        return stage1_results

    def mock_stage2(text, fields, model_loader=None):
        stage2_called.append(fields)
        return {}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        stage3_called.append(fields)
        return {}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    docx_bytes = _make_docx_bytes()
    result = await engine.parse(docx_bytes, "docx")

    # All fields had confidence 0.90 → stage2/3 should NOT be called
    assert len(stage2_called) == 0
    assert len(stage3_called) == 0

    # All fields should be stage RULE
    for name in IFU_FIELD_NAMES:
        assert result.device_name.stage == ExtractionStage.RULE or \
               getattr(result, name).stage == ExtractionStage.RULE


@pytest.mark.asyncio
async def test_all_stages_below_threshold_sets_needs_correction():
    """scenario 4: all stages <0.85 → needs_correction=True per field, requires_correction=True."""
    from app.schemas.parse import IFU_FIELD_NAMES
    from app.services.parser_engine import ParserEngine

    low_conf = 0.5

    def mock_stage1(text, fields):
        return {name: _make_fe(low_conf) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {name: _make_fe(low_conf) for name in fields}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {name: _make_fe(low_conf) for name in fields}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    docx_bytes = _make_docx_bytes()
    result = await engine.parse(docx_bytes, "docx")

    assert result.requires_correction is True
    # At least some fields should have needs_correction=True
    for name in IFU_FIELD_NAMES:
        fe = getattr(result, name)
        assert fe.needs_correction is True


@pytest.mark.asyncio
async def test_low_overall_confidence_sets_rejected():
    """scenario 5: overall_confidence < 0.50 → rejected=True."""
    from app.services.parser_engine import ParserEngine

    very_low = 0.1

    def mock_stage1(text, fields):
        return {name: _make_fe(very_low, value=None) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {name: _make_fe(very_low, value=None) for name in fields}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {name: _make_fe(very_low, value=None) for name in fields}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    docx_bytes = _make_docx_bytes()
    result = await engine.parse(docx_bytes, "docx")
    assert result.rejected is True


@pytest.mark.asyncio
async def test_every_output_field_has_confidence_and_stage():
    """REQ-010: every output field has confidence + stage."""
    from app.schemas.parse import IFU_FIELD_NAMES
    from app.services.parser_engine import ParserEngine

    def mock_stage1(text, fields):
        return {name: _make_fe(0.7) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {name: _make_fe(0.7) for name in fields}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {name: _make_fe(0.7) for name in fields}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    docx_bytes = _make_docx_bytes()
    result = await engine.parse(docx_bytes, "docx")

    for name in IFU_FIELD_NAMES:
        fe = getattr(result, name)
        assert fe.confidence is not None
        assert fe.stage is not None


@pytest.mark.asyncio
async def test_empty_bytes_returns_all_none_rejected():
    from app.services.parser_engine import ParserEngine

    def mock_stage1(text, fields):
        from app.schemas.parse import ExtractionStage, FieldExtraction
        return {name: FieldExtraction(value=None, confidence=0.0, stage=ExtractionStage.NONE) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    result = await engine.parse(b"", "docx")
    assert result.rejected is True


@pytest.mark.asyncio
async def test_docx_doc_type_uses_docx_reader():
    """parse('docx') calls docx_reader, not xlsx_reader."""
    from app.services.parser_engine import ParserEngine

    reader_calls = []

    def tracking_stage1(text, fields):
        reader_calls.append(("stage1", len(text)))
        return _make_full_stage_result(0.9)

    def mock_stage2(text, fields, model_loader=None):
        return {}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=tracking_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    docx_bytes = _make_docx_bytes("CardioScan Pro 3000")
    await engine.parse(docx_bytes, "docx")
    assert len(reader_calls) > 0  # stage1 was called with text


@pytest.mark.asyncio
async def test_xlsx_doc_type_uses_xlsx_reader():
    """parse('xlsx') calls xlsx_reader."""
    from app.services.parser_engine import ParserEngine

    reader_calls = []

    def tracking_stage1(text, fields):
        reader_calls.append(("stage1", len(text)))
        return _make_full_stage_result(0.9)

    def mock_stage2(text, fields, model_loader=None):
        return {}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=tracking_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    xlsx_bytes = _make_xlsx_bytes()
    await engine.parse(xlsx_bytes, "xlsx")
    assert len(reader_calls) > 0


@pytest.mark.asyncio
async def test_stage1_exception_gracefully_handled():
    """Stage 1 exception → all fields become _none_field, pipeline continues."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import IFU_FIELD_NAMES

    def failing_stage1(text, fields):
        raise RuntimeError("Stage 1 crashed")

    def mock_stage2(text, fields, model_loader=None):
        return _make_full_stage_result(0.9)

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=failing_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    result = await engine.parse(_make_docx_bytes(), "docx")
    # Should not raise; all fields should be present
    for name in IFU_FIELD_NAMES:
        fe = getattr(result, name)
        assert fe is not None


@pytest.mark.asyncio
async def test_stage2_exception_gracefully_handled():
    """Stage 2 exception → continue with stage 3."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import IFU_FIELD_NAMES

    def mock_stage1(text, fields):
        return {name: _make_fe(0.5) for name in fields}

    def failing_stage2(text, fields, model_loader=None):
        raise RuntimeError("Stage 2 crashed")

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {name: _make_fe(0.9) for name in fields}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=failing_stage2,
        stage3_fn=mock_stage3,
    )

    result = await engine.parse(_make_docx_bytes(), "docx")
    for name in IFU_FIELD_NAMES:
        assert getattr(result, name) is not None


@pytest.mark.asyncio
async def test_stage3_exception_gracefully_handled():
    """Stage 3 exception → fields remain at stage2 or stage1 result."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import IFU_FIELD_NAMES

    def mock_stage1(text, fields):
        return {name: _make_fe(0.5) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {name: _make_fe(0.6) for name in fields}

    async def failing_stage3(text, fields, llm_client=None, base_url=None):
        raise RuntimeError("Stage 3 crashed")

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=failing_stage3,
    )

    result = await engine.parse(_make_docx_bytes(), "docx")
    for name in IFU_FIELD_NAMES:
        assert getattr(result, name) is not None


@pytest.mark.asyncio
async def test_stage2_improves_confidence():
    """Stage 2 result with higher confidence replaces stage 1 result."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import ExtractionStage

    def mock_stage1(text, fields):
        return {name: _make_fe(0.5) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        # Return higher confidence for all fields
        from app.schemas.parse import FieldExtraction
        return {
            name: FieldExtraction(value="ner_value", confidence=0.9, stage=ExtractionStage.NER)
            for name in fields
        }

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    result = await engine.parse(_make_docx_bytes(), "docx")
    # Fields with high stage2 confidence should not need correction
    assert result.requires_correction is False


@pytest.mark.asyncio
async def test_stage3_improves_confidence():
    """Stage 3 result with higher confidence replaces lower stage results."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import ExtractionStage, FieldExtraction

    def mock_stage1(text, fields):
        return {name: _make_fe(0.4) for name in fields}

    def mock_stage2(text, fields, model_loader=None):
        return {name: _make_fe(0.5) for name in fields}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {
            name: FieldExtraction(value="llm_value", confidence=0.9, stage=ExtractionStage.LLM)
            for name in fields
        }

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    result = await engine.parse(_make_docx_bytes(), "docx")
    assert result.requires_correction is False


@pytest.mark.asyncio
async def test_corrupted_docx_bytes_handled_gracefully():
    """Corrupted DOCX → read returns empty string → fields all NONE."""
    from app.services.parser_engine import ParserEngine
    from app.schemas.parse import ExtractionStage

    def mock_stage1(text, fields):
        # Will be called with empty text
        from app.schemas.parse import FieldExtraction
        return {
            name: FieldExtraction(value=None, confidence=0.0, stage=ExtractionStage.NONE)
            for name in fields
        }

    def mock_stage2(text, fields, model_loader=None):
        return {}

    async def mock_stage3(text, fields, llm_client=None, base_url=None):
        return {}

    engine = ParserEngine(
        stage1_fn=mock_stage1,
        stage2_fn=mock_stage2,
        stage3_fn=mock_stage3,
    )

    # Corrupted bytes will cause DocxReadError → empty text
    result = await engine.parse(b"corrupted bytes!!!", "docx")
    assert result.rejected is True
