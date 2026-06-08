"""Air-gap outbound validation — REQ-API-013, FR-210.

Customer document originals MUST only be processed within Customer Local Runtime
and MUST NEVER be sent to cloud.

# @MX:ANCHOR: [AUTO] AirGapService.validate_outbound — security boundary for all outbound payloads
# @MX:REASON: fan_in >= 3 (sync router, test_airgap, future export endpoints)
"""
from typing import Any


class AirGapViolation(Exception):
    """Raised when sensitive customer data is detected in an outbound payload."""


class AirGapService:
    """Validates outbound payloads to ensure no customer document data leaks (FR-210)."""

    # @MX:NOTE: [AUTO] SENSITIVE_FIELDS is the enforcement boundary for FR-210
    SENSITIVE_FIELDS: frozenset[str] = frozenset({
        "content",
        "raw_text",
        "file_content",
        "document_text",
        "storage_key",
    })

    def validate_outbound(self, payload: dict[str, Any]) -> None:
        """Recursively scan payload for sensitive field names.

        Raises:
            AirGapViolation: if any sensitive field is found in the payload or nested dicts.
        """
        self._scan(payload)

    def sanitize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a deep copy of payload with sensitive fields removed.

        Recursively sanitizes nested dicts.
        """
        return self._strip(payload)

    def _scan(self, obj: Any) -> None:
        """Recursively scan obj for sensitive field names."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in self.SENSITIVE_FIELDS:
                    raise AirGapViolation(
                        f"Sensitive field '{key}' detected in outbound payload. "
                        "Customer document data must not leave the local runtime (FR-210)."
                    )
                self._scan(value)
        elif isinstance(obj, list):
            for item in obj:
                self._scan(item)

    def _strip(self, obj: Any) -> Any:
        """Recursively remove sensitive fields from dicts."""
        if isinstance(obj, dict):
            return {
                key: self._strip(value)
                for key, value in obj.items()
                if key.lower() not in self.SENSITIVE_FIELDS
            }
        if isinstance(obj, list):
            return [self._strip(item) for item in obj]
        return obj
