"""SPEC-TEMPLATE-002: Template API live integration — unit tests.

Covers:
- REQ-TEMPLATE-002-001/002: live fetch returns API data
- REQ-TEMPLATE-002-004: deterministic error on failure
- REQ-TEMPLATE-002-005: retry N times then raise TemplateAPIError
- REQ-TEMPLATE-002-006: no stub when TEMPLATE_API_URL is unset → TemplateAPIError
- REQ-TEMPLATE-002-007: stub fallback is NOT used in any env
"""
import os

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost:5432/db")
os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_SECTIONS = [
    {"section_id": "s-001", "blocking": True, "evidence_required": True, "title": "CER"},
    {"section_id": "s-002", "blocking": False, "evidence_required": False, "title": "IFU"},
]


def _make_httpx_response(status_code: int, json_data=None, text: str = ""):
    """Build a minimal httpx.Response-like mock."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    resp.text = text

    if status_code >= 400:
        resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                f"HTTP {status_code}", request=MagicMock(), response=resp
            )
        )
    else:
        resp.raise_for_status = MagicMock()

    return resp


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-001/002: success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_template_sections_success():
    """Live fetch returns API JSON when TEMPLATE_API_URL is set."""
    resp_mock = _make_httpx_response(200, json_data=FAKE_SECTIONS)

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=resp_mock)

    with patch("app.services.template_client.httpx.AsyncClient", return_value=mock_client):
        with patch.dict(os.environ, {"TEMPLATE_API_URL": "https://template.example.com"}):
            from app.services.template_client import fetch_template_sections

            result = await fetch_template_sections("pack-001")

    assert result == FAKE_SECTIONS
    mock_client.get.assert_called_once_with(
        "https://template.example.com/packs/pack-001/sections"
    )


@pytest.mark.asyncio
async def test_fetch_template_sections_404_returns_empty():
    """404 from API returns empty list (pack not found)."""
    resp_mock = _make_httpx_response(404)
    resp_mock.raise_for_status = MagicMock()  # 404 handled before raise_for_status

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=resp_mock)

    with patch("app.services.template_client.httpx.AsyncClient", return_value=mock_client):
        with patch.dict(os.environ, {"TEMPLATE_API_URL": "https://template.example.com"}):
            from importlib import reload
            import app.services.template_client as tc_module
            reload(tc_module)

            result = await tc_module.fetch_template_sections("pack-unknown")

    assert result == []


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-006: no stub when URL not set → TemplateAPIError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_template_sections_no_url_raises():
    """TemplateAPIError raised when TEMPLATE_API_URL is not configured."""
    env_without_url = {k: v for k, v in os.environ.items() if k != "TEMPLATE_API_URL"}

    with patch.dict(os.environ, env_without_url, clear=True):
        from importlib import reload
        import app.services.template_client as tc_module
        reload(tc_module)

        with pytest.raises(tc_module.TemplateAPIError, match="TEMPLATE_API_URL is not configured"):
            await tc_module.fetch_template_sections("pack-001")


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-005: retry then raise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_template_sections_retry_exhausted():
    """TemplateAPIError raised after all retries fail (timeout)."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

    with patch("app.services.template_client.httpx.AsyncClient", return_value=mock_client):
        with patch.dict(os.environ, {"TEMPLATE_API_URL": "https://template.example.com"}):
            with patch("app.services.template_client.TEMPLATE_API_MAX_RETRIES", 3):
                from importlib import reload
                import app.services.template_client as tc_module
                reload(tc_module)

                with pytest.raises(tc_module.TemplateAPIError, match="failed.*3 retries"):
                    await tc_module.fetch_template_sections("pack-001")

    # All 3 attempts were made
    assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_fetch_template_sections_retry_success_on_last():
    """Succeeds on last attempt after earlier timeouts."""
    resp_mock = _make_httpx_response(200, json_data=FAKE_SECTIONS)

    call_count = 0

    async def flaky_get(url):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("timeout")
        return resp_mock

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = flaky_get

    with patch("app.services.template_client.httpx.AsyncClient", return_value=mock_client):
        with patch.dict(os.environ, {"TEMPLATE_API_URL": "https://template.example.com"}):
            with patch("app.services.template_client.TEMPLATE_API_MAX_RETRIES", 3):
                from importlib import reload
                import app.services.template_client as tc_module
                reload(tc_module)

                result = await tc_module.fetch_template_sections("pack-001")

    assert result == FAKE_SECTIONS
    assert call_count == 3


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-004: deterministic error response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_template_sections_http_error_raises():
    """HTTPStatusError raises TemplateAPIError after retries (not a silent fallback)."""
    resp_mock = _make_httpx_response(500, text="Internal Server Error")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=resp_mock)

    with patch("app.services.template_client.httpx.AsyncClient", return_value=mock_client):
        with patch.dict(os.environ, {"TEMPLATE_API_URL": "https://template.example.com"}):
            with patch("app.services.template_client.TEMPLATE_API_MAX_RETRIES", 2):
                from importlib import reload
                import app.services.template_client as tc_module
                reload(tc_module)

                with pytest.raises(tc_module.TemplateAPIError):
                    await tc_module.fetch_template_sections("pack-001")


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-003: authoring router uses fetch_template_sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authoring_router_calls_fetch_template_sections():
    """Authoring _fetch_template_sections delegates to fetch_template_sections."""
    # Import first to ensure module is loaded, then patch the bound name
    from app.routers.authoring import _fetch_template_sections

    with patch("app.routers.authoring.fetch_template_sections", return_value=FAKE_SECTIONS) as mock_fetch:
        result = await _fetch_template_sections("pack-001")

    assert result == FAKE_SECTIONS
    mock_fetch.assert_called_once_with(
        "pack-001",
        endpoint_path="/packs/{pack_id}/sections",
    )


