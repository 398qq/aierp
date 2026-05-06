"""AI API endpoints — chat, analysis, embeddings."""

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import CustomerAgent, EmbeddingService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/customer/{customer_id}/rfm")
async def analyze_rfm(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.sales import SalesOrder

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    # Aggregate order data
    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()

    # Get last followup
    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        "last_followup": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
    }
    analysis = await CustomerAgent.rfm_analysis(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/churn-risk")
async def analyze_churn(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.sales import SalesOrder

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    order_count = (await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "level": customer.level or "",
        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        "last_followup": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
        "recent_orders": order_count,
    }
    analysis = await CustomerAgent.churn_risk(data)
    return ok(analysis)


@router.post("/customer/{customer_id}/followup-suggestion")
async def suggest_followup(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    last_fu = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
        "level": customer.level or "",
        "last_followup_content": last_fu.content if last_fu else None,
        "last_followup_date": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
    }
    suggestion = await CustomerAgent.followup_suggestion(data)
    return ok(suggestion)


@router.post("/customer/{customer_id}/embed")
async def embed_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    embedding = await EmbeddingService.embed_customer({
        "name": customer.name,
        "industry": customer.industry or "",
        "notes": customer.notes or "",
    })
    return ok({"embedding": embedding, "dimensions": len(embedding)})


async def _chat_stream(query: str):
    async for chunk in CustomerAgent.chat(query, model=settings.AI_CHAT_MODEL):
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def ai_chat(query: str = Query(...), _user: dict = Depends(get_current_user)):
    return StreamingResponse(_chat_stream(query), media_type="text/event-stream")
