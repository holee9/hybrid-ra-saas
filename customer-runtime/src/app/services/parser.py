"""Parser service interface — injectable stub for testing."""
from dataclasses import dataclass
from typing import Any


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
