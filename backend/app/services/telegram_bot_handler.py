"""Telegram inbound bot handler — code expert assistant.

Receives messages from @Wechabot_bot users, forwards them to the AI code model
(MiniMax-M3 by default), and replies via Telegram bot API.

Long-polling mode (no public HTTPS endpoint required). Started by main.py
lifespan as a background asyncio task.

Config (env, loaded lazily):
    TELEGRAM_BOT_TOKEN      bot token from @BotFather
    TELEGRAM_DISABLED       '1' to silence the bot (default unset = enabled)
    AI_CODE_MODEL           model id, defaults to settings.AI_CODE_MODEL

Usage (in main.py lifespan):
    from app.services.telegram_bot_handler import run_polling_loop
    task = asyncio.create_task(run_polling_loop())
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"
POLL_INTERVAL_S = 0.5
# Telegram standard long-poll is 30s. Using 25s stays well under typical NAT/LB
# idle timeouts (60s+) while letting Telegram hold the connection long enough
# to actually deliver updates (5s causes Server disconnected on every poll).
POLL_LONG_TIMEOUT_S = 25
POLL_CLIENT_TIMEOUT_S = POLL_LONG_TIMEOUT_S + 30
MAX_MESSAGE_LEN = 4000  # Telegram limit is 4096, leave headroom


CODE_EXPERT_SYSTEM_PROMPT = """你是一位资深软件工程师，精通多种技术栈：Python、JavaScript/TypeScript、Go、Rust、Java、C/C++、SQL、Shell、Vue/React、Solidity 等。

回答风格：
- 先给可运行的方案，再解释为什么这样写
- 代码必须能跑，不写伪代码（除非显式说明）
- 涉及性能 / 安全 / 可维护性 / 边界条件时主动指出
- 不确定的地方明说，不要瞎编 API 或库
- 中文为主，技术名词、库名、命令保持英文
- 复杂问题先列要点，再给完整代码块

输出格式（适配 Telegram HTML）：
- 标题用 <b>...</b>
- 行内代码用 <code>...</code>
- 代码块用三反引号 + 语言名
- 长答案分段，列表用 • 或 1./2./3.
- 不要用 markdown 标题（# / ##），Telegram 不渲染
"""


def _bot_token() -> str | None:
    token = settings.TELEGRAM_BOT_TOKEN
    return token or None


def _is_disabled() -> bool:
    return settings.TELEGRAM_DISABLED == "1"


async def _send_text(chat_id: int, text: str) -> bool:
    """Send a plain text message via Telegram bot API.

    Splits long messages into multiple chunks (Telegram 4096 char limit).
    Returns True if every chunk sent successfully.
    """
    token = _bot_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set, cannot send reply")
        return False

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    chunks: list[str] = []
    if len(text) <= MAX_MESSAGE_LEN:
        chunks.append(text)
    else:
        # Split on newlines to keep paragraphs intact when possible.
        remaining = text
        while len(remaining) > MAX_MESSAGE_LEN:
            cut = remaining.rfind("\n", 0, MAX_MESSAGE_LEN)
            if cut <= 0:
                cut = MAX_MESSAGE_LEN
            chunks.append(remaining[:cut])
            remaining = remaining[cut:].lstrip("\n")
        if remaining:
            chunks.append(remaining)

    ok = True
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            for chunk in chunks:
                payload = {
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                }
                r = await client.post(url, json=payload)
                if r.status_code != 200:
                    logger.error(
                        "telegram send failed %s: %s", r.status_code, r.text[:200]
                    )
                    ok = False
                # Tiny gap to avoid hitting rate limits on long responses.
                if len(chunks) > 1:
                    await asyncio.sleep(0.3)
    except Exception as exc:  # network / timeout / DNS
        logger.exception("telegram send error: %s", exc)
        return False
    return ok


def _welcome_text() -> str:
    return (
        "👋 你好，我是 <b>代码高手</b>，AI 驱动。\n\n"
        "直接发代码问题给我——算法、Bug、review、架构、重构、性能，"
        "Python / JS / TS / Go / Rust / Java / SQL 都行。\n\n"
        "<b>命令</b>：\n"
        "/help  用法说明\n"
        "/model 当前模型\n"
        "/reset 清空上下文"
    )


def _help_text() -> str:
    return (
        "📖 <b>用法</b>\n\n"
        "• 直接发问题或代码片段\n"
        "• 多轮对话按顺序保留上下文\n"
        "• 长输出会自动分多条发送\n\n"
        "<b>命令</b>：\n"
        "/start  欢迎\n"
        "/help   帮助\n"
        "/model  查看当前模型\n"
        "/reset  清空对话上下文"
    )


# In-memory per-chat message history. Kept short to control token usage.
_MAX_HISTORY = 12
_chat_histories: dict[int, list[dict]] = {}


def _push_history(chat_id: int, role: str, content: str) -> None:
    history = _chat_histories.setdefault(chat_id, [])
    history.append({"role": role, "content": content})
    if len(history) > _MAX_HISTORY:
        history[:] = history[-_MAX_HISTORY:]


def _build_messages(chat_id: int, user_text: str) -> list[dict]:
    """Build the messages array: system + recent history + new user turn."""
    history = list(_chat_histories.get(chat_id, []))
    return [
        {"role": "system", "content": CODE_EXPERT_SYSTEM_PROMPT},
        *history,
        {"role": "user", "content": user_text},
    ]


async def _handle_update(update: dict[str, Any]) -> None:
    """Process a single Telegram update (message or edited_message)."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    sender = message.get("from") or {}
    sender_name = sender.get("username") or sender.get("first_name") or "anon"

    if not chat_id or not text:
        return

    logger.info(
        "code bot <- chat=%s user=%s text=%r",
        chat_id,
        sender_name,
        text[:120],
    )

    # Slash commands.
    cmd = text.split()[0].lower()
    if cmd == "/start":
        await _send_text(chat_id, _welcome_text())
        return
    if cmd == "/help":
        await _send_text(chat_id, _help_text())
        return
    if cmd == "/model":
        model = settings.AI_CODE_MODEL or settings.AI_MODEL
        await _send_text(chat_id, f"🤖 当前模型：<code>{model}</code>")
        return
    if cmd == "/reset":
        _chat_histories.pop(chat_id, None)
        await _send_text(chat_id, "🧹 上下文已清空。")
        return

    # Regular message → forward to AI with rolling history.
    messages = _build_messages(chat_id, text)
    model = settings.AI_CODE_MODEL or settings.AI_MODEL
    try:
        from app.services.ai.client import ai_client

        reply = await ai_client.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=4096,
            model=model,
        )
    except Exception as exc:
        logger.exception("code model call failed: %s", exc)
        reply = (
            f"⚠️ 模型调用失败：<code>{type(exc).__name__}</code>\n"
            f"{str(exc)[:300]}"
        )

    _push_history(chat_id, "user", text)
    _push_history(chat_id, "assistant", reply)

    # Strip m3 thinking trace (<think>...</think>) before sending.
    # Telegram's HTML parser rejects unknown tags with 400.
    import re

    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL).strip()

    await _send_text(chat_id, reply)


