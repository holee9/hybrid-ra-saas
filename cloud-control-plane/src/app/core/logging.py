"""Structured JSON logger for cloud-control-plane.

Every log record is rendered as a single-line JSON object written to stdout.
Container Apps ships stdout to Application Insights automatically.

# @MX:NOTE: [AUTO] JSON field contract: timestamp, level, event are always present.
#           Optional fields (source, document_count, job_id) appear only when set
#           on the LogRecord as extra attributes. Absent fields are NEVER included
#           in the output — callers must not rely on a key being None vs missing.
"""

import json
import logging
import sys
from datetime import datetime, timezone


_OPTIONAL_FIELDS = ("source", "document_count", "job_id")

# Standard LogRecord attributes to exclude from the output — we handle them explicitly.
_SKIP_ATTRS = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON.

    Required fields: timestamp (ISO-8601 UTC), level, event.
    Optional fields: source, document_count, job_id — included only when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        # format() populates record.message and record.exc_text
        record.message = record.getMessage()

        payload: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.message,
        }

        # Include optional fields only when set on the record
        for field in _OPTIONAL_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """Return a Logger configured with JsonFormatter writing to stdout.

    # @MX:ANCHOR: [AUTO] Single entry point for all structured logging in the service.
    # @MX:REASON: Called by routers, services, and crawler orchestrator (fan_in >= 3).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
