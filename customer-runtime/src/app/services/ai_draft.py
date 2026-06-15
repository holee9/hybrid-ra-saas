"""AI draft generation service — SPEC-AUTHORING-001.

# @MX:ANCHOR: [AUTO] generate_draft — AI draft generation entry point
# @MX:REASON: [AUTO] FR-210: _assert_local() must fire before any Ollama call
"""
import asyncio
import json
import logging
import os
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.authoring_section_entry import AuthoringSectionEntry
from app.services.parser_engine.llm_fallback import _assert_local

logger = logging.getLogger(__name__)

OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_TIMEOUT = 25.0  # 30s total budget minus 5s margin

_DRAFT_PROMPT = """\
You are a medical device regulatory authoring expert.
Generate a draft section for the following regulatory document section.

Section instructions: {instructions}

Product context: {product_context}

Write a clear, concise draft for this section. Return JSON:
{{"draft": "<section text>", "confidence": <0.0-1.0>, "sources": [<ref_ids>]}}

JSON only. No explanation."""


async def generate_draft(
    entry: AuthoringSectionEntry,
    section_instructions: str,
    product_context: str,
    db: AsyncSession,
    ollama_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Generate an AI draft for a section entry.

    Args:
        entry: The section entry to draft.
        section_instructions: Instructions from the template section.
        product_context: Product profile context string.
        db: Async database session.
        ollama_client: Optional injected client (for testing).

    Returns:
        Dict with ai_draft, ai_draft_confidence, ai_draft_sources, status.
    """
    # Security gate: FR-210 — must verify local endpoint before any HTTP call
    _assert_local(OLLAMA_ENDPOINT)

    prompt = _DRAFT_PROMPT.format(
        instructions=section_instructions,
        product_context=product_context,
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        async with asyncio.timeout(30.0):
            result = await _call_ollama(payload, ollama_client)
    except asyncio.TimeoutError:
        logger.warning("AI draft generation timed out for entry %s", entry.entry_id)
        return {
            "status": "timeout",
            "reason": "AI draft generation exceeded 30s limit",
        }
    except Exception as exc:
        logger.error("AI draft generation failed: %s", exc)
        return {
            "status": "error",
            "reason": str(exc),
        }

    # Parse response
    raw_text = result.get("response", "")
    ai_draft = raw_text
    confidence = 0.5
    sources: list[str] = []

    try:
        parsed = json.loads(raw_text)
        ai_draft = parsed.get("draft", raw_text)
        confidence = float(parsed.get("confidence", 0.5))
        sources = parsed.get("sources", [])
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "ai_draft": ai_draft,
        "ai_draft_confidence": confidence,
        "ai_draft_sources": sources,
        "status": "ai_draft",
    }


async def _call_ollama(
    payload: dict[str, Any],
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Send generate request to Ollama. Uses injected client if provided."""
    if client is not None:
        resp = await client.post(
            f"{OLLAMA_ENDPOINT}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()

    async with httpx.AsyncClient() as c:
        resp = await c.post(
            f"{OLLAMA_ENDPOINT}/api/generate",
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
