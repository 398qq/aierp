"""Sales AI Pipeline — proactive intelligence that runs on every mutation.

Fire-and-forget enrichment on save, advisory validation on flow conversions.
All functions gracefully degrade — AI failures never block the user.
"""

import asyncio
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session

logger = logging.getLogger(__name__)

# Skip background tasks in test environments
_ENABLED = os.getenv("SALES_AI_PIPELINE", "1") != "0"


# ============================================================
# Fire-and-forget enrichment hooks
# ============================================================

def after_opportunity_save(opp_id: int):
    """Spawn background enrichment + risk notification for an opportunity."""
    if not _ENABLED:
        return
    asyncio.create_task(_bg_enrich_opportunity(opp_id))


def after_quotation_save(quote_id: int):
    """Spawn background enrichment + risk notification for a quotation."""
    if not _ENABLED:
        return
    asyncio.create_task(_bg_enrich_quotation(quote_id))


async def _bg_enrich_opportunity(opp_id: int):
    try:
        from app.models.sales import Opportunity
        from app.services.sales_ai_service import enrich_opportunity
        from app.services.notification_service import create_notification

        async with async_session() as db:
            opp = await db.get(Opportunity, opp_id)
            if not opp or opp.deleted_at:
                return
            result = await enrich_opportunity(db, opp)
            if not result:
                return
            risk = result.get("risk_level", "low")
            if risk == "high":
                await create_notification(
                    db, user_id=1, type="risk_alert",
                    title=f"高风险商机: {opp.title}",
                    content=f"赢单概率 {result.get('win_probability', '?')}%，建议: {result.get('next_best_action', '无')}",
                    related_id=opp_id,
                )
    except Exception:
        logger.exception("bg_enrich_opportunity failed for opp_id=%s", opp_id)


async def _bg_enrich_quotation(quote_id: int):
    try:
        from app.models.sales import Quotation
        from app.services.sales_ai_service import enrich_quotation
        from app.services.notification_service import create_notification

        async with async_session() as db:
            quote = await db.get(Quotation, quote_id)
            if not quote or quote.deleted_at:
                return
            result = await enrich_quotation(db, quote)
            if not result:
                return
            prob = result.get("win_probability", 50)
            if prob < 30:
                await create_notification(
                    db, user_id=1, type="risk_alert",
                    title=f"低赢单概率报价: ¥{quote.total_amount:,.2f}",
                    content=f"赢单概率 {prob}%，健康度 {result.get('pricing_health', '?')}",
                    related_id=quote_id,
                )
    except Exception:
        logger.exception("bg_enrich_quotation failed for quote_id=%s", quote_id)


# ============================================================
# Flow conversion validation (advisory, not blocking)
# ============================================================

async def validate_quote_to_order(db: AsyncSession, quote) -> dict | None:
    """AI validation before quote→order conversion. Returns warnings or None."""
    from app.services.sales_ai_service import _call_ai
    from app.services.ai.prompts import flow_validate_quote_to_order_prompt

    ctx = {
        "total_amount": str(quote.total_amount),
        "item_count": str(len(quote.items) if quote.items else 0),
        "status": quote.status,
        "items_summary": ", ".join(
            f"{qi.product_name or '?'}x{qi.quantity}" for qi in (quote.items or [])
        )[:500],
    }
    schema = {
        "risk_level": "string: low / medium / high",
        "warnings": ["string"],
        "recommendations": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件订单审核专家。给出转换建议（仅供参考）。"},
         {"role": "user", "content": flow_validate_quote_to_order_prompt(ctx)}],
        schema,
    )


async def validate_order_to_delivery(db: AsyncSession, order) -> dict | None:
    """AI validation before order→delivery conversion. Returns warnings or None."""
    from app.services.sales_ai_service import _call_ai
    from app.services.ai.prompts import flow_validate_order_to_delivery_prompt

    ctx = {
        "total_amount": str(order.total_amount),
        "item_count": str(len(order.items) if order.items else 0),
        "status": order.status,
        "delivery_date": str(order.delivery_date)[:10] if order.delivery_date else "",
    }
    schema = {
        "risk_level": "string: low / medium / high",
        "warnings": ["string"],
        "recommendations": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件物流审核专家。给出发货建议（仅供参考）。"},
         {"role": "user", "content": flow_validate_order_to_delivery_prompt(ctx)}],
        schema,
    )
