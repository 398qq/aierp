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


# --- Sales AI ---

@router.post("/sales/recommend")
async def ai_sales_recommend(
    customer_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer
    from app.models.sales import Opportunity, Quotation, SalesOrder

    cust_result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = cust_result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    opp_count = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id, Opportunity.deleted_at.is_(None)
        )
    )).scalar() or 0

    order_count = (await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    data = {
        "name": customer.name,
        "industry": customer.industry or "",
        "level": customer.level or "",
        "opportunities": opp_count,
        "orders": order_count,
        "total_revenue": float(total_revenue),
    }

    try:
        from app.services.ai.client import ai_client
        from app.services.ai.prompts import SALES_AGENT_SYSTEM

        schema = {
            "recommended_products": "list of strings, recommended product categories or types",
            "opportunity_suggestion": "string, suggestion for next sales opportunity",
            "cross_sell_opportunities": "string, cross-sell suggestions",
            "priority_action": "string, the single most important action to take",
        }
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_AGENT_SYSTEM},
                {"role": "user", "content": f"基于以下客户历史数据，推荐产品和商机：客户名称={data['name']}，行业={data['industry']}，级别={data['level']}，历史商机数={data['opportunities']}，历史订单数={data['orders']}，历史交易总额={data['total_revenue']}"},
            ],
            schema,
        )
        return ok(result)
    except Exception as e:
        return ok({"recommended_products": [], "opportunity_suggestion": "AI 分析暂时不可用", "cross_sell_opportunities": "", "priority_action": str(e)})


@router.post("/sales/predict")
async def ai_sales_predict(
    opportunity_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.customer import Customer
    from app.models.sales import Opportunity, SalesOrder

    opp_result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id, Opportunity.deleted_at.is_(None))
    )
    opp = opp_result.scalar_one_or_none()
    if opp is None:
        return fail("Opportunity not found", 404)

    cust_result = await db.execute(
        select(Customer).where(Customer.id == int(opp.customer_id), Customer.deleted_at.is_(None))
    )
    customer = cust_result.scalar_one_or_none()

    order_count = (await db.execute(
        select(func.count(SalesOrder.id)).where(
            SalesOrder.customer_id == opp.customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    total_revenue = (await db.execute(
        select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
            SalesOrder.customer_id == opp.customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalar() or 0

    data = {
        "name": opp.name,
        "amount": float(opp.amount),
        "stage": opp.stage,
        "probability": opp.probability,
        "customer_name": customer.name if customer else "未知",
        "customer_industry": customer.industry if customer else "",
        "customer_level": customer.level if customer else "",
        "customer_orders": order_count,
        "customer_revenue": float(total_revenue),
    }

    try:
        from app.services.ai.client import ai_client
        from app.services.ai.prompts import SALES_AGENT_SYSTEM

        schema = {
            "win_probability": "integer 0-100, predicted win probability",
            "confidence": "string: high/medium/low",
            "key_factors": "list of strings, key factors affecting the prediction",
            "recommendation": "string, what to do to improve win rate",
        }
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": SALES_AGENT_SYSTEM},
                {"role": "user", "content": f"预测商机成交概率：商机名称={data['name']}，金额={data['amount']}，当前阶段={data['stage']}，当前估算概率={data['probability']}%，客户名称={data['customer_name']}，客户行业={data['customer_industry']}，客户级别={data['customer_level']}，历史订单数={data['customer_orders']}，历史交易总额={data['customer_revenue']}"},
            ],
            schema,
        )
        return ok(result)
    except Exception as e:
        return ok({"win_probability": opp.probability, "confidence": "low", "key_factors": [f"AI 分析暂时不可用: {e}"], "recommendation": ""})
