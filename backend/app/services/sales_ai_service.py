"""Sales AI enrichment — embeds AI insights into every sales entity."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sales import DeliveryNote, Opportunity, Quotation, SalesOrder

logger = logging.getLogger(__name__)


async def _call_ai(messages: list[dict], output_schema: dict) -> dict | None:
    """Call AI with structured output. Returns None on any failure."""
    try:
        from app.services.ai.client import ai_client
        result = await ai_client.chat_structured(messages, output_schema, temperature=0.3)
        return result
    except Exception:
        logger.exception("Sales AI enrichment failed")
        return None


# ============================================================
# Per-entity enrichment (detail view)
# ============================================================

async def enrich_opportunity(db: AsyncSession, opp: Opportunity) -> dict | None:
    from app.services.ai.prompts import opportunity_enrich_prompt

    ctx = {
        "title": opp.title,
        "stage": opp.stage or "未知",
        "amount": str(opp.amount or 0),
        "status": opp.status,
        "notes": opp.notes or "",
    }
    schema = {
        "risk_level": "string: low / medium / high",
        "win_probability": "integer: 0-100",
        "next_best_action": "string | null",
        "key_concerns": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件销售专家。"},
         {"role": "user", "content": opportunity_enrich_prompt(ctx)}],
        schema,
    )


async def enrich_quotation(db: AsyncSession, quote: Quotation) -> dict | None:
    from app.services.ai.prompts import quotation_enrich_prompt

    items_data = []
    for qi in quote.items:
        items_data.append({
            "product_name": qi.product_name or "未知",
            "quantity": qi.quantity,
            "unit_price": str(qi.unit_price or 0),
            "total_price": str(qi.total_price or 0),
        })

    ctx = {
        "total_amount": str(quote.total_amount),
        "status": quote.status,
        "item_count": str(len(quote.items)),
        "items": items_data,
    }
    schema = {
        "pricing_health": "string: good / fair / poor",
        "win_probability": "integer: 0-100",
        "margin_assessment": "string | null",
        "improvement_suggestions": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件报价分析专家。"},
         {"role": "user", "content": quotation_enrich_prompt(ctx)}],
        schema,
    )


async def enrich_sales_order(db: AsyncSession, order: SalesOrder) -> dict | None:
    from app.services.ai.prompts import sales_order_enrich_prompt

    ctx = {
        "total_amount": str(order.total_amount),
        "status": order.status,
        "order_date": str(order.order_date)[:10] if order.order_date else "",
        "delivery_date": str(order.delivery_date)[:10] if order.delivery_date else "",
        "notes": order.notes or "",
        "item_count": str(len(order.items)),
    }
    schema = {
        "delivery_risk": "string: low / medium / high",
        "payment_risk": "string: low / medium / high",
        "health_score": "integer: 0-100",
        "flags": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件订单管理专家。"},
         {"role": "user", "content": sales_order_enrich_prompt(ctx)}],
        schema,
    )


async def enrich_delivery_note(db: AsyncSession, note: DeliveryNote) -> dict | None:
    from app.services.ai.prompts import delivery_note_enrich_prompt

    ctx = {
        "status": note.status,
        "delivery_date": str(note.delivery_date)[:10] if note.delivery_date else "",
        "received_date": str(note.received_date)[:10] if note.received_date else "",
        "notes": note.notes or "",
        "item_count": str(len(note.items)),
    }
    schema = {
        "completion_risk": "string: low / medium / high",
        "signing_delay_probability": "integer: 0-100",
        "issues": ["string"],
    }
    return await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件物流管理专家。"},
         {"role": "user", "content": delivery_note_enrich_prompt(ctx)}],
        schema,
    )


# ============================================================
# Batch list enrichment
# ============================================================

async def enrich_opportunity_list(db: AsyncSession, opps: list[Opportunity]) -> dict[int, dict]:
    from app.services.ai.prompts import list_risk_summary_prompt

    if not opps:
        return {}

    opp_data = [{
        "id": o.id,
        "title": o.title,
        "stage": o.stage or "",
        "amount": str(o.amount or 0),
        "status": o.status,
        "win_probability": str(o.win_probability or ""),
    } for o in opps]

    schema = {
        "items": [{"id": "integer", "risk_level": "string", "flag": "string | null"}],
    }
    result = await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件销售分析专家。批量评估商机风险。"},
         {"role": "user", "content": list_risk_summary_prompt(opp_data)}],
        schema,
    )
    if not result:
        return {}
    return {item["id"]: {"risk_level": item.get("risk_level", "low"), "flag": item.get("flag")}
            for item in result.get("items", []) if "id" in item}


async def enrich_quotation_list(db: AsyncSession, quotes: list[Quotation]) -> dict[int, dict]:
    from app.services.ai.prompts import quotation_list_enrich_prompt

    if not quotes:
        return {}

    quote_data = [{
        "id": q.id,
        "total_amount": str(q.total_amount),
        "status": q.status,
        "item_count": str(len(q.items) if q.items else 0),
    } for q in quotes]

    schema = {
        "items": [{"id": "integer", "pricing_health": "string", "flag": "string | null"}],
    }
    result = await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件报价分析专家。批量评估报价单质量。"},
         {"role": "user", "content": quotation_list_enrich_prompt(quote_data)}],
        schema,
    )
    if not result:
        return {q.id: {"pricing_health": "fair", "flag": None} for q in quotes}
    return {item["id"]: {"pricing_health": item.get("pricing_health", "fair"), "flag": item.get("flag")}
            for item in result.get("items", []) if "id" in item}


async def enrich_order_list(db: AsyncSession, orders: list[SalesOrder]) -> dict[int, dict]:
    from app.services.ai.prompts import order_list_enrich_prompt

    if not orders:
        return {}

    order_data = [{
        "id": o.id,
        "total_amount": str(o.total_amount),
        "status": o.status,
        "item_count": str(len(o.items) if o.items else 0),
    } for o in orders]

    schema = {
        "items": [{"id": "integer", "delivery_risk": "string", "flag": "string | null"}],
    }
    result = await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件订单管理专家。批量评估订单风险。"},
         {"role": "user", "content": order_list_enrich_prompt(order_data)}],
        schema,
    )
    if not result:
        return {o.id: {"delivery_risk": "low", "flag": None} for o in orders}
    return {item["id"]: {"delivery_risk": item.get("delivery_risk", "low"), "flag": item.get("flag")}
            for item in result.get("items", []) if "id" in item}


async def enrich_delivery_list(db: AsyncSession, notes: list[DeliveryNote]) -> dict[int, dict]:
    from app.services.ai.prompts import delivery_list_enrich_prompt

    if not notes:
        return {}

    note_data = [{
        "id": n.id,
        "status": n.status,
        "item_count": str(len(n.items) if n.items else 0),
    } for n in notes]

    schema = {
        "items": [{"id": "integer", "completion_risk": "string", "flag": "string | null"}],
    }
    result = await _call_ai(
        [{"role": "system", "content": "你是B2B电子元器件物流专家。批量评估发货风险。"},
         {"role": "user", "content": delivery_list_enrich_prompt(note_data)}],
        schema,
    )
    if not result:
        return {n.id: {"completion_risk": "low", "flag": None} for n in notes}
    return {item["id"]: {"completion_risk": item.get("completion_risk", "low"), "flag": item.get("flag")}
            for item in result.get("items", []) if "id" in item}
