"""Unit tests for EU MDR crawler source (T-019, REQ-001).

All HTTP calls use httpx.MockTransport — no real network.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_eu_mdr_source_name():
    """EUMDRSource.SOURCE_NAME must be 'eu-mdr' (REQ-002 path convention)."""
    from app.services.crawler.eu_mdr import EUMDRSource

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)
    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html?type=advanced&lang=en",
        doc_path_prefix="/legal-content/",
    )

    assert source.SOURCE_NAME == "eu-mdr"


@pytest.mark.asyncio
async def test_eu_mdr_discover_returns_document_urls():
    """discover_document_urls parses EUR-Lex listing and returns PDF links."""
    from app.services.crawler.eu_mdr import EUMDRSource

    listing_html = b"""
    <html><body>
      <a href="/legal-content/EN/TXT/PDF/?uri=CELEX:32017R0745">MDR PDF</a>
      <a href="/legal-content/EN/TXT/HTML/?uri=CELEX:32017R0745">MDR HTML</a>
      <a href="/homepage">Home</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html",
        doc_path_prefix="/legal-content/",
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    assert isinstance(urls, list)
    assert len(urls) == 2
    assert all("eur-lex.europa.eu" in u for u in urls)


@pytest.mark.asyncio
async def test_eu_mdr_discover_filters_non_legal_content():
    """discover_document_urls only returns links matching doc_path_prefix."""
    from app.services.crawler.eu_mdr import EUMDRSource

    listing_html = b"""
    <html><body>
      <a href="/legal-content/EN/TXT/PDF/?uri=A">Doc A</a>
      <a href="/other/page">Other</a>
      <a href="/legal-content/EN/TXT/HTML/?uri=B">Doc B HTML</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html",
        doc_path_prefix="/legal-content/",
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    assert len(urls) == 2
    assert all("/legal-content/" in u for u in urls)


@pytest.mark.asyncio
async def test_eu_mdr_robots_disallow_respected():
    """EUMDRSource respects robots.txt disallow rules (REQ-008)."""
    from app.services.crawler.eu_mdr import EUMDRSource

    robots_txt = b"User-agent: *\nDisallow: /legal-content/\n"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=robots_txt)
        return httpx.Response(200, content=b"<html></html>")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html",
        doc_path_prefix="/legal-content/",
    )
    await source.load_robots()

    with pytest.raises(PermissionError):
        await source.fetch_document(
            "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32017R0745"
        )


@pytest.mark.asyncio
async def test_eu_mdr_fetch_document_returns_bytes():
    """fetch_document returns raw bytes of the document."""
    from app.services.crawler.eu_mdr import EUMDRSource

    pdf_bytes = b"%PDF-1.4 eu mdr regulation"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=pdf_bytes)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html",
        doc_path_prefix="/legal-content/",
    )
    await source.load_robots()

    result = await source.fetch_document(
        "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32017R0745"
    )

    assert result == pdf_bytes


@pytest.mark.asyncio
async def test_eu_mdr_sleep_injection():
    """Sleep function is injectable (supports rate-limit testing)."""
    from app.services.crawler.eu_mdr import EUMDRSource

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)

    source = EUMDRSource(
        client=client,
        listing_url="https://eur-lex.europa.eu/search.html",
        doc_path_prefix="/legal-content/",
        sleep=fake_sleep,
    )

    assert source._sleep is fake_sleep
