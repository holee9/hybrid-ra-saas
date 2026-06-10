"""Abstract base for all regulatory document crawlers.

Responsibilities:
- Fetch and parse robots.txt before each job run (REQ-007, REQ-008, AC-006).
  robots.txt is re-fetched on every run — never cached across job boundaries.
- Enforce robots.txt disallow rules: raises PermissionError for disallowed URLs.
- Exponential backoff retry on network error or non-2xx response (REQ-005, AC-004).
  After all retries exhausted: raises — caller (orchestrator) catches and continues.
- Per-source rate limiting via RateLimiter (REQ-009, AC-003): 1 req/s default.

# @MX:NOTE: [AUTO] robots.txt is re-fetched on every job run (not cached) to pick up
#           policy changes without requiring a service restart (AC-006).
"""

from __future__ import annotations

import asyncio
import re
import time
import urllib.robotparser
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.core.logging import get_logger
from app.core.ratelimit import RateLimiter

logger = get_logger(__name__)

# User-Agent string sent with every request (REQ-007: must identify the crawler)
CRAWLER_USER_AGENT = "RA-Crawler/1.0"


class CrawlerSource(ABC):
    """Abstract base class for all regulatory document sources.

    # @MX:ANCHOR: [AUTO] Public contract for crawler sources (REQ-007/008/005/006/009).
    # @MX:REASON: Subclassed by FDASource (P1), MFDSSource, EUMDRSource (P2); fan_in >= 3.
    """

    SOURCE_NAME: str  # e.g. "fda", "mfds", "eu-mdr"

    def __init__(
        self,
        client: httpx.AsyncClient,
        robots_url: str,
        retry_count: int = 3,
        initial_delay: float = 2.0,
        multiplier: float = 2.0,
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
        clock: Optional[Callable[[], float]] = None,
        rate_limit: float = 1.0,
    ) -> None:
        self._client = client
        self._robots_url = robots_url
        self._retry_count = retry_count
        self._initial_delay = initial_delay
        self._multiplier = multiplier
        # Inject sleep for testability (avoids real waits in unit tests)
        self._sleep: Callable[[float], Awaitable[None]] = sleep or asyncio.sleep
        self._robots_parser: Optional[urllib.robotparser.RobotFileParser] = None
        # Per-source rate limiter (REQ-009, AC-003) — injectable clock for unit testing
        min_interval = 1.0 / rate_limit if rate_limit > 0 else 1.0
        self._rate_limiter = RateLimiter(
            min_interval=min_interval,
            clock=clock or time.monotonic,
            sleep=self._sleep,
        )

    # ------------------------------------------------------------------
    # robots.txt handling
    # ------------------------------------------------------------------

    async def load_robots(self) -> None:
        """Fetch and parse robots.txt for this source.

        Must be called once per job run before any fetch_document calls.
        Always re-fetches — never uses a cached parser from a previous run.

        # @MX:NOTE: [AUTO] Re-fetch rationale: robots.txt policy can change between runs.
        #           Caching across jobs would violate AC-006 compliance requirement.
        """
        try:
            response = await self._client.get(self._robots_url)
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(self._robots_url)
            parser.parse(response.text.splitlines())
            self._robots_parser = parser
        except Exception as exc:
            logger.warning(
                "Failed to fetch robots.txt for %s: %s — defaulting to allow-all",
                self._robots_url,
                exc,
            )
            # Fail open: if robots.txt is unreachable, allow all (conservative choice)
            self._robots_parser = None

    def _is_allowed(self, url: str) -> bool:
        """Return True if the URL is allowed per robots.txt."""
        if self._robots_parser is None:
            return True  # no robots.txt loaded — allow all
        return self._robots_parser.can_fetch(CRAWLER_USER_AGENT, url)

    # ------------------------------------------------------------------
    # Document fetching with retry / backoff (REQ-005/006)
    # ------------------------------------------------------------------

    async def fetch_document(self, url: str) -> bytes:
        """Fetch raw bytes for a document URL.

        Checks robots.txt disallow rules first (REQ-008).
        Applies per-source rate limiting via RateLimiter (REQ-009, AC-003).
        Retries on network errors or non-2xx responses with exponential backoff.
        Raises after all retries are exhausted (caller must handle; REQ-006).

        # @MX:WARN: [AUTO] Retry loop sleeps real time unless sleep is injected.
        # @MX:REASON: Without mock sleep, unit tests would be slow (2s+4s+8s per case).
        """
        if not self._is_allowed(url):
            raise PermissionError(f"URL disallowed by robots.txt: {url}")

        # Rate limit per source (REQ-009, AC-003) — must run after robots check,
        # before the HTTP GET.  robots.txt fetch itself is NOT rate-limited.
        await self._rate_limiter.acquire()

        delay = self._initial_delay
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retry_count + 2):  # +2 = initial + retries
            try:
                response = await self._client.get(url)
                if response.status_code >= 200 and response.status_code < 300:
                    return response.content
                # Non-2xx: treat as retriable error
                last_exc = ValueError(f"Non-2xx response {response.status_code} for {url}")
            except httpx.HTTPError as exc:
                last_exc = exc

            # Don't sleep after the last attempt
            if attempt <= self._retry_count:
                logger.warning(
                    "Fetch attempt %d failed for %s: %s — retrying in %.1fs",
                    attempt,
                    url,
                    last_exc,
                    delay,
                )
                await self._sleep(delay)
                delay *= self._multiplier

        # All retries exhausted — raise so orchestrator can log + continue
        logger.error("All %d retry attempts exhausted for %s", self._retry_count, url)
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Link extraction helper (SSRF-safe, shared by all subclasses)
    # ------------------------------------------------------------------

    def _extract_links(self, html: str, prefix: str, listing_url: str) -> list[str]:
        """Extract and return absolute URLs from html matching prefix, same-host only.

        Steps:
        1. Regex-extract all href values.
        2. Filter hrefs that start with prefix (relative paths).
        3. urljoin each against listing_url to get absolute URLs.
        4. REJECT any resulting URL whose netloc differs from listing_url's netloc.

        # @MX:NOTE: [AUTO] SSRF mitigation: absolute hrefs to foreign hosts are dropped.
        #           An attacker-controlled page cannot redirect the crawler off-domain.
        """
        listing_netloc = urlparse(listing_url).netloc
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)

        urls: list[str] = []
        for href in hrefs:
            if not href.startswith(prefix):
                continue
            abs_url = urljoin(listing_url, href)
            if urlparse(abs_url).netloc != listing_netloc:
                # Cross-domain — reject (SSRF prevention)
                continue
            urls.append(abs_url)
        return urls

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def discover_document_urls(self) -> list[str]:
        """Return list of document URLs to fetch from this source."""
        ...
