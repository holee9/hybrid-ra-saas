"""Unit tests for MFDS crawler source (T-018, REQ-001).

All HTTP calls use httpx.MockTransport — no real network.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_mfds_source_name_is_mfds():
    """MFDSSource.SOURCE_NAME must be 'mfds' (REQ-002 path convention)."""
    from app.services.crawler.mfds import MFDSSource

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)
    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
    )

    assert source.SOURCE_NAME == "mfds"


@pytest.mark.asyncio
async def test_mfds_discover_returns_document_urls():
    """discover_document_urls parses listing page and returns matching URLs."""
    from app.services.crawler.mfds import MFDSSource

    listing_html = b"""
    <html><body>
      <a href="/brd/m_218/view.do?seq=1">Notice 1</a>
      <a href="/brd/m_218/view.do?seq=2">Notice 2</a>
      <a href="/about">About MFDS</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    assert isinstance(urls, list)
    assert len(urls) == 2
    assert all("mfds.go.kr" in u for u in urls)


@pytest.mark.asyncio
async def test_mfds_discover_filters_non_doc_links():
    """discover_document_urls only returns links matching doc_path_prefix."""
    from app.services.crawler.mfds import MFDSSource

    listing_html = b"""
    <html><body>
      <a href="/brd/m_218/view.do?seq=10">Doc A</a>
      <a href="/eng/main.do">English</a>
      <a href="/brd/m_999/view.do?seq=5">Other board</a>
    </body></html>
    """

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=listing_html)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
    )
    await source.load_robots()

    urls = await source.discover_document_urls()

    # /brd/ prefix matches both /brd/m_218/ and /brd/m_999/
    assert all("/brd/" in u for u in urls)


@pytest.mark.asyncio
async def test_mfds_robots_disallow_respected():
    """MFDSSource respects robots.txt disallow rules (REQ-008)."""
    from app.services.crawler.mfds import MFDSSource

    robots_txt = b"User-agent: *\nDisallow: /brd/\n"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=robots_txt)
        return httpx.Response(200, content=b"<html><body></body></html>")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
    )
    await source.load_robots()

    with pytest.raises(PermissionError):
        await source.fetch_document("https://www.mfds.go.kr/brd/m_218/view.do?seq=1")


@pytest.mark.asyncio
async def test_mfds_fetch_document_returns_bytes():
    """fetch_document returns raw bytes."""
    from app.services.crawler.mfds import MFDSSource

    pdf_bytes = b"%PDF-1.4 mfds document"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=pdf_bytes)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
    )
    await source.load_robots()

    result = await source.fetch_document("https://www.mfds.go.kr/brd/m_218/view.do?seq=1")

    assert result == pdf_bytes


@pytest.mark.asyncio
async def test_mfds_rate_limit_enforces_min_interval_between_fetches():
    """Two consecutive fetch_document calls must throttle the second via injected sleep (AC-003, REQ-009).

    Clock is frozen so the second acquire sees zero elapsed time — forcing a sleep of
    exactly min_interval (1.0 s).  A weak '>= 0' assertion would mask a missing
    acquire() call, so we assert sleep >= min_interval to catch wiring regressions.
    """
    from app.services.crawler.mfds import MFDSSource

    MIN_INTERVAL = 1.0
    # Clock sequence:
    #   acquire #1: now=0.0 (no prior request), last=0.0
    #   acquire #2: now=0.0 → elapsed=0.0 → wait=1.0 → sleep(1.0), last=0.0
    # All reads return 0.0 so the second acquire always sees zero elapsed time.
    clock_time = [0.0]

    def fake_clock() -> float:
        return clock_time[0]

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=b"bytes")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = MFDSSource(
        client=client,
        listing_url="https://www.mfds.go.kr/brd/m_218/list.do",
        doc_path_prefix="/brd/",
        sleep=fake_sleep,
        clock=fake_clock,
    )
    await source.load_robots()

    # First fetch — no prior request, rate limiter must NOT sleep.
    await source.fetch_document("https://www.mfds.go.kr/brd/m_218/view.do?seq=1")
    assert slept == [], "First fetch must not trigger rate-limiter sleep"

    # Second fetch immediately after (clock still at 0.0) — rate limiter MUST sleep.
    await source.fetch_document("https://www.mfds.go.kr/brd/m_218/view.do?seq=2")

    assert len(slept) == 1, (
        "Rate limiter must call sleep exactly once between two consecutive fetches. "
        "If this fails, RateLimiter.acquire() is not wired into fetch_document()."
    )
    assert slept[0] >= MIN_INTERVAL, (
        f"Sleep duration {slept[0]:.3f}s must be >= min_interval {MIN_INTERVAL}s. "
        "The rate limiter is not enforcing the configured minimum interval."
    )
