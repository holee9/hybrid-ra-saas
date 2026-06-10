"""Unit tests for token-bucket rate limiter (REQ-CRAWLER-009, AC-003).

All timing is injected/mocked — no real sleeps.
"""
import pytest

from app.core.ratelimit import RateLimiter


class FakeClock:
    """Injectable monotonic clock for deterministic tests."""

    def __init__(self, start: float = 0.0) -> None:
        self._time = start

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


@pytest.mark.asyncio
async def test_first_request_does_not_sleep():
    """First request is always allowed immediately (no wait)."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    clock = FakeClock(0.0)
    limiter = RateLimiter(min_interval=1.0, clock=clock.now, sleep=fake_sleep)

    await limiter.acquire()

    assert slept == [], "First request must not sleep"


@pytest.mark.asyncio
async def test_second_request_within_interval_sleeps():
    """Second request within 1s interval must sleep the remaining gap."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    clock = FakeClock(0.0)
    limiter = RateLimiter(min_interval=1.0, clock=clock.now, sleep=fake_sleep)

    await limiter.acquire()         # first — no sleep
    clock.advance(0.3)              # 300ms later
    await limiter.acquire()         # second — should sleep ~0.7s

    assert len(slept) == 1
    assert abs(slept[0] - 0.7) < 1e-6


@pytest.mark.asyncio
async def test_request_after_full_interval_does_not_sleep():
    """Request arriving after the full interval elapses must not sleep."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    clock = FakeClock(0.0)
    limiter = RateLimiter(min_interval=1.0, clock=clock.now, sleep=fake_sleep)

    await limiter.acquire()       # first
    clock.advance(1.5)            # 1.5s later — more than min_interval
    await limiter.acquire()       # second — no sleep needed

    assert slept == []


@pytest.mark.asyncio
async def test_sources_are_independent():
    """Two limiters (one per source) are fully independent."""
    slept_a: list[float] = []
    slept_b: list[float] = []

    async def sleep_a(s: float) -> None:
        slept_a.append(s)

    async def sleep_b(s: float) -> None:
        slept_b.append(s)

    clock = FakeClock(0.0)
    limiter_fda = RateLimiter(min_interval=1.0, clock=clock.now, sleep=sleep_a)
    limiter_mfds = RateLimiter(min_interval=1.0, clock=clock.now, sleep=sleep_b)

    # FDA: first request at t=0
    await limiter_fda.acquire()
    # MFDS: first request also at t=0 — should NOT sleep (independent limiter)
    await limiter_mfds.acquire()

    assert slept_a == []
    assert slept_b == []
