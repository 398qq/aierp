"""AI Chat submodule — streaming chat endpoint."""

import json
import logging

from fastapi import APIRouter, Body, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.services.ai import CustomerAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


async def _chat_stream(
    query: str,
    context: str = "",
    history: list[dict] | None = None,
):
    """SSE generator for streaming chat responses."""
    async for chunk in CustomerAgent.chat(
        query, context=context, history=history, model=settings.AI_CHAT_MODEL
    ):
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def ai_chat(
    query: str = Query(...),
    customer_id: int | None = Query(None),
    context: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
    body: dict | None = Body(None),
):
    """Streaming chat endpoint with optional customer context."""
    # Build context from customer data if customer_id provided
    chat_ctx = context or ""
    if customer_id and not context:
        from app.models.customer import Customer
        from app.models.sales import SalesOrder

        cust = (
            await db.execute(
                select(Customer).where(
                    Customer.id == customer_id, Customer.deleted_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        if cust:
            order_count = (
                await db.execute(
                    select(func.count(SalesOrder.id)).where(
                        SalesOrder.customer_id == customer_id,
                        SalesOrder.deleted_at.is_(None),
                    )
                )
            ).scalar() or 0
            total_rev = (
                await db.execute(
                    select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                        SalesOrder.customer_id == customer_id,
                        SalesOrder.deleted_at.is_(None),
                    )
                )
            ).scalar() or 0
            chat_ctx = (
                f"客户名称：{cust.name}，行业：{cust.industry or '未知'}，"
                f"等级：{cust.level or '未知'}，区域：{cust.region or '未知'}，"
                f"历史订单数：{order_count}，历史交易总额：{float(total_rev)}元，"
                f"最后联系时间：{cust.last_contacted_at or '无'}"
            )

    # Accept conversation history from request body
    history_msgs: list[dict] | None = None
    if body and isinstance(body.get("history"), list):
        history_msgs = body["history"]

    return StreamingResponse(
        _chat_stream(query, chat_ctx, history_msgs), media_type="text/event-stream"
    )
