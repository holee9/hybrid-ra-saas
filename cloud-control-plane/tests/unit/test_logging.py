"""Unit tests for structured JSON logger — RED phase.

Tests verify the JSON formatter contract without any network or Docker dependency.
"""
import json
import logging


def test_json_log_has_required_fields():
    """Every log record produces JSON with timestamp, level, source, event."""
    from app.core.logging import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="crawl started",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)

    assert "timestamp" in data
    assert "level" in data
    assert "event" in data
    assert data["level"] == "INFO"
    assert data["event"] == "crawl started"


def test_json_log_omits_absent_optional_fields():
    """Optional fields (document_count, job_id) are absent when not set."""
    from app.core.logging import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="crawler",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="job complete",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    data = json.loads(output)

    # Optional fields must not appear unless explicitly set on the record
    assert "document_count" not in data
    assert "job_id" not in data


def test_json_log_includes_optional_fields_when_set():
    """document_count and job_id appear when set as record extras."""
    from app.core.logging import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="crawler",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="fetched",
        args=(),
        exc_info=None,
    )
    record.document_count = 5
    record.job_id = "job-abc-123"

    output = formatter.format(record)
    data = json.loads(output)

    assert data["document_count"] == 5
    assert data["job_id"] == "job-abc-123"


def test_json_log_includes_source_when_set():
    """source field appears when set as record extra."""
    from app.core.logging import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="crawler",
        level=logging.WARNING,
        pathname="",
        lineno=0,
        msg="rate limited",
        args=(),
        exc_info=None,
    )
    record.source = "fda"

    output = formatter.format(record)
    data = json.loads(output)

    assert data["source"] == "fda"
    assert data["level"] == "WARNING"


def test_get_logger_returns_configured_logger():
    """get_logger() returns a Logger with JSON handler attached."""
    from app.core.logging import get_logger

    logger = get_logger("test.module")
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) > 0


def test_log_output_is_single_line():
    """Each log record is exactly one line (no newlines in JSON output)."""
    from app.core.logging import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="crawler",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg="connection failed",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)

    assert "\n" not in output
