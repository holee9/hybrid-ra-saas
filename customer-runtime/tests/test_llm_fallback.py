"""T-007: llm_fallback.py — injectable httpx client + _assert_local guard 테스트."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock


EN_TEXT = """
Device Name: CardioScan Pro 3000
Intended Use: Cardiac monitoring.
Product Code: CSP-3000-US
"""


def _make_fake_client(response_fields: dict) -> MagicMock:
    """Create a mock httpx.AsyncClient that returns the given fields JSON."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json = MagicMock(return_value={
        "response": json.dumps(response_fields)
    })

    mock_client = MagicMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_inject_fake_client_returns_llm_extraction():
    from app.schemas.parse import ExtractionStage
    from app.services.parser_engine.llm_fallback import extract

    fake_client = _make_fake_client({
        "device_name": "CardioScan Pro 3000",
        "intended_use": "Cardiac monitoring",
    })

    result = await extract(
        EN_TEXT,
        ["device_name", "intended_use"],
        llm_client=fake_client,
        base_url="http://localhost:11434",
    )

    assert "device_name" in result
    assert "intended_use" in result
    for fe in result.values():
        assert fe.stage == ExtractionStage.LLM
        assert 0.0 <= fe.confidence <= 1.0


def test_assert_local_raises_for_external_url():
    from app.services.parser_engine.llm_fallback import _assert_local

    with pytest.raises(ValueError, match="localhost"):
        _assert_local("http://external.example.com")


def test_assert_local_raises_for_public_ip():
    from app.services.parser_engine.llm_fallback import _assert_local

    with pytest.raises(ValueError):
        _assert_local("http://192.168.1.100:11434")


def test_assert_local_passes_for_localhost():
    from app.services.parser_engine.llm_fallback import _assert_local

    # Should not raise
    _assert_local("http://localhost:11434")


def test_assert_local_passes_for_127_0_0_1():
    from app.services.parser_engine.llm_fallback import _assert_local

    _assert_local("http://127.0.0.1:11434")


def test_assert_local_passes_for_ollama_service():
    """Docker internal service name 'ollama' should be allowed."""
    from app.services.parser_engine.llm_fallback import _assert_local

    _assert_local("http://ollama:11434")


@pytest.mark.asyncio
async def test_external_url_guard_raises_before_client_call():
    """mock client with external URL → guard raises, 0 calls made."""
    from app.services.parser_engine.llm_fallback import extract

    fake_client = _make_fake_client({"device_name": "X"})

    with pytest.raises(ValueError):
        await extract(
            EN_TEXT,
            ["device_name"],
            llm_client=fake_client,
            base_url="http://external.example.com",
        )

    # Guard must raise before any HTTP call
    fake_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_empty_fields_returns_empty():
    from app.services.parser_engine.llm_fallback import extract

    fake_client = _make_fake_client({})
    result = await extract(EN_TEXT, [], llm_client=fake_client, base_url="http://localhost:11434")
    assert result == {}
