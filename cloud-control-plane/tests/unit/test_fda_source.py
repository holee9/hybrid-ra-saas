"""Unit tests for FDA crawler source (T-015, REQ-001).

All HTTP calls use httpx.MockTransport — no real network.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_discover_document_urls_returns_list():
    """discover_document_urls parses listing page and returns at least one URL."""
    from app.services.crawler.fda import FDASource

    # Minimal HTML listing page with one PDF link
    listing_html = b"""
    <html><body>
      <a href="/media/12345/download">Guidance Document 1</a>
      <a href="/media/67890/download">Guidance Document 2</a>
      <a href="/about">About FDA</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = FDASource(
        client=client, listing_url="https://fda.gov/guidance/", media_path_prefix="/media/"
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    assert isinstance(urls, list)
    assert len(urls) >= 1
    assert all("fda.gov" in u or u.startswith("https://") for u in urls)


@pytest.mark.asyncio
async def test_discover_filters_non_media_links():
    """discover_document_urls only returns links matching media_path_prefix."""
    from app.services.crawler.fda import FDASource

    listing_html = b"""
    <html><body>
      <a href="/media/111/download">Doc 1</a>
      <a href="/guidance/something">Not a doc</a>
      <a href="/media/222/download">Doc 2</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = FDASource(
        client=client, listing_url="https://fda.gov/guidance/", media_path_prefix="/media/"
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    assert len(urls) == 2
    assert all("/media/" in u for u in urls)


@pytest.mark.asyncio
async def test_source_name_is_fda():
    """FDASource.SOURCE_NAME must be 'fda' (REQ-002 path convention)."""
    from app.services.crawler.fda import FDASource

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)
    source = FDASource(
        client=client, listing_url="https://fda.gov/guidance/", media_path_prefix="/media/"
    )

    assert source.SOURCE_NAME == "fda"


@pytest.mark.asyncio
async def test_fetch_document_returns_bytes():
    """fetch_document returns raw bytes of the document."""
    from app.services.crawler.fda import FDASource

    pdf_bytes = b"%PDF-1.4 fake pdf content"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=pdf_bytes)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = FDASource(
        client=client, listing_url="https://fda.gov/guidance/", media_path_prefix="/media/"
    )
    await source.load_robots()

    result = await source.fetch_document("https://fda.gov/media/12345/download")

    assert result == pdf_bytes
