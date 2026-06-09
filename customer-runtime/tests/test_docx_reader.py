"""T-003: docx_reader.py — read_docx() 테스트."""
import io
import pytest


def _make_docx_bytes(text: str = "Device Name: Test Device\nIntended Use: Testing") -> bytes:
    """Create a minimal valid DOCX in memory using python-docx."""
    from docx import Document
    doc = Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_read_docx_returns_nonempty_string():
    from app.services.parser_engine.docx_reader import read_docx

    docx_bytes = _make_docx_bytes("Hello World")
    result = read_docx(docx_bytes)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Hello World" in result


def test_read_docx_corrupted_bytes_raises_docx_read_error():
    from app.services.parser_engine.docx_reader import read_docx
    from app.services.parser_engine.errors import DocxReadError

    with pytest.raises(DocxReadError):
        read_docx(b"this is not a valid docx file at all!!!")


def test_read_docx_oversized_raises_input_too_large_error():
    from app.services.parser_engine.docx_reader import read_docx
    from app.services.parser_engine.errors import InputTooLargeError

    # Create bytes larger than the limit (50MB)
    huge_bytes = b"X" * (51 * 1024 * 1024)
    with pytest.raises(InputTooLargeError):
        read_docx(huge_bytes)


def test_read_docx_empty_doc_returns_empty_or_whitespace():
    from app.services.parser_engine.docx_reader import read_docx

    docx_bytes = _make_docx_bytes("")
    result = read_docx(docx_bytes)
    assert isinstance(result, str)


def test_read_docx_multiline_text():
    from app.services.parser_engine.docx_reader import read_docx

    text = "Line 1\nLine 2\nLine 3"
    docx_bytes = _make_docx_bytes(text)
    result = read_docx(docx_bytes)
    assert "Line 1" in result
    assert "Line 3" in result