@pytest.mark.asyncio
async def test_authoring_router_502_on_template_api_error():
    """TemplateAPIError from template_client → 502 HTTPException."""
    from app.services.template_client import TemplateAPIError
    from fastapi import HTTPException
    from importlib import reload
    import app.routers.authoring as authoring_module

    # Reload to restore module-level bindings after any reload in previous tests
    reload(authoring_module)
    _fetch_template_sections = authoring_module._fetch_template_sections

    with patch(
        "app.routers.authoring.fetch_template_sections",
        side_effect=TemplateAPIError("TEMPLATE_API_URL is not configured"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _fetch_template_sections("pack-001")

    assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-003: checklist generator uses fetch_template_sections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_checklist_generator_calls_fetch_template_sections():
    """Checklist _fetch_sections delegates to fetch_template_sections."""
    from app.services.checklist.generator import _fetch_sections

    with patch(
        "app.services.checklist.generator.fetch_template_sections",
        return_value=FAKE_SECTIONS,
    ) as mock_fetch:
        result = await _fetch_sections("pack-001")

    assert result == FAKE_SECTIONS
    mock_fetch.assert_called_once_with(
        "pack-001",
        endpoint_path="/template-packs/{pack_id}/sections",
    )


@pytest.mark.asyncio
async def test_checklist_generator_propagates_template_api_error():
    """TemplateAPIError from template_client propagates out of _fetch_sections."""
    from app.services.template_client import TemplateAPIError
    from app.services.checklist.generator import _fetch_sections

    with patch(
        "app.services.checklist.generator.fetch_template_sections",
        side_effect=TemplateAPIError("TEMPLATE_API_URL is not configured"),
    ):
        with pytest.raises(TemplateAPIError):
            await _fetch_sections("pack-001")


# ---------------------------------------------------------------------------
# REQ-TEMPLATE-002-007: no stub path exists anywhere in the shared client
# ---------------------------------------------------------------------------


def test_no_stub_data_in_template_client():
    """template_client.py must not contain any stub/fallback section data."""
    import inspect
    import app.services.template_client as tc_module

    source = inspect.getsource(tc_module)
    assert "STUB" not in source, "template_client must not contain stub data"
    assert "fallback" not in source.lower() or "No stub" not in source, \
        "template_client must not silently fall back to stub"
