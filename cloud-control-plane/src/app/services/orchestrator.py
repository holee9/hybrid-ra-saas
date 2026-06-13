"""Crawl job orchestrator (T-016, REQ-001/004/006/010, AC-001/004/005).

Orchestrates the per-document pipeline:
  rate limit → fetch (with retry) → hash → dedup check → blob upload → metadata INSERT

Per-document and per-source failures are fully isolated:
  a single failed document/source never aborts the job (REQ-006, AC-004).

Emits structured JSON log events for each job lifecycle event (REQ-010, AC-005).

In-memory job_registry holds {job_id: {status, document_count}} for the status API.

# @MX:WARN: [AUTO] job_registry is a module-level dict — not safe for multi-process deployment.
# @MX:REASON: Suitable for single-process Container App; a distributed cache is required for HA.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
import os
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.regulatory_document import RegulatoryDocument
from app.services.dedup import DedupService
from app.services.knowledge_push import KnowledgePushService

logger = get_logger(__name__)

# @MX:WARN: [AUTO] Module-level mutable shared state — concurrency risk.
# @MX:REASON: Only one async crawl job runs at a time per process; concurrent access
#             is not expected. Replace with Redis for multi-process HA deployments.
job_registry: dict[str, dict[str, Any]] = {}


class CrawlOrchestrator:
    """Runs a complete crawl job across all enabled sources.

    # @MX:ANCHOR: [AUTO] Entry point for crawl job execution (REQ-001, AC-001).
    # @MX:REASON: Called by API trigger endpoint and cron job; fan_in >= 3.
    """

    def __init__(
        self,
        sources: list[Any],
        storage: Any,
        session: AsyncSession,
    ) -> None:
        self._sources = sources
        self._storage = storage
        self._session = session

    async def run(self, job_id: Optional[str] = None) -> str:
        """Execute one full crawl job and return the job_id.

        If job_id is provided (e.g., pre-registered by the trigger endpoint),
        that same id is used and updated in the registry — avoiding dual-id confusion.
        If not provided, a new UUID is generated.
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        job_registry[job_id] = {"status": "running", "document_count": 0}

        logger.info(
            "job_started",
            extra={"job_id": job_id, "source": "orchestrator"},
        )

        push_service = KnowledgePushService(
            push_url=os.getenv("REGULA_KNOWLEDGE_PUSH_URL", ""),
            push_secret=os.getenv("CRAWL_PUSH_SECRET", ""),
        )
        dedup = DedupService(self._session)
        total_stored = 0
        total_skipped = 0
        total_failed = 0
        stored_docs: list[dict] = []

        for source in self._sources:
            source_name = getattr(source, "SOURCE_NAME", "unknown")
            try:
                await source.load_robots()
                urls = await source.discover_document_urls()
            except Exception as exc:
                logger.error(
                    "source_discovery_failed",
                    extra={"job_id": job_id, "source": source_name},
                )
                logger.debug("source discovery exception: %s", exc)
                continue

            for url in urls:
                try:
                    content = await source.fetch_document(url)
                    content_hash = dedup.compute_hash(content)

                    if await dedup.is_duplicate(content_hash):
                        logger.info(
                            "document_skipped",
                            extra={
                                "job_id": job_id,
                                "source": source_name,
                                "document_count": total_skipped,
                            },
                        )
                        total_skipped += 1
                        continue

                    # Derive filename from URL path
                    filename = urlparse(url).path.split("/")[-1] or "document"
                    fetch_date = datetime.now(timezone.utc).date()

                    blob_path = await self._storage.upload_document(
                        source=source_name,
                        filename=filename,
                        content=content,
                        fetch_date=fetch_date,
                    )

                    doc = RegulatoryDocument(
                        source=source_name,
                        blob_path=blob_path,
                        content_hash=content_hash,
                        fetched_at=datetime.now(timezone.utc),
                        source_url=url,
                    )
                    self._session.add(doc)
                    await self._session.commit()

                    total_stored += 1
                    stored_docs.append({
                        "id": blob_path,
                        "url": url,
                        "hash": content_hash,
                        "source": source_name,
                        "content": (
                            content.decode("utf-8", errors="replace")
                            if isinstance(content, bytes)
                            else str(content)
                        ),
                    })
                    logger.info(
                        "document_stored",
                        extra={
                            "job_id": job_id,
                            "source": source_name,
                            "document_count": total_stored,
                        },
                    )

                except PermissionError:
                    # robots.txt disallowed — skip silently
                    total_skipped += 1
                except Exception as exc:
                    total_failed += 1
                    logger.error(
                        "document_failed",
                        extra={
                            "job_id": job_id,
                            "source": source_name,
                            "document_count": total_failed,
                        },
                    )
                    logger.debug("document failure exception for %s: %s", url, exc)
                    # REQ-006: continue with next document

        job_registry[job_id] = {
            "status": "completed",
            "document_count": total_stored,
            "skipped_count": total_skipped,
            "failed_count": total_failed,
        }

        logger.info(
            "job_completed",
            extra={
                "job_id": job_id,
                "source": "orchestrator",
                "document_count": total_stored,
            },
        )

        # GAP-03: Push newly stored documents to Regula Vectorize (non-blocking)
        await push_service.push(job_id=job_id, documents=stored_docs)

        return job_id
