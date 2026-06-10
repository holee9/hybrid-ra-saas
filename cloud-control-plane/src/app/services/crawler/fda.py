"""FDA regulatory document crawler source (T-015, REQ-001).

Discovers document URLs from the FDA guidance listing page and
fetches raw bytes for each document.

Listing URL and media path prefix are configurable via constructor
to mitigate breakage from FDA HTML structure changes.
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Optional
from urllib.parse import urljoin

import httpx

from app.services.crawler.base import CrawlerSource


class FDASource(CrawlerSource):
    """FDA guidance document crawler.

    # @MX:NOTE: [AUTO] Listing URL and media_path_prefix are injected to survive
    #           FDA HTML structure changes without code changes (risk mitigation).
    """

    SOURCE_NAME = "fda"

    def __init__(
        self,
        client: httpx.AsyncClient,
        listing_url: str,
        media_path_prefix: str = "/media/",
        robots_url: Optional[str] = None,
        retry_count: int = 3,
        initial_delay: float = 2.0,
        multiplier: float = 2.0,
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        # Derive robots URL from listing URL base if not provided
        if robots_url is None:
            from urllib.parse import urlparse
            parsed = urlparse(listing_url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        super().__init__(
            client=client,
            robots_url=robots_url,
            retry_count=retry_count,
            initial_delay=initial_delay,
            multiplier=multiplier,
            sleep=sleep,
        )
        self._listing_url = listing_url
        self._media_path_prefix = media_path_prefix

    async def discover_document_urls(self) -> list[str]:
        """Fetch the listing page and extract document download URLs.

        Only returns links whose href starts with media_path_prefix,
        converted to absolute URLs.
        """
        response = await self._client.get(self._listing_url)
        response.raise_for_status()

        # Extract all href attributes from anchor tags
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', response.text)

        urls: list[str] = []
        for href in hrefs:
            if href.startswith(self._media_path_prefix):
                # Build absolute URL
                abs_url = urljoin(self._listing_url, href)
                urls.append(abs_url)

        return urls
