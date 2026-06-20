"""Template API client — shared by authoring router and checklist generator.

# @MX:ANCHOR: [AUTO] fetch_template — Template API contract boundary
# @MX:REASON: [AUTO] fan_in >= 2 (authoring router + checklist generator); timeout/retry behavior must be stable.
"""
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TEMPLATE_API_TIMEOUT = float(os.environ.get("TEMPLATE_API_TIMEOUT", "10.0"))
TEMPLATE_API_MAX_RETRIES = int(os.environ.get("TEMPLATE_API_MAX_RETRIES", "3"))


class TemplateAPIError(Exception):
    """Raised when the template API call fails after all retries."""


async def fetch_template_sections(
    pack_id: str,
    endpoint_path: str = "/packs/{pack_id}/sections",
    *,
    base_url: str = "",
) -> list[dict[str, Any]]:
    """Fetch template sections from the Template API.

    Args:
        pack_id: Template pack identifier.
        endpoint_path: URL path template. Defaults to authoring pack endpoint.
            Use "/template-packs/{pack_id}/sections" for checklist endpoint.
        base_url: Override base URL (for testing). Falls back to TEMPLATE_API_URL env.

    Returns:
        List of section dicts from the API.

    Raises:
        TemplateAPIError: When TEMPLATE_API_URL is not configured, pack returns 404,
            or all retries are exhausted.
    """
    url = base_url or os.environ.get("TEMPLATE_API_URL", "")
    if not url:
        raise TemplateAPIError(
            "TEMPLATE_API_URL is not configured. "
            "Set this environment variable to point to the template service."
        )

    path = endpoint_path.format(pack_id=pack_id)
    full_url = f"{url.rstrip('/')}{path}"
    last_exc: Exception | None = None

    for attempt in range(1, TEMPLATE_API_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TEMPLATE_API_TIMEOUT) as client:
                resp = await client.get(full_url)
                if resp.status_code == 404:
                    # Pack not found — deterministic empty result, no retry.
                    return []
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException as exc:
            logger.warning(
                "template_api_timeout attempt=%d/%d url=%s: %s",
                attempt,
                TEMPLATE_API_MAX_RETRIES,
                full_url,
                exc,
            )
            last_exc = exc
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "template_api_http_error attempt=%d/%d status=%d url=%s: %s",
                attempt,
                TEMPLATE_API_MAX_RETRIES,
                exc.response.status_code,
                full_url,
                exc,
            )
            last_exc = exc
        except Exception as exc:
            raise TemplateAPIError(
                f"Unexpected template API error for pack '{pack_id}': {exc}"
            ) from exc

    raise TemplateAPIError(
        f"Template API failed for pack '{pack_id}' after {TEMPLATE_API_MAX_RETRIES} "
        f"retries. Last error: {last_exc}"
    ) from last_exc
