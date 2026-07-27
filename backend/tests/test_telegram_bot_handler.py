"""Regression tests for the legacy Telegram inbound poller."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.services import telegram_bot_handler


def test_polling_can_be_disabled_without_disabling_outbound(monkeypatch):
    """The inbound poller has its own kill switch."""
    monkeypatch.setattr(telegram_bot_handler.settings, "TELEGRAM_DISABLED", "0")
    monkeypatch.setattr(
        telegram_bot_handler.settings,
        "TELEGRAM_POLLING_DISABLED",
        "1",
    )

    assert telegram_bot_handler._is_disabled() is True


@pytest.mark.asyncio
async def test_polling_lock_is_refreshed_after_each_long_poll(monkeypatch):
    """A 60-second lock must renew after every ~30-second getUpdates call."""
    monkeypatch.setattr(telegram_bot_handler, "_is_disabled", lambda: False)
    monkeypatch.setattr(telegram_bot_handler, "_bot_token", lambda: "123:test")
    acquire = AsyncMock(return_value=True)
    poll = AsyncMock(side_effect=[1, asyncio.CancelledError()])
    refresh = AsyncMock()
    release = AsyncMock()
    monkeypatch.setattr(telegram_bot_handler, "_acquire_polling_lock", acquire)
    monkeypatch.setattr(telegram_bot_handler, "_poll_once", poll)
    monkeypatch.setattr(telegram_bot_handler, "_refresh_polling_lock", refresh)
    monkeypatch.setattr(telegram_bot_handler, "_release_polling_lock", release)

    with pytest.raises(asyncio.CancelledError):
        await telegram_bot_handler.run_polling_loop()

    refresh.assert_awaited_once()
    release.assert_awaited_once()
