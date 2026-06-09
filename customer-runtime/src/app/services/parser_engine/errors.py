"""Custom exceptions for the parser_engine package."""


class DocxReadError(Exception):
    """Raised when a DOCX file cannot be parsed."""


class XlsxReadError(Exception):
    """Raised when an XLSX file cannot be parsed."""


class InputTooLargeError(Exception):
    """Raised when input bytes exceed the configured size limit."""
