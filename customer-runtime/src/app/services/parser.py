"""Parser service interface — injectable stub for testing."""
from dataclasses import dataclass
from typing import Any

from app.schemas.parse import ParsedFields


@dataclass
class ParseResult:
    confidence: float
    field_candidates: dict[str, Any]
    required_missing: list[str]


class ParserService:
    """Base parser. Override parse() for real implementations."""

    async def parse(self, file_bytes: bytes, doc_type: str) -> ParseResult:
        raise NotImplementedError


class StubParserService(ParserService):
    """Stub that returns a configurable result — used in tests."""

    def __init__(self, result: ParseResult) -> None:
        self._result = result

    async def parse(self, file_bytes: bytes, doc_type: str) -> ParseResult:
        return self._result


def parsed_fields_to_parse_result(parsed: ParsedFields) -> ParseResult:
    """Map ParsedFields → ParseResult for backward compatibility.

    Args:
        parsed: Output from ParserEngine.

    Returns:
        ParseResult with confidence, field_candidates, required_missing.
    """
    from app.schemas.parse import IFU_FIELD_NAMES

    field_candidates: dict[str, Any] = {}
    required_missing: list[str] = []

    for name in IFU_FIELD_NAMES:
        fe = getattr(parsed, name)
        field_candidates[name] = fe.value
        if fe.value is None:
            required_missing.append(name)

    return ParseResult(
        confidence=parsed.overall_confidence,
        field_candidates=field_candidates,
        required_missing=required_missing,
    )


class EngineParserService(ParserService):
    """Real parser backed by ParserEngine.

    # @MX:NOTE: [AUTO] EngineParserService wraps ParserEngine; ParseResult compat preserved
    """

    def __init__(self, engine: Any | None = None) -> None:
        if engine is None:
            from app.services.parser_engine import ParserEngine
            engine = ParserEngine()
        self._engine = engine

    async def parse(self, file_bytes: bytes, doc_type: str) -> ParseResult:
        parsed: ParsedFields = await self._engine.parse(file_bytes, doc_type)
        return parsed_fields_to_parse_result(parsed)
