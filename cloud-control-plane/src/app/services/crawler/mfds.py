"""MFDS (Korea Food and Drug Safety Ministry) regulatory document crawler source (T-018, REQ-001).

Discovers document URLs from the MFDS guidance/notice listing page
and fetches raw bytes for each document.

# @MX:NOTE: [AUTO] Listing URL and doc_path_prefix are injected via constructor to survive
#           MFDS HTML structure changes without code changes.
#           MFDS uses a board-style URL scheme: /brd/m_{board_id}/view.do?seq={n}
#           The doc_path_prefix "/brd/" captures all board paths, allowing the
#           operator to narrow scope by passing a more specific prefix (e.g., "/brd/m_218/").
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.services.crawler.base import CrawlerSource


class MFDSSource(CrawlerSource):
    """MFDS guidance/notice document crawler.

    # @MX:NOTE: [AUTO] MFDS board structure: listings at /brd/m_{id}/list.do,
    #           document views at /brd/m_{id}/view.do?seq={n}.
    #           We collect all hrefs matching doc_path_prefix to stay resilient
    #           to board ID changes.
    """

    SOURCE_NAME = "mfds"

    def __init__(
        self,
        client: httpx.AsyncClient,
        listing_url: str,
        doc_path_prefix: str = "/brd/",
        robots_url: Optional[str] = None,
        retry_count: int = 3,
        initial_delay: float = 2.0,
        multiplier: float = 2.0,
        sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        # Derive robots URL from listing URL base if not provided
        if robots_url is None:
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
        self._doc_path_prefix = doc_path_prefix

    async def discover_document_urls(self) -> list[str]:
        """Fetch the listing page and extract document view/download URLs.

        Only returns links whose href starts with doc_path_prefix,
        converted to absolute URLs.
        """
        response = await self._client.get(self._listing_url)
        response.raise_for_status()

        # Extract all href attributes from anchor tags
        hrefs = re.findall(r'href=["\']([^"\']+)["\']', response.text)

        urls: list[str] = []
        for href in hrefs:
            if href.startswith(self._doc_path_prefix):
                abs_url = urljoin(self._listing_url, href)
                urls.append(abs_url)

        return urls
