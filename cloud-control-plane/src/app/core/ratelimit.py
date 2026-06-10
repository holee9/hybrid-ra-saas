"""Token-bucket style rate limiter ensuring max 1 request/second per source.

Each source creates its own RateLimiter instance (independent, per-source).
Clock and sleep are injectable for deterministic unit testing.

# @MX:WARN: [AUTO] RateLimiter instances are NOT thread-safe.
# @MX:REASON: Designed for single-threaded async crawl; concurrent callers need per-caller instance.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Optional


class RateLimiter:
    """Min-interval rate limiter: ensures at least `min_interval` seconds between requests.

    # @MX:ANCHOR: [AUTO] Public contract for per-source rate limiting (REQ-CRAWLER-009, AC-003).
    # @MX:REASON: Called by CrawlerSource.fetch_document and orchestrator; fan_in >= 3.
    """

    def __init__(
        self,
        min_interval: float = 1.0,
        clock: Optional[Callable[[], float]] = None,
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        self._min_interval = min_interval
        # Inject clock for testability; default to monotonic time
        self._clock: Callable[[], float] = clock or time.monotonic
        # Inject sleep for testability; default to asyncio.sleep
        self._sleep: Callable[[float], Awaitable[None]] = sleep or asyncio.sleep
        self._last_request_time: Optional[float] = None

    async def acquire(self) -> None:
        """Wait until the min_interval has elapsed since the last request."""
        now = self._clock()
        if self._last_request_time is not None:
            elapsed = now - self._last_request_time
            wait = self._min_interval - elapsed
            if wait > 0:
                await self._sleep(wait)
        self._last_request_time = self._clock()
