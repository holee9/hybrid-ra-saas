"""T-004: xlsx_reader.py — read_xlsx() 테스트."""
import io
import pytest


def _make_xlsx_bytes(data: list[list] | None = None) -> bytes:
    """Create a minimal valid XLSX in memory using openpyxl."""
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    if data is None:
        data = [["Device Name", "Test Device"], ["Intended Use", "Testing purposes"]]
    for row in data:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_read_xlsx_returns_nonempty_string():
    from app.services.parser_engine.xlsx_reader import read_xlsx

    xlsx_bytes = _make_xlsx_bytes()
    result = read_xlsx(xlsx_bytes)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Test Device" in result


def test_read_xlsx_corrupted_bytes_raises_xlsx_read_error():
    from app.services.parser_engine.xlsx_reader import read_xlsx
    from app.services.parser_engine.errors import XlsxReadError

    with pytest.raises(XlsxReadError):
        read_xlsx(b"not a valid xlsx file!!!")


def test_read_xlsx_multiple_rows():
    from app.services.parser_engine.xlsx_reader import read_xlsx

    data = [["field1", "value1"], ["field2", "value2"], ["field3", "value3"]]
    xlsx_bytes = _make_xlsx_bytes(data)
    result = read_xlsx(xlsx_bytes)
    assert "value1" in result
    assert "value3" in result


def test_read_xlsx_empty_returns_string():
    from app.services.parser_engine.xlsx_reader import read_xlsx

    xlsx_bytes = _make_xlsx_bytes([])
    result = read_xlsx(xlsx_bytes)
    assert isinstance(result, str)
