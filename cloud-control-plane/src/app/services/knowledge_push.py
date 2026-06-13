"""Regula knowledge push service — POSTs newly crawled documents to Regula Vectorize.

# @MX:ANCHOR: [AUTO] Integration boundary: Azure CCP → Regula Vectorize sync (GAP-03).
# @MX:REASON: Called by CrawlOrchestrator.run() after every successful crawl job.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Truncate very large documents to avoid oversized payloads
_MAX_CONTENT_CHARS = 50_000


class KnowledgePushService:
    """Pushes newly crawled document metadata to Regula's knowledge sync endpoint.

    No-op when REGULA_KNOWLEDGE_PUSH_URL is not configured.
    Push failures are logged as warnings and do NOT abort the crawl job.
    """

    def __init__(self, push_url: str, push_secret: str) -> None:
        self._push_url = push_url
        self._push_secret = push_secret

    async def push(self, job_id: str, documents: list[dict[str, Any]]) -> None:
        """POST documents batch to Regula sync endpoint.

        Args:
            job_id: Crawl job identifier.
            documents: List of {id, url, hash, source, content} dicts.
        """
        if not self._push_url:
            logger.debug("knowledge_push skipped: REGULA_KNOWLEDGE_PUSH_URL not configured")
            return
        if not self._push_secret:
            logger.warning("knowledge_push skipped: CRAWL_PUSH_SECRET not configured")
            return
        if not documents:
            logger.debug("knowledge_push skipped: no new documents in job %s", job_id)
            return

        # Truncate content to avoid oversized payloads
        truncated = [
            {**doc, "content": doc.get("content", "")[:_MAX_CONTENT_CHARS]}
            for doc in documents
        ]

        payload = {"job_id": job_id, "documents": truncated}
        headers = {
            "X-Crawl-Push-Secret": self._push_secret,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self._push_url, json=payload, headers=headers)
                response.raise_for_status()
            logger.info(
                "knowledge_push_succeeded",
                extra={"job_id": job_id, "document_count": len(truncated)},
            )
        except Exception as exc:
            # Non-blocking: push failure must not abort the crawl job
            logger.warning(
                "knowledge_push_failed",
                extra={"job_id": job_id, "error": str(exc)},
            )
