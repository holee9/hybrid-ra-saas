"""parser_engine — 15-field IFU extraction engine.

Public API: ParserEngine only.
"""
import logging
from typing import Any, Callable, Coroutine

from app.schemas.parse import (
    ExtractionStage,
    FieldExtraction,
    IFU_FIELD_NAMES,
    ParsedFields,
)
from app.services.parser_engine import confidence as _confidence_module
from app.services.parser_engine.docx_reader import read_docx
from app.services.parser_engine.errors import DocxReadError, XlsxReadError
from app.services.parser_engine.xlsx_reader import read_xlsx

logger = logging.getLogger(__name__)

# Type aliases for injectable stage functions
_SyncStageFn = Callable[[str, list[str]], dict[str, FieldExtraction]]
_AsyncStageFn = Callable[
    [str, list[str]],
    Coroutine[Any, Any, dict[str, FieldExtraction]],
]


def _default_stage1(text: str, fields: list[str]) -> dict[str, FieldExtraction]:
    from app.services.parser_engine.rule_based import extract
    return extract(text, fields)


def _default_stage2(
    text: str,
    fields: list[str],
    model_loader: Any = None,
) -> dict[str, FieldExtraction]:
    from app.services.parser_engine.spacy_ner import extract
    return extract(text, fields, model_loader=model_loader)


async def _default_stage3(
    text: str,
    fields: list[str],
    llm_client: Any = None,
    base_url: str = "http://localhost:11434",
) -> dict[str, FieldExtraction]:
    from app.services.parser_engine.llm_fallback import extract
    return await extract(text, fields, llm_client=llm_client, base_url=base_url)


def _none_field() -> FieldExtraction:
    return FieldExtraction(value=None, confidence=0.0, stage=ExtractionStage.NONE)


class ParserEngine:
    """Orchestrates the 3-stage IFU field extraction pipeline.

    Stages run per-field with early exit at confidence >= CORRECTION_UI_THRESHOLD.
    Injection of stage functions enables unit testing without real models.
    """

    # @MX:ANCHOR: [AUTO] ParserEngine.parse — central pipeline seam, fan_in >= 3
    # @MX:REASON: Called by EngineParserService, integration tests, and direct callers

    def __init__(
        self,
        stage1_fn: _SyncStageFn | None = None,
        stage2_fn: Any | None = None,
        stage3_fn: Any | None = None,
        correction_threshold: float | None = None,
        reject_threshold: float | None = None,
    ) -> None:
        self._stage1 = stage1_fn if stage1_fn is not None else _default_stage1
        self._stage2 = stage2_fn if stage2_fn is not None else _default_stage2
        self._stage3 = stage3_fn if stage3_fn is not None else _default_stage3
        self._correction_threshold = (
            correction_threshold
            if correction_threshold is not None
            else _confidence_module.CORRECTION_UI_THRESHOLD
        )
        self._reject_threshold = (
            reject_threshold
            if reject_threshold is not None
            else _confidence_module.REJECT_THRESHOLD
        )

    async def parse(self, file_bytes: bytes, doc_type: str) -> ParsedFields:
        """Run the 3-stage pipeline and return ParsedFields.

        Args:
            file_bytes: Raw document bytes.
            doc_type: One of 'docx' or 'xlsx'.

        Returns:
            ParsedFields with per-field extractions and aggregate scores.
        """
        # Read text from document
        text = self._read_text(file_bytes, doc_type)

        # Per-field pipeline
        field_results: dict[str, FieldExtraction] = {}
        threshold = self._correction_threshold

        # Stage 1 — batch all fields
        remaining = list(IFU_FIELD_NAMES)
        try:
            s1_results = self._stage1(text, remaining)
        except Exception as exc:
            logger.warning("Stage 1 failed: %s", exc)
            s1_results = {}

        for field in remaining[:]:
            fe = s1_results.get(field, _none_field())
            field_results[field] = fe

        # Stage 2 — fields below threshold
        needs_stage2 = [f for f in remaining if field_results[f].confidence < threshold]
        if needs_stage2:
            try:
                s2_results = self._stage2(text, needs_stage2)
            except Exception as exc:
                logger.warning("Stage 2 failed: %s", exc)
                s2_results = {}

            for field in needs_stage2:
                fe = s2_results.get(field)
                if fe is not None and fe.confidence > field_results[field].confidence:
                    field_results[field] = fe

        # Stage 3 — fields still below threshold
        needs_stage3 = [f for f in remaining if field_results[f].confidence < threshold]
        if needs_stage3:
            try:
                s3_results = await self._stage3(text, needs_stage3)
            except Exception as exc:
                logger.warning("Stage 3 failed: %s", exc)
                s3_results = {}

            for field in needs_stage3:
                fe = s3_results.get(field)
                if fe is not None and fe.confidence > field_results[field].confidence:
                    field_results[field] = fe

        # Mark fields still below threshold as needing correction
        for field in IFU_FIELD_NAMES:
            fe = field_results.get(field, _none_field())
            if fe.confidence < threshold:
                field_results[field] = FieldExtraction(
                    value=fe.value,
                    confidence=fe.confidence,
                    stage=fe.stage,
                    needs_correction=True,
                )

        # Ensure all fields present
        for field in IFU_FIELD_NAMES:
            if field not in field_results:
                field_results[field] = _none_field()

        # Build ParsedFields
        requires_correction = any(
            field_results[f].needs_correction for f in IFU_FIELD_NAMES
        )
        parsed = ParsedFields(
            overall_confidence=0.0,  # Placeholder — recalculated below
            requires_correction=requires_correction,
            **field_results,
        )
        overall_conf = _confidence_module.overall(parsed)
        rejected = overall_conf < self._reject_threshold

        return ParsedFields(
            overall_confidence=overall_conf,
            requires_correction=requires_correction,
            rejected=rejected,
            **field_results,
        )

    def _read_text(self, file_bytes: bytes, doc_type: str) -> str:
        """Dispatch to the correct reader based on doc_type."""
        if not file_bytes:
            return ""
        try:
            if doc_type == "xlsx":
                return read_xlsx(file_bytes)
            return read_docx(file_bytes)
        except (DocxReadError, XlsxReadError) as exc:
            logger.warning("Document read failed (%s): %s", doc_type, exc)
            return ""
        except Exception as exc:
            logger.warning("Unexpected read error: %s", exc)
            return ""


__all__ = ["ParserEngine"]
