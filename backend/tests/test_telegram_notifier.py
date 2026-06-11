"""Tests for telegram_notifier (Stage 8 Day 4)."""

import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.telegram_notifier import send_message


@pytest.mark.asyncio
async def test_disabled_returns_false():
    with patch.dict(os.environ, {"TELEGRAM_DISABLED": "1", "TELEGRAM_BOT_TOKEN": "x"}):
        result = await send_message("hello")
    assert result is False


@pytest.mark.asyncio
async def test_no_token_returns_false():
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}, clear=False):
        # Inside the patch, the value is "" (empty string, falsy)
        # send_message checks `if not bot_token` → returns False
        result = await send_message("hello")
    assert result is False


@pytest.mark.asyncio
async def test_no_chat_id_returns_false():
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "",
    }, clear=False):
        # Inside the patch, TELEGRAM_CHAT_ID is "" (falsy)
        result = await send_message("hello")
    assert result is False


@pytest.mark.asyncio
async def test_success_returns_true():
    """Mock httpx to return 200, verify call."""
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "12345",
    }):
        with patch("app.services.telegram_notifier.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            result = await send_message("test message")
            assert result is True
            mock_client.post.assert_called_once()
            call = mock_client.post.call_args
            assert "bottest_token" in call.args[0]
            assert call.kwargs["json"]["chat_id"] == "12345"
            assert call.kwargs["json"]["text"] == "test message"


@pytest.mark.asyncio
async def test_http_error_returns_false():
    """Non-200 response → False (no raise)."""
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "12345",
    }):
        with patch("app.services.telegram_notifier.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.text = "bad request"
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            result = await send_message("test")
            assert result is False


@pytest.mark.asyncio
async def test_network_error_returns_false():
    """Network/timeout → False (no raise)."""
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHAT_ID": "12345",
    }):
        with patch("app.services.telegram_notifier.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("network down"))
            MockClient.return_value = mock_client

            result = await send_message("test")
            assert result is False


@pytest.mark.asyncio
async def test_truncates_long_message():
    """Telegram limit 4096 chars — auto-truncate."""
    long_text = "x" * 5000
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "t",
        "TELEGRAM_CHAT_ID": "1",
    }):
        with patch("app.services.telegram_notifier.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_client

            await send_message(long_text)
            sent_text = mock_client.post.call_args.kwargs["json"]["text"]
            assert len(sent_text) == 4096
