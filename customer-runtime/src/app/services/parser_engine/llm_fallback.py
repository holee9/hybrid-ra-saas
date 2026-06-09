"""Stage 3: Ollama local LLM fallback (localhost only, data sovereignty).

REQ-007: All LLM calls must remain on-premises. _assert_local() enforces this.
"""
import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.schemas.parse import ExtractionStage, FieldExtraction
from app.services.parser_engine.confidence import calculate

logger = logging.getLogger(__name__)

# @MX:WARN: [AUTO] _assert_local() is a security gate — must not be bypassed
# @MX:REASON: Data sovereignty requirement (REQ-007): no PHI/PII to external hosts

_ALLOWED_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "ollama"})

_PROMPT_TEMPLATE: str = """You are a medical device regulatory expert.
Extract the following fields from the IFU document text below.
Return a JSON object with ONLY the requested fields as keys and their extracted values as strings.
If a field cannot be found, set its value to null.

Fields to extract: {fields}

Document text:
{text}

Respond with valid JSON only. No explanation."""


def _assert_local(base_url: str) -> None:
    """Raise ValueError if base_url points to a non-local host.

    Allowed hosts: localhost, 127.0.0.1, ollama (Docker service name).

    Args:
        base_url: The LLM endpoint base URL.

    Raises:
        ValueError: When the host is not in the allowed list.
    """
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    if host not in _ALLOWED_HOSTS:
        raise ValueError(
            f"LLM endpoint '{base_url}' is not local. "
            f"Allowed hosts: {sorted(_ALLOWED_HOSTS)}. "
            "Data sovereignty policy (REQ-007) prohibits external LLM calls."
        )


async def extract(
    text: str,
    fields_needed: list[str],
    *,
    llm_client: httpx.AsyncClient | None = None,
    base_url: str = "http://localhost:11434",
    model: str = "llama3.1:8b",
) -> dict[str, FieldExtraction]:
    """Extract fields using a local Ollama LLM.

    Args:
        text: Document plain text.
        fields_needed: Field names to extract.
        llm_client: Injected httpx.AsyncClient (injectable for unit tests, B3).
        base_url: Ollama endpoint — must be local (REQ-007).
        model: Ollama model name.

    Returns:
        Dict of extracted fields with stage=LLM, or {} on failure.

    Raises:
        ValueError: If base_url is not a local host (_assert_local guard).
    """
    if not fields_needed:
        return {}

    # Security gate — raises before any HTTP call if not local
    _assert_local(base_url)

    client = llm_client if llm_client is not None else httpx.AsyncClient()

    prompt = _PROMPT_TEMPLATE.format(
        fields=", ".join(fields_needed),
        text=text[:4000],  # Truncate to avoid context overflow
    )

    try:
        response = await client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        response.raise_for_status()
        raw_json = response.json()
        llm_text = raw_json.get("response", "{}")
        extracted: dict[str, Any] = json.loads(llm_text)
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
        logger.warning("LLM fallback failed: %s", exc)
        return {}

    result: dict[str, FieldExtraction] = {}
    for field in fields_needed:
        value = extracted.get(field)
        if value is not None:
            str_value = str(value) if not isinstance(value, (list, type(None))) else value
            field_completeness = 1.0
            rule_match = 0.4  # LLM is least certain stage
        else:
            str_value = None
            field_completeness = 0.0
            rule_match = 0.0

        confidence = calculate(
            field_completeness=field_completeness,
            rule_match=rule_match,
            semantic_similarity=0.0,
        )
        result[field] = FieldExtraction(
            value=str_value,
            confidence=confidence,
            stage=ExtractionStage.LLM,
        )

    return result
