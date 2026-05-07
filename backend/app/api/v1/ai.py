"""AI API endpoints — chat, analysis, embeddings."""

import json
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_db
from app.schemas.common import fail, ok
from app.services.ai import CustomerAgent, EmbeddingService, InventoryAgent, ProductAgent
from app.services.ai.client import ai_client

logger = logging.getLogger(__name__)

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

    # Use cached result from batch job if available
    if customer.ai_insights and customer.ai_insights.get("rfm"):
        return ok(customer.ai_insights["rfm"])

    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()

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
    from datetime import datetime, timedelta, timezone
    from app.models.customer import Customer, CustomerFollowUp
    from app.models.finance import PaymentRecord
    from app.models.sales import Opportunity, Quotation, SalesOrder

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    # Use cached result from batch job if available
    if customer.ai_insights and customer.ai_insights.get("churn"):
        return ok(customer.ai_insights["churn"])

    now = datetime.now(timezone.utc)
    d90 = now - timedelta(days=90)
    d180 = now - timedelta(days=180)

    # Order stats
    order_stats = (await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
            func.max(SalesOrder.created_at),
            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
            func.count(SalesOrder.id).filter(SalesOrder.created_at >= d180),
        ).where(SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None))
    )).first()

    # Opportunity & quotation counts
    active_opps = (await db.execute(
        select(func.count(Opportunity.id)).where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.in_(["lead", "qualification", "proposal", "negotiation"]),
        )
    )).scalar() or 0

    active_quotations = (await db.execute(
        select(func.count(Quotation.id)).where(
            Quotation.customer_id == customer_id,
            Quotation.deleted_at.is_(None),
            Quotation.status.in_(["draft", "sent"]),
        )
    )).scalar() or 0

    # Credit & AR
    credit_util = "无数据"
    if customer.credit_limit and customer.credit_limit > 0:
        outstanding = (await db.execute(
            select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                PaymentRecord.customer_id == customer_id,
                PaymentRecord.deleted_at.is_(None),
                PaymentRecord.status != "paid",
            )
        )).scalar() or 0
        credit_util = f"{min(100, round(float(outstanding) / float(customer.credit_limit) * 100))}%"

    # AR overdue: unpaid payments older than 30 days
    ar_overdue_days = 0
    thirty_days_ago = now - timedelta(days=30)
    oldest_unpaid = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.customer_id == customer_id,
            PaymentRecord.deleted_at.is_(None),
            PaymentRecord.status != "paid",
            PaymentRecord.created_at < thirty_days_ago,
        ).order_by(PaymentRecord.created_at.asc()).limit(1)
    )).scalar_one_or_none()
    if oldest_unpaid and oldest_unpaid.created_at:
        ar_overdue_days = (now - oldest_unpaid.created_at.replace(tzinfo=timezone.utc)).days

    # Health score
    from app.services.customer_service import calc_health
    payments_for_health = (await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.customer_id == customer_id, PaymentRecord.deleted_at.is_(None)
        )
    )).scalars().all()
    orders_for_health = (await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
        )
    )).scalars().all()
    health_score, health_label = calc_health(customer, list(orders_for_health), list(payments_for_health), now)

    # Order trend
    orders_90d = order_stats[3] or 0
    orders_180d = order_stats[4] or 0
    orders_before = (orders_180d or 0) - (orders_90d or 0)
    order_trend = "稳定"
    if orders_90d > 0 and orders_before > 0:
        if orders_90d > orders_before * 1.3:
            order_trend = "增长"
        elif orders_90d < orders_before * 0.7:
            order_trend = "下降"

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
        "lifecycle": customer.lifecycle or "未知",
        "total_orders": order_stats[0] or 0,
        "total_revenue": float(order_stats[1]) if order_stats[1] else 0,
        "last_order_date": str(order_stats[2]) if order_stats[2] else None,
        "orders_last_90d": orders_90d,
        "orders_last_180d": orders_180d,
        "order_trend": order_trend,
        "last_followup_date": str(last_fu.planned_at) if last_fu and last_fu.planned_at else None,
        "last_contacted_at": str(customer.last_contacted_at) if customer.last_contacted_at else None,
        "active_opportunities": active_opps,
        "active_quotations": active_quotations,
        "credit_utilization": credit_util,
        "ar_overdue_days": ar_overdue_days,
        "health_score": health_score,
        "health_label": health_label,
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


