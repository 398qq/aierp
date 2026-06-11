"""Commission status change notifier (Stage 10 Day 2).

Fires on:
- approve: notify the sales user (\"your commission is approved\")
- pay: notify the sales user (\"your commission has been paid\")
- reject: notify the sales user (\"your commission was rejected\")
- cancel: notify the sales user (\"your commission was cancelled\")

Best-effort: any error is logged, never raised. The commission flow must
not break because of a notification hiccup.

Stage 10 Day 1: stub created. Day 2 implements Telegram.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def on_commission_status_changed(
    db: AsyncSession,
    commission: Any,
    previous_status: str,
    new_status: str,
    actor: str,
) -> None:
    """Hook called after a commission status change. Best-effort.

    Day 2 will implement Telegram sending here. Day 1 is a no-op stub
    so the transition endpoint can wire up without breaking.
    """
    logger.info(
        "commission %s: %s → %s by %s",
        commission.commission_no,
        previous_status,
        new_status,
        actor,
    )
    # Day 2: real Telegram notification goes here
