"""DOCX → plain text extraction."""
import io

from app.services.parser_engine.errors import DocxReadError, InputTooLargeError

# 50 MB limit
_MAX_BYTES: int = 50 * 1024 * 1024


def _normalize_text(text: str) -> str:
    """Strip excess whitespace while preserving newline structure."""
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def read_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes.

    Args:
        file_bytes: Raw bytes of a DOCX file.

    Returns:
        Normalized plain text content.

    Raises:
        InputTooLargeError: When file_bytes exceeds _MAX_BYTES.
        DocxReadError: When the bytes cannot be parsed as DOCX.
    """
    if len(file_bytes) > _MAX_BYTES:
        raise InputTooLargeError(
            f"Input size {len(file_bytes)} bytes exceeds limit {_MAX_BYTES} bytes"
        )

    try:
        from docx import Document  # type: ignore[import-untyped]
        from docx.opc.exceptions import PackageNotFoundError  # type: ignore[import-untyped]
    except ImportError as exc:
        raise DocxReadError(f"python-docx not installed: {exc}") from exc

    try:
        doc = Document(io.BytesIO(file_bytes))
        raw_text = "\n".join(para.text for para in doc.paragraphs)
        return _normalize_text(raw_text)
    except PackageNotFoundError as exc:
        raise DocxReadError(f"Invalid DOCX format: {exc}") from exc
    except Exception as exc:
        raise DocxReadError(f"Failed to read DOCX: {exc}") from exc
