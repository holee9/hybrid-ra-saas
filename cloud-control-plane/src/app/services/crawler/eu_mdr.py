"""EU MDR (Medical Device Regulation 2017/745) document crawler source (T-019, REQ-001).

Discovers document links from EUR-Lex search/listing pages and
fetches raw bytes for each document.

# @MX:NOTE: [AUTO] Listing URL and doc_path_prefix are injected via constructor.
#           EUR-Lex uses /legal-content/{lang}/TXT/{format}/?uri=CELEX:{id} paths.
#           The doc_path_prefix "/legal-content/" captures all EUR-Lex content links,
#           allowing narrowing by passing e.g. "/legal-content/EN/TXT/PDF/" for PDF-only.
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.services.crawler.base import CrawlerSource


class EUMDRSource(CrawlerSource):
    """EUR-Lex EU MDR regulation document crawler.

    # @MX:NOTE: [AUTO] EUR-Lex URL structure: /legal-content/{lang}/TXT/{fmt}/?uri=CELEX:{id}
    #           CELEX:32017R0745 = EU MDR 2017/745 (Regulation (EU) 2017/745 on medical devices).
    #           doc_path_prefix default "/legal-content/" captures HTML, PDF, and other formats.
    """

    SOURCE_NAME = "eu-mdr"

    def __init__(
        self,
        client: httpx.AsyncClient,
        listing_url: str,
        doc_path_prefix: str = "/legal-content/",
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
        """Fetch the listing page and extract document links.

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
