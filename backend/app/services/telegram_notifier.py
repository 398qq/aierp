"""Lightweight Telegram notifier — sends messages to a chat via bot API.

Stage 8 Day 4: notifies the sales user (or a group) when a commission is
auto-created. Also useful for any other business event that should ping
Telegram (approval needed, payment received, etc.).

Uses httpx (already a project dep). No retry — fail fast and log.

Config via env (loaded lazily at call time, not module import):
    TELEGRAM_BOT_TOKEN  — get from @BotFather
    TELEGRAM_CHAT_ID    — chat / user id to send to
    TELEGRAM_DISABLED   — set '1' to silence in dev/test (default unset)

Usage:
    from app.services.telegram_notifier import send_message
    await send_message("Hello, world!")
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


async def send_message(text: str, chat_id: Optional[str] = None) -> bool:
    """Send a text message to a Telegram chat. Returns True on success.

    If TELEGRAM_DISABLED=1 (or TELEGRAM_BOT_TOKEN unset), logs and returns
    False without raising — the caller decides whether that's fatal.

    Format: HTML (so we can use <b> for emphasis). Truncated at 4096
    chars per Telegram limits.
    """
    if os.environ.get("TELEGRAM_DISABLED") == "1":
        logger.info("telegram disabled, skip: %s", text[:80])
        return False

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skip: %s", text[:80])
        return False

    target = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not target:
        logger.warning("no chat_id provided and TELEGRAM_CHAT_ID unset")
        return False

    # Truncate to Telegram's limit
    payload_text = text[:4096]
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target,
        "text": payload_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload)
        if r.status_code == 200:
            logger.info("telegram sent to %s: %s", target, payload_text[:60])
            return True
        logger.error("telegram send failed %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as exc:  # network / timeout / DNS
        logger.exception("telegram send error: %s", exc)
        return False
