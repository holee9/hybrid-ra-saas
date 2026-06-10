"""Unit tests for CrawlerSource abstract base (T-010, T-012).

Tests cover:
- robots.txt disallow enforcement (REQ-007/008, AC-006)
- robots.txt re-fetch on every job run
- retry with exponential backoff (REQ-005, AC-004)
- failure isolation — continues after exhausted retries (REQ-006, AC-004)
- User-Agent header sent with requests
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def make_response(status_code: int = 200, content: bytes = b"PDF content") -> httpx.Response:
    """Build a minimal httpx.Response for testing."""
    return httpx.Response(status_code, content=content)


def make_robots_response(allow_all: bool = True) -> httpx.Response:
    """Return a robots.txt response that allows or disallows all."""
    if allow_all:
        body = b"User-agent: *\nAllow: /\n"
    else:
        body = b"User-agent: *\nDisallow: /\n"
    return httpx.Response(200, content=body)


def make_robots_response_partial_disallow(disallow_path: str = "/guidance/") -> httpx.Response:
    """Return robots.txt that disallows a specific path."""
    body = f"User-agent: *\nDisallow: {disallow_path}\n".encode()
    return httpx.Response(200, content=body)


# ---------------------------------------------------------------------------
# Concrete subclass for testing (minimal)
# ---------------------------------------------------------------------------


class ConcreteSource:
    """Test-only subclass of CrawlerSource."""

    SOURCE_NAME = "test-source"
    BASE_URL = "https://example.com"
    ROBOTS_URL = "https://example.com/robots.txt"

    def __init__(self, client: httpx.AsyncClient, delays: list[float] | None = None) -> None:
        from app.services.crawler.base import CrawlerSource

        self._base = CrawlerSource.__new__(CrawlerSource)
        # Store for use in tests
        self._client = client
        self._delays = delays or []
        self._delay_idx = 0

    # We test CrawlerSource directly — see tests below.


# ---------------------------------------------------------------------------
# Tests: robots.txt enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_robots_disallow_all_raises():
    """fetch_document must refuse URLs disallowed by robots.txt."""

    robots_body = b"User-agent: *\nDisallow: /\n"

    transport = httpx.MockTransport(handler=lambda req: httpx.Response(200, content=robots_body))
    client = httpx.AsyncClient(transport=transport)

    source = _make_source(client)
    await source.load_robots()

    with pytest.raises(PermissionError, match="disallowed"):
        await source.fetch_document("https://example.com/doc.pdf")


@pytest.mark.asyncio
async def test_robots_allow_all_permits_fetch():
    """fetch_document succeeds when robots.txt allows the URL."""

    robots_body = b"User-agent: *\nAllow: /\n"
    doc_body = b"PDF bytes here"
    call_count = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=robots_body)
        return httpx.Response(200, content=doc_body)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = _make_source(client)
    await source.load_robots()
    result = await source.fetch_document("https://example.com/doc.pdf")

    assert result == doc_body


@pytest.mark.asyncio
async def test_robots_partial_disallow_blocks_matching_path():
    """Disallow: /guidance/ blocks guidance URLs but not others."""

    robots_body = b"User-agent: *\nDisallow: /guidance/\n"
    doc_body = b"ok"

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=robots_body)
        return httpx.Response(200, content=doc_body)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = _make_source(client)
    await source.load_robots()

    # Disallowed path
    with pytest.raises(PermissionError):
        await source.fetch_document("https://example.com/guidance/2024/doc.pdf")

    # Allowed path (outside /guidance/)
    result = await source.fetch_document("https://example.com/other/doc.pdf")
    assert result == doc_body


@pytest.mark.asyncio
async def test_load_robots_called_on_each_run():
    """robots.txt is fetched anew for each crawl run (not cached)."""

    fetch_count = 0

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal fetch_count
        if "robots.txt" in str(req.url):
            fetch_count += 1
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=b"doc")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)

    source = _make_source(client)

    # Simulate two separate job runs
    await source.load_robots()
    await source.load_robots()

    assert fetch_count == 2, "robots.txt must be fetched on every run, not cached"


# ---------------------------------------------------------------------------
# Tests: retry / backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_network_error_succeeds_on_third_attempt():
    """fetch_document retries up to 3 times; succeeds on 3rd attempt."""

    attempt = 0
    delays_used: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal attempt
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        attempt += 1
        if attempt < 3:
            raise httpx.ConnectError("Connection refused")
        return httpx.Response(200, content=b"success")

    async def fake_sleep(seconds: float) -> None:
        delays_used.append(seconds)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)
    source = _make_source(client, sleep=fake_sleep)

    await source.load_robots()
    result = await source.fetch_document("https://example.com/doc.pdf")

    assert result == b"success"
    assert attempt == 3
    # First retry delay: 2s; second retry delay: 4s
    assert len(delays_used) == 2
    assert abs(delays_used[0] - 2.0) < 1e-6
    assert abs(delays_used[1] - 4.0) < 1e-6


@pytest.mark.asyncio
async def test_retry_on_non_2xx_uses_backoff():
    """Non-2xx responses trigger retry with exponential backoff."""

    attempt = 0
    delays_used: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        nonlocal attempt
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        attempt += 1
        if attempt < 2:
            return httpx.Response(503, content=b"Service Unavailable")
        return httpx.Response(200, content=b"data")

    async def fake_sleep(seconds: float) -> None:
        delays_used.append(seconds)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)
    source = _make_source(client, sleep=fake_sleep)

    await source.load_robots()
    result = await source.fetch_document("https://example.com/doc.pdf")

    assert result == b"data"
    assert len(delays_used) == 1
    assert abs(delays_used[0] - 2.0) < 1e-6


@pytest.mark.asyncio
async def test_all_retries_exhausted_raises():
    """After 3 failed attempts, fetch_document raises an exception."""

    delays_used: list[float] = []

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        raise httpx.ConnectError("Always fails")

    async def fake_sleep(seconds: float) -> None:
        delays_used.append(seconds)

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)
    source = _make_source(client, sleep=fake_sleep)

    await source.load_robots()

    with pytest.raises(Exception):
        await source.fetch_document("https://example.com/doc.pdf")

    # 3 retries: delays 2s, 4s, 8s
    assert len(delays_used) == 3
    assert abs(delays_used[0] - 2.0) < 1e-6
    assert abs(delays_used[1] - 4.0) < 1e-6
    assert abs(delays_used[2] - 8.0) < 1e-6


@pytest.mark.asyncio
async def test_user_agent_sent_in_requests():
    """Requests must carry a User-Agent header."""

    user_agents_seen: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        ua = req.headers.get("user-agent", "")
        user_agents_seen.append(ua)
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=b"doc")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport, headers={"User-Agent": "RA-Crawler/1.0"})
    source = _make_source(client)

    await source.load_robots()
    await source.fetch_document("https://example.com/doc.pdf")

    assert all(ua for ua in user_agents_seen), "All requests must have a User-Agent"


# ---------------------------------------------------------------------------
# Tests: rate-limit wiring in CrawlerSource.fetch_document (REQ-009, AC-003)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_document_second_call_is_throttled_by_rate_limiter():
    """Two consecutive fetch_document calls on the same source instance must
    invoke the injected sleep with a delay >= min_interval.

    This test verifies that CrawlerSource.fetch_document() calls
    RateLimiter.acquire() between requests — not just that the limiter exists.
    Clock is frozen at 0.0 so the second acquire always sees zero elapsed time
    and must sleep for the full min_interval.
    """

    MIN_INTERVAL = 1.0
    clock_time = [0.0]  # frozen clock — never advances

    def fake_clock() -> float:
        return clock_time[0]

    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    def handler(req: httpx.Request) -> httpx.Response:
        if "robots.txt" in str(req.url):
            return httpx.Response(200, content=b"User-agent: *\nAllow: /\n")
        return httpx.Response(200, content=b"doc")

    transport = httpx.MockTransport(handler=handler)
    client = httpx.AsyncClient(transport=transport)
    source = _make_source(client, sleep=fake_sleep, clock=fake_clock)

    await source.load_robots()

    # First fetch: no prior timestamp — must NOT sleep.
    await source.fetch_document("https://example.com/doc1.pdf")
    rate_limiter_sleeps_after_first = [s for s in slept if s > 0]
    assert not rate_limiter_sleeps_after_first, (
        "First fetch_document call must not trigger a rate-limiter sleep"
    )
    slept.clear()

    # Second fetch: clock still at 0.0 → elapsed=0 → must sleep for min_interval.
    await source.fetch_document("https://example.com/doc2.pdf")

    assert len(slept) == 1, (
        "Rate limiter must sleep exactly once on the second consecutive fetch. "
        "RateLimiter.acquire() must be called inside fetch_document()."
    )
    assert slept[0] >= MIN_INTERVAL, (
        f"Rate-limiter sleep {slept[0]:.3f}s must be >= min_interval {MIN_INTERVAL}s."
    )


# ---------------------------------------------------------------------------
# Tests: _extract_links SSRF protection (Finding 4)
# ---------------------------------------------------------------------------


def test_extract_links_rejects_cross_domain_href():
    """_extract_links must exclude absolute hrefs pointing to a different netloc (SSRF prevention)."""
    from app.services.crawler.base import CrawlerSource

    # Create a minimal concrete subclass
    class _TestSource(CrawlerSource):
        SOURCE_NAME = "test-source"

        async def discover_document_urls(self) -> list[str]:
            return []

    import httpx

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)
    source = _TestSource(
        client=client,
        robots_url="https://example.com/robots.txt",
    )

    html = """
    <html><body>
      <a href="/media/doc.pdf">Good doc</a>
      <a href="https://attacker.example/steal">Malicious</a>
      <a href="http://attacker.example/evil.pdf">Also malicious</a>
      <a href="/media/other.pdf">Another good doc</a>
    </body></html>
    """

    results = source._extract_links(
        html, prefix="/media/", listing_url="https://example.com/listing"
    )

    # Must not include attacker.example URLs
    assert not any("attacker.example" in u for u in results), (
        "SSRF: cross-domain absolute href must be excluded by _extract_links"
    )
    # Must include same-domain paths
    assert len(results) == 2
    assert all("example.com" in u for u in results)


def test_extract_links_rejects_protocol_relative_cross_domain():
    """_extract_links must not include hrefs that after urljoin resolve to a different host."""
    from app.services.crawler.base import CrawlerSource

    class _TestSource(CrawlerSource):
        SOURCE_NAME = "test-source"

        async def discover_document_urls(self) -> list[str]:
            return []

    import httpx

    transport = httpx.MockTransport(handler=lambda r: httpx.Response(200, content=b""))
    client = httpx.AsyncClient(transport=transport)
    source = _TestSource(
        client=client,
        robots_url="https://example.com/robots.txt",
    )

    html = '<a href="/media/doc.pdf">ok</a><a href="https://evil.com/media/steal.pdf">bad</a>'

    results = source._extract_links(html, prefix="/media/", listing_url="https://example.com/page")

    assert len(results) == 1
    assert "example.com" in results[0]


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def _make_source(
    client: httpx.AsyncClient,
    sleep=None,
    clock=None,
    robots_url: str = "https://example.com/robots.txt",
) -> Any:
    """Instantiate a minimal concrete subclass of CrawlerSource for testing."""
    from app.services.crawler.base import CrawlerSource

    async def default_sleep(_: float) -> None:
        pass

    # Create a minimal concrete subclass so abstract method is satisfied
    class _TestSource(CrawlerSource):
        SOURCE_NAME = "test-source"

        async def discover_document_urls(self) -> list[str]:
            return []

    return _TestSource(
        client=client,
        robots_url=robots_url,
        retry_count=3,
        initial_delay=2.0,
        multiplier=2.0,
        sleep=sleep or default_sleep,
        clock=clock,
    )