async def _poll_once(offset: int | None) -> int | None:
    """Fetch new updates via long-polling. Returns next offset to use."""
    token = _bot_token()
    if not token:
        return offset

    url = f"{TELEGRAM_API_BASE}/bot{token}/getUpdates"
    params: dict[str, Any] = {
        "timeout": POLL_LONG_TIMEOUT_S,
        "allowed_updates": ["message", "edited_message"],
    }
    if offset is not None:
        params["offset"] = offset

    # Sandbox blocks direct egress; must go through HTTP(S) proxy from env.
    # trust_env=False avoids ALL_PROXY=socks5 (would need socksio); explicit
    # proxy= from HTTPS_PROXY/HTTP_PROXY is the only path that actually works.
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
    try:
        async with httpx.AsyncClient(
            trust_env=False,
            proxy=proxy,
            timeout=POLL_CLIENT_TIMEOUT_S,
        ) as client:
            r = await client.get(url, params=params)
    except httpx.RemoteProtocolError:
        # Telegram closed the long-poll connection without a response (timeout
        # elapsed, no updates). Normal — treat as "no new updates", don't spam
        # the log.
        return offset
    except Exception as exc:
        logger.exception("getUpdates network error: %s", exc)
        return offset

    if r.status_code != 200:
        logger.error("getUpdates failed %s: %s", r.status_code, r.text[:200])
        return offset

    data = r.json()
    if not data.get("ok"):
        logger.error("getUpdates returned not-ok: %s", data)
        return offset

    next_offset = offset
    for update in data.get("result", []):
        update_id = update.get("update_id")
        if update_id is None:
            continue
        try:
            await _handle_update(update)
        except Exception as exc:
            logger.exception("error handling update %s: %s", update_id, exc)
        # Always advance past this update, even if handler raised.
        next_offset = update_id + 1
    return next_offset


async def run_polling_loop() -> None:
    """Long-running polling task. Started by main.py lifespan."""
    if _is_disabled():
        logger.info("telegram code bot disabled via TELEGRAM_DISABLED=1, skipping")
        return
    if not _bot_token():
        logger.warning(
            "TELEGRAM_BOT_TOKEN not set, telegram code bot polling NOT started"
        )
        return

    model = settings.AI_CODE_MODEL or settings.AI_MODEL
    logger.info(
        "telegram code bot polling started (model=%s, bot=%s)",
        model,
        (_bot_token() or "").split(":", 1)[0],  # log bot id only, never the token
    )

    offset: int | None = None
    backoff = 1.0
    try:
        while True:
            try:
                new_offset = await _poll_once(offset)
                if new_offset != offset:
                    offset = new_offset
                    backoff = 1.0
                else:
                    await asyncio.sleep(POLL_INTERVAL_S)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("polling loop error: %s", exc)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)
    except asyncio.CancelledError:
        logger.info("telegram code bot polling stopped (cancelled)")
        raise