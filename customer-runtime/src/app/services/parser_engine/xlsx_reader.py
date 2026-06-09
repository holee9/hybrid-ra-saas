"""XLSX → plain text extraction."""
import io

from app.services.parser_engine.docx_reader import _normalize_text
from app.services.parser_engine.errors import XlsxReadError


def read_xlsx(file_bytes: bytes) -> str:
    """Extract plain text from XLSX bytes.

    Args:
        file_bytes: Raw bytes of an XLSX file.

    Returns:
        Normalized plain text content (cells tab-separated, rows newline-separated).

    Raises:
        XlsxReadError: When the bytes cannot be parsed as XLSX.
    """
    try:
        import openpyxl  # type: ignore[import-untyped]
    except ImportError as exc:
        raise XlsxReadError(f"openpyxl not installed: {exc}") from exc

    try:
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        lines: list[str] = []
        for sheet in wb.worksheets:
            for row in sheet.iter_rows(values_only=True):
                cells = [str(cell) if cell is not None else "" for cell in row]
                lines.append("\t".join(cells))
        return _normalize_text("\n".join(lines))
    except Exception as exc:
        raise XlsxReadError(f"Failed to read XLSX: {exc}") from exc