@router.post("/customer/{customer_id}/analyze-followups")
async def analyze_followups(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Semantic analysis of follow-up history: sentiment, topics, action items, risk signals."""
    from app.models.customer import Customer, CustomerFollowUp

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)

    followups = (await db.execute(
        select(CustomerFollowUp).where(
            CustomerFollowUp.customer_id == customer_id,
            CustomerFollowUp.deleted_at.is_(None),
        ).order_by(CustomerFollowUp.created_at.desc()).limit(20)
    )).scalars().all()

    analysis = await CustomerAgent.analyze_followups(
        [{"method": f.method, "content": f.content, "result": f.result} for f in followups],
        customer_name=customer.name,
    )
    return ok(analysis)


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
    customer.embedding = embedding
    await db.commit()
    return ok({"customer_id": customer_id, "dimensions": len(embedding)})

@router.get("/customer/{customer_id}/similar")
async def similar_customers(customer_id: int, top_k: int = 10, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.customer import Customer

    result = await db.execute(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    customer = result.scalar_one_or_none()
    if customer is None:
        return fail("Customer not found", 404)
    if customer.embedding is None:
        return fail("Customer has no embedding, call POST embed first", 400)

    similar = await EmbeddingService.similar_customers(customer.embedding, db, top_k, exclude_id=customer_id)
    return ok(similar)


@router.post("/alert/{event_id}/enrich")
async def enrich_alert(event_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Generate AI action suggestions for a specific alert event."""
    from app.models.customer import AlertEvent, Customer

    event_result = await db.execute(
        select(AlertEvent).where(AlertEvent.id == event_id)
    )
    event = event_result.scalar_one_or_none()
    if event is None:
        return fail("Alert event not found", 404)

    cust_result = await db.execute(
        select(Customer).where(Customer.id == event.customer_id, Customer.deleted_at.is_(None))
    )
    customer = cust_result.scalar_one_or_none()

    ctx = {
        "rule_type": event.rule_type,
        "rule_name": event.rule_name,
        "severity": event.severity,
        "message": event.message,
        "customer_name": customer.name if customer else "未知",
        "industry": customer.industry or "" if customer else "",
        "level": customer.level or "" if customer else "",
        "last_contact": str(customer.last_contacted_at) if customer and customer.last_contacted_at else "无",
    }
    enrichment = await CustomerAgent.enrich_alert(ctx)
    return ok(enrichment)


@router.get("/customer/similar/search")
async def search_similar_by_text(q: str = Query(...), top_k: int = 10, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Natural-language semantic search for similar customers."""
    similar = await EmbeddingService.similar_by_text(q, db, top_k)
    return ok(similar)


@router.post("/customer/embed-all")
async def embed_all_customers(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Batch generate embeddings for all customers that lack them."""
    stats = await EmbeddingService.index_all(db)
    await db.commit()
    return ok(stats)


@router.get("/customer/segments")
async def customer_segments(n_clusters: int = 5, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI-driven customer segmentation via K-means clustering on embeddings."""
    result = await EmbeddingService.segment_customers(db, n_clusters)
    return ok(result)


async def _chat_stream(query: str, context: str = ""):
    async for chunk in CustomerAgent.chat(query, context=context, model=settings.AI_CHAT_MODEL):
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/chat")
async def ai_chat(
    query: str = Query(...),
    customer_id: int | None = Query(None),
    context: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    # Build context from customer data if customer_id provided
    chat_ctx = context or ""
    if customer_id and not context:
        from app.models.customer import Customer
        from app.models.sales import SalesOrder
        cust = (await db.execute(
            select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
        )).scalar_one_or_none()
        if cust:
            order_count = (await db.execute(
                select(func.count(SalesOrder.id)).where(
                    SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
                )
            )).scalar() or 0
            total_rev = (await db.execute(
                select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                    SalesOrder.customer_id == customer_id, SalesOrder.deleted_at.is_(None)
                )
            )).scalar() or 0
            chat_ctx = (
                f"客户名称：{cust.name}，行业：{cust.industry or '未知'}，"
                f"等级：{cust.level or '未知'}，区域：{cust.region or '未知'}，"
                f"历史订单数：{order_count}，历史交易总额：{float(total_rev)}元，"
                f"最后联系时间：{cust.last_contacted_at or '无'}"
            )

    return StreamingResponse(_chat_stream(query, chat_ctx), media_type="text/event-stream")


# --- Inventory AI ---

@router.post("/inventory/analyze")
async def analyze_inventory(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.models.product import Product, InventoryItem

    items = (await db.execute(
        select(
            Product.name, InventoryItem.quantity, InventoryItem.safety_stock,
        ).select_from(InventoryItem).join(
            Product, InventoryItem.product_id == Product.id
        ).where(
            InventoryItem.deleted_at.is_(None), Product.deleted_at.is_(None),
        )
    )).all()

    if not items:
        return fail("No inventory data found", 404)

    inventory_data = [
        {"product_name": r[0], "current_stock": r[1] or 0, "safety_stock": r[2] or 0}
        for r in items
    ]
    analysis = await InventoryAgent.analyze(inventory_data)
    return ok(analysis)


# --- Sales AI ---

@router.post("/sales/recommend")
async def ai_sales_recommend(
    customer_id: int = Query(...),
    top_k: int = Query(10, le=50),
    use_llm: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Product recommendation: pgvector collaborative-filtering (default) or LLM fallback."""
    try:
        from app.services.ai.recommend import recommend_products
        result = await recommend_products(customer_id, db, top_k=top_k)
        return ok(result)
    except Exception as e:
        logger.exception("Collaborative recommendation failed, falling back to LLM")
        if not use_llm:
            return fail(f"Recommendation not available: {str(e)}", 503)

    # LLM fallback (original behavior)
    from app.models.customer import Customer
    from app.models.sales import Opportunity, SalesOrder

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
        return fail(f"AI 分析暂时不可用: {str(e)}", 503)


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
        import logging
        logging.getLogger(__name__).error(f"Win prediction failed: {e}")
        return fail(f"AI 分析暂时不可用: {str(e)}", 503)


# --- Product AI ---


@router.post("/products/parse")
async def ai_parse_product(text: str = Query(...), _user: dict = Depends(get_current_user)):
    """AI parses raw part-number/description text into structured product fields."""
    result = await ProductAgent.parse_product(text)
    return ok(result)


@router.post("/products/parse-bom")
async def ai_parse_bom(text: str = Query(...), _user: dict = Depends(get_current_user)):
    """AI parses a BOM list into structured line items."""
    items = await ProductAgent.parse_bom(text)
    return ok({"items": items, "count": len(items)})


@router.post("/products/search")
async def ai_product_search(q: str = Query(...), top_k: int = Query(10, le=50), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Semantic product search via embedding similarity."""
    from app.models.product import Brand, Product

    embedding = await ai_client.embed_single(q)

    result = await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            Product.package_type, Product.specs, Product.unit, Product.brand_id,
            Brand.name_cn, Brand.name,
            Product.embedding.cosine_distance(embedding).label("distance"),
        )
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.deleted_at.is_(None), Product.embedding.isnot(None))
        .order_by(Product.embedding.cosine_distance(embedding))
        .limit(top_k)
    )
    rows = result.all()
    return ok([{
        "id": r[0], "sku": r[1], "name": r[2], "category": r[3],
        "package_type": r[4], "specs": r[5], "unit": r[6],
        "brand_id": r[7], "brand_name": r[8] or r[9],
        "similarity": round(1 - float(r[10]), 4),
    } for r in rows])


@router.post("/products/{product_id}/embed")
async def embed_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Generate pgvector embedding for a product."""
    from app.models.product import Brand, Product

    result = await db.execute(
        select(Product).outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )
    row = result.first()
    if row is None:
        return fail("Product not found", 404)
    p = row[0]
    b = row[1] if len(row) > 1 else None

    embedding = await EmbeddingService.embed_product({
        "part_number": f"{p.sku or ''} {p.name}".strip(),
        "description": p.specs or p.notes or "",
        "brand_name": b.name if b else "",
    })
    p.embedding = embedding
    await db.commit()
    return ok({"product_id": product_id, "dimensions": len(embedding)})


@router.post("/products/embed-all")
async def embed_all_products(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Batch generate embeddings for all products that lack them."""
    from app.models.product import Brand, Product

    result = await db.execute(
        select(Product).where(Product.deleted_at.is_(None), Product.embedding.is_(None))
    )
    products = result.scalars().all()
    indexed, errors = 0, 0
    batch_size = 50

    for i in range(0, len(products), batch_size):
        batch = products[i : i + batch_size]
        texts = []
        for p in batch:
            # Get brand name
            b_result = await db.execute(select(Brand.name).where(Brand.id == p.brand_id))
            brand_name = b_result.scalar() or ""
            texts.append(
                f"型号：{p.sku or ''} {p.name}，描述：{p.specs or ''}，品牌：{brand_name}"
            )
        try:
            embeddings = await ai_client.embed(texts)
            for p, emb in zip(batch, embeddings):
                p.embedding = emb
            indexed += len(batch)
            await db.flush()
        except Exception:
            errors += len(batch)

    await db.commit()
    return ok({"indexed": indexed, "errors": errors})


@router.get("/products/{product_id}/similar")
async def similar_products(product_id: int, top_k: int = 10, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Find similar products via pgvector cosine distance."""
    from app.models.product import Brand, Product

    prod = (await db.execute(
        select(Product).where(Product.id == product_id, Product.deleted_at.is_(None))
    )).scalar_one_or_none()
    if prod is None:
        return fail("Product not found", 404)
    if prod.embedding is None:
        return fail("Product has no embedding yet", 400)

    result = await db.execute(
        select(
            Product.id, Product.sku, Product.name, Product.category,
            Product.package_type, Product.unit, Brand.name_cn, Brand.name,
            Product.embedding.cosine_distance(prod.embedding).label("distance"),
        )
        .outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.deleted_at.is_(None), Product.id != product_id, Product.embedding.isnot(None))
        .order_by(Product.embedding.cosine_distance(prod.embedding))
        .limit(top_k)
    )
    rows = result.all()
    return ok([{
        "id": r[0], "sku": r[1], "name": r[2], "category": r[3],
        "package_type": r[4], "unit": r[5],
        "brand_name": r[6] or r[7],
        "similarity": round(1 - float(r[8]), 4),
    } for r in rows])


@router.get("/products/{product_id}/substitutes")
async def product_substitutes(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI-recommended substitute parts for a product."""
    from app.models.product import Brand, Product

    prod = (await db.execute(
        select(Product).outerjoin(Brand, Product.brand_id == Brand.id)
        .where(Product.id == product_id, Product.deleted_at.is_(None))
    )).first()
    if prod is None:
        return fail("Product not found", 404)

    product_info = {
        "part_number": f"{prod[0].sku or ''} {prod[0].name}".strip(),
        "description": prod[0].specs or prod[0].notes or "",
        "category": prod[0].category or "",
        "specs": prod[0].specs or "",
        "brand": f"{prod[3] or ''} {prod[2] or ''}".strip(),
    }
    result = await ProductAgent.suggest_substitutes(product_info)
    return ok(result)


# --- Supplier-Product Matching AI ---


@router.post("/suppliers/{supplier_id}/match-products")
async def ai_match_supplier_products(supplier_id: int, catalog_text: str | None = Query(None), auto_link: bool = Query(False), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI matches a supplier's product catalog to system products."""
    from app.services.pricing_service import match_supplier_to_products

    try:
        matches = await match_supplier_to_products(db, supplier_id, catalog_text)
    except ValueError as e:
        return fail(str(e), 404)

    if auto_link and matches:
        from app.models.product import SupplierProduct
        linked = 0
        for m in matches:
            pid = m.get("product_id")
            if not pid:
                continue
            exists = (await db.execute(
                select(SupplierProduct).where(
                    SupplierProduct.supplier_id == supplier_id,
                    SupplierProduct.product_id == pid,
                    SupplierProduct.deleted_at.is_(None),
                )
            )).scalar_one_or_none()
            if not exists:
                sp = SupplierProduct(
                    supplier_id=supplier_id,
                    product_id=pid,
                    cost_price=m.get("cost_price"),
                    lead_time_days=m.get("lead_time_days"),
                    moq=m.get("moq"),
                )
                db.add(sp)
                linked += 1
        await db.commit()
        return ok({"matches": matches, "linked": linked})

    return ok({"matches": matches})


# --- Pricing AI ---


@router.get("/pricing/benchmark/{product_id}")
async def pricing_benchmark(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Get historical price benchmarks for a product."""
    from app.services.pricing_service import get_pricing_benchmark

    try:
        result = await get_pricing_benchmark(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/pricing/recommend")
async def pricing_recommend(
    product_id: int = Query(...),
    customer_id: int | None = Query(None),
    quantity: int = Query(1, ge=1),
    is_sample: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """AI-recommended price for a product considering costs, market, and customer."""
    from app.services.pricing_service import recommend_price

    try:
        result = await recommend_price(db, product_id, customer_id, quantity, is_sample)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# --- Product Intelligence ---


@router.post("/products/{product_id}/profile")
async def product_profile(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI generates a full product intelligence profile."""
    from app.services.product_intel_service import generate_product_profile

    try:
        result = await generate_product_profile(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/normalize-specs")
async def normalize_product_specs(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI normalizes unstructured spec text into key-value parameters."""
    from app.services.product_intel_service import normalize_specs

    try:
        result = await normalize_specs(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.get("/products/{product_id}/associations")
async def product_associations(product_id: int, top_k: int = 10, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """Find co-purchased/associated products via collaborative filtering."""
    from app.services.product_intel_service import get_product_associations

    result = await get_product_associations(db, product_id, top_k)
    return ok(result)


@router.post("/products/{product_id}/procurement-optimize")
async def procurement_optimize(product_id: int, quantity: int = Query(..., ge=1), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI recommends optimal multi-source procurement allocation."""
    from app.services.product_intel_service import optimize_procurement

    try:
        result = await optimize_procurement(db, product_id, quantity)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/lifecycle")
async def analyze_product_lifecycle(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    """AI evaluates product lifecycle stage and EOL/NRND risks."""
    from app.services.product_intel_service import analyze_lifecycle

    try:
        result = await analyze_lifecycle(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# --- Brand Intelligence ---


@router.post("/brands/{brand_id}/profile")
async def brand_profile(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import generate_brand_profile
    try:
        result = await generate_brand_profile(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/portfolio")
async def brand_portfolio(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import analyze_brand_portfolio
    try:
        result = await analyze_brand_portfolio(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.get("/brands/{brand_id}/similar")
async def similar_brands(brand_id: int, top_k: int = 5, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import find_similar_brands
    result = await find_similar_brands(db, brand_id, top_k)
    return ok(result)


@router.post("/brands/compare")
async def compare_brands(brand_a: int = Query(...), brand_b: int = Query(...), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import compare_brands
    try:
        result = await compare_brands(db, brand_a, brand_b)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/import")
async def import_brand(text: str = Query(...), auto_create: bool = Query(False), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import import_brand_from_text
    try:
        result = await import_brand_from_text(db, text, auto_create)
        return ok(result)
    except ValueError as e:
        return fail(f"AI 解析失败: {str(e)}", 503)


@router.post("/brands/{brand_id}/health")
async def brand_health(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import get_brand_health
    try:
        result = await get_brand_health(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/risk")
async def brand_risk(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import assess_brand_risk
    try:
        result = await assess_brand_risk(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/supplier-matrix")
async def brand_supplier_matrix(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import get_brand_supplier_matrix
    try:
        result = await get_brand_supplier_matrix(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/recommendations")
async def brand_recommendations(brand_id: int, top_k: int = Query(5), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import recommend_brands
    try:
        result = await recommend_brands(db, brand_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Smart Quotation Assistant
# ============================================================


class QuoteAssistItem(BaseModel):
    product_id: int
    quantity: int = 1


class QuoteAssistRequest(BaseModel):
    customer_id: int
    items: list[QuoteAssistItem]


@router.post("/quotations/assist")
async def quote_assist(req: QuoteAssistRequest, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.quote_assistant_service import quote_assist
    try:
        items = [{"product_id": it.product_id, "quantity": it.quantity} for it in req.items]
        result = await quote_assist(db, req.customer_id, items)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Sales Intelligence Routes
# ============================================================

@router.post("/sales/opportunities/{opportunity_id}/score")
async def opportunity_score(opportunity_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.sales_intel_service import score_opportunity
    try:
        result = await score_opportunity(db, opportunity_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/sales/pipeline-health")
async def pipeline_health(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.sales_intel_service import analyze_pipeline_health
    try:
        result = await analyze_pipeline_health(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 500)


@router.post("/sales/quotations/{quotation_id}/optimize")
async def quotation_optimize(quotation_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.sales_intel_service import optimize_quotation
    try:
        result = await optimize_quotation(db, quotation_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/sales/customers/{customer_id}/cross-sell")
async def customer_cross_sell(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.sales_intel_service import detect_cross_sell
    try:
        result = await detect_cross_sell(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  AI Watchtower — System-wide anomaly scan
# ============================================================

@router.get("/watchtower/scan")
async def watchtower_scan(days_back: int = Query(90), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.watchtower_service import scan_all
    try:
        result = await scan_all(db, days_back)
        return ok(result)
    except Exception as e:
        return fail(str(e), 500)


# ============================================================
#  Smart Matching — Customer-Product Recommendations
# ============================================================

@router.post("/customers/{customer_id}/recommend-products")
async def recommend_products(customer_id: int, top_k: int = Query(5), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.matching_service import recommend_products_for_customer
    try:
        result = await recommend_products_for_customer(db, customer_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/products/{product_id}/recommend-customers")
async def recommend_customers(product_id: int, top_k: int = Query(5), db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.matching_service import recommend_customers_for_product
    try:
        result = await recommend_customers_for_product(db, product_id, top_k)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Brand Product Performance, Customer Penetration, Lifecycle, Price Trends
# ============================================================

@router.post("/brands/{brand_id}/product-performance")
async def brand_product_performance(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import get_brand_product_performance
    try:
        result = await get_brand_product_performance(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/customer-penetration")
async def brand_customer_penetration(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import get_brand_customer_penetration
    try:
        result = await get_brand_customer_penetration(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/lifecycle")
async def brand_lifecycle(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import predict_brand_lifecycle
    try:
        result = await predict_brand_lifecycle(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/brands/{brand_id}/price-trends")
async def brand_price_trends(brand_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.brand_intel_service import get_brand_price_trends
    try:
        result = await get_brand_price_trends(db, brand_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Supplier Intelligence Routes
# ============================================================

@router.post("/suppliers/{supplier_id}/scorecard")
async def supplier_scorecard(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import get_supplier_scorecard
    try:
        result = await get_supplier_scorecard(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/suppliers/{supplier_id}/delay-prediction")
async def supplier_delay_prediction(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import predict_supplier_delay
    try:
        result = await predict_supplier_delay(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/suppliers/{supplier_id}/alternatives")
async def supplier_alternatives(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import get_supplier_alternatives
    try:
        result = await get_supplier_alternatives(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/suppliers/{supplier_id}/price-variance")
async def supplier_price_variance(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import detect_supplier_price_variance
    try:
        result = await detect_supplier_price_variance(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/suppliers/{supplier_id}/negotiation")
async def supplier_negotiation(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import get_supplier_negotiation
    try:
        result = await get_supplier_negotiation(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/suppliers/{supplier_id}/360")
async def supplier_360(supplier_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import get_supplier_360
    try:
        result = await get_supplier_360(db, supplier_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


@router.post("/suppliers/compare")
async def supplier_compare(body: dict, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.supplier_intel_service import compare_suppliers
    supplier_ids = body.get("supplier_ids", [])
    if not isinstance(supplier_ids, list) or len(supplier_ids) < 2:
        return fail("supplier_ids 必须是至少包含2个ID的数组", 400)
    try:
        result = await compare_suppliers(db, supplier_ids)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Purchase Order Intelligence Routes
# ============================================================

@router.post("/purchase-orders/{order_id}/optimize")
async def po_optimize(order_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.po_intel_service import optimize_purchase_order
    try:
        result = await optimize_purchase_order(db, order_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/purchase-orders/suggest")
async def po_suggest(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.po_intel_service import suggest_purchase_orders
    try:
        result = await suggest_purchase_orders(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/purchase-orders/{order_id}/risk")
async def po_risk(order_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.po_intel_service import assess_po_risk
    try:
        result = await assess_po_risk(db, order_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Payment & AR Intelligence Routes
# ============================================================

@router.post("/finance/payment-prediction")
async def finance_payment_prediction(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_intel_service import predict_payment_delays
    try:
        result = await predict_payment_delays(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/finance/cash-flow")
async def finance_cash_flow(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_intel_service import forecast_cash_flow
    try:
        result = await forecast_cash_flow(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/finance/dunning/{invoice_id}")
async def finance_dunning(invoice_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_intel_service import generate_dunning_strategy
    try:
        result = await generate_dunning_strategy(db, invoice_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/finance/credit-risk/{customer_id}")
async def finance_credit_risk(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.finance_intel_service import assess_credit_risk
    try:
        result = await assess_credit_risk(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Sales Target Intelligence Routes
# ============================================================

@router.post("/targets/recommend/{user_id}")
async def target_recommend(user_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.target_intel_service import recommend_targets
    try:
        result = await recommend_targets(db, user_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/targets/{target_id}/attainment")
async def target_attainment(target_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.target_intel_service import predict_attainment
    try:
        result = await predict_attainment(db, target_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/targets/early-warning")
async def target_early_warning(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.target_intel_service import scan_target_early_warning
    try:
        result = await scan_target_early_warning(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Visit Intelligence Routes
# ============================================================

@router.post("/visits/{visit_id}/report")
async def visit_report(visit_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.visit_intel_service import generate_visit_report
    try:
        result = await generate_visit_report(db, visit_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/visits/{visit_id}/sentiment")
async def visit_sentiment(visit_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.visit_intel_service import analyze_visit_sentiment
    try:
        result = await analyze_visit_sentiment(db, visit_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/visits/effectiveness")
async def visit_effectiveness(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.visit_intel_service import evaluate_visit_effectiveness
    try:
        result = await evaluate_visit_effectiveness(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Ticket Intelligence Routes
# ============================================================

@router.post("/tickets/{ticket_id}/classify")
async def ticket_classify(ticket_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.ticket_intel_service import classify_ticket
    try:
        result = await classify_ticket(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/tickets/{ticket_id}/suggest-response")
async def ticket_suggest_response(ticket_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.ticket_intel_service import suggest_ticket_response
    try:
        result = await suggest_ticket_response(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/tickets/{ticket_id}/predict-resolution")
async def ticket_predict_resolution(ticket_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.ticket_intel_service import predict_ticket_resolution
    try:
        result = await predict_ticket_resolution(db, ticket_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/tickets/cluster")
async def ticket_cluster(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.ticket_intel_service import cluster_tickets
    try:
        result = await cluster_tickets(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Contract Intelligence Routes
# ============================================================

@router.post("/contracts/{contract_id}/extract")
async def contract_extract(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.contract_intel_service import extract_contract_terms
    try:
        result = await extract_contract_terms(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/contracts/{contract_id}/risk")
async def contract_risk(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.contract_intel_service import assess_contract_risk
    try:
        result = await assess_contract_risk(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/contracts/expiry-alerts")
async def contract_expiry_alerts(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.contract_intel_service import scan_contract_expiry
    try:
        result = await scan_contract_expiry(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/contracts/{contract_id}/rebate-tracking")
async def contract_rebate(contract_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.contract_intel_service import track_contract_rebate
    try:
        result = await track_contract_rebate(db, contract_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Multi-Agent Orchestration Routes
# ============================================================

@router.post("/orchestrate/customer/{customer_id}")
async def orchestrate_customer(customer_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.orchestration_service import orchestrate_customer_360
    try:
        result = await orchestrate_customer_360(db, customer_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/orchestrate/product/{product_id}")
async def orchestrate_product(product_id: int, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.orchestration_service import orchestrate_product_360
    try:
        result = await orchestrate_product_360(db, product_id)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)

@router.post("/orchestrate/global")
async def orchestrate_global(db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.orchestration_service import orchestrate_global_360
    try:
        result = await orchestrate_global_360(db)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)


# ============================================================
#  Natural Language ERP Query Routes
# ============================================================

@router.post("/query")
async def ai_query(data: dict, db: AsyncSession = Depends(get_db), _user: dict = Depends(get_current_user)):
    from app.services.nlp_query_service import natural_language_query
    query_text = data.get("query", "")
    if not query_text:
        return fail("query is required", 400)
    try:
        result = await natural_language_query(db, query_text)
        return ok(result)
    except ValueError as e:
        return fail(str(e), 404)
