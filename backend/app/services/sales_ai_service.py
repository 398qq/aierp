"""Sales AI enrichment — embeds AI insights into every sales entity."""

import logging
from collections import Counter

from sqlalchemy import select, or_, func
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


# ============================================================
# Inquiry Auto-Reply
# ============================================================

async def inquiry_auto_reply(db: AsyncSession, req: dict) -> dict:
    """
    Core auto-reply engine for incoming inquiries.

    1. Parse product mentions from inquiry text
    2. Search product catalog (MPN + brand keyword match)
    3. Fetch inventory + unit_price for matched products
    4. Generate AI reply with product availability and pricing
    5. Persist Inquiry record and return structured response
    """
    import json
    import re

    from app.models.product import Product, Brand, Inventory
    from app.models.customer import Customer
    from app.models.sales import Inquiry
    from app.services.ai.client import ai_client
    from app.services.brand_intel_service import suggest_eol_alternatives

    inquiry_text = req["inquiry_text"]
    customer_id = req.get("customer_id")
    contact_name = req.get("contact_name")
    contact_info = req.get("contact_info")
    channel = req.get("channel", "web")

    # --- Step 1: Parse potential MPNs from inquiry text ---
    tokens = re.findall(r"[A-Za-z0-9\-]{4,30}", inquiry_text)
    mpn_candidates = [t.upper() for t in tokens if len(t) >= 4]

    # --- Step 2: Search product catalog ---
    matched_products = []
    if mpn_candidates:
        sku_clauses = [Product.sku.ilike(f"%{m}%") for m in mpn_candidates[:5]]
        name_clauses = [Product.name.ilike(f"%{m}%") for m in mpn_candidates[:5]]
        cond = [
            Product.deleted_at.is_(None),
            or_(*(sku_clauses + name_clauses)),
        ]
        result = await db.execute(
            select(
                Product.id,
                Product.sku,
                Product.name,
                Product.brand_id,
                func.coalesce(func.sum(Inventory.quantity), 0).label("qty"),
                func.coalesce(func.sum(Inventory.safety_stock), 0).label("safety"),
                func.min(Inventory.unit_price).label("unit_price"),
            )
            .outerjoin(Inventory, Product.id == Inventory.product_id)
            .where(*cond)
            .group_by(Product.id, Product.sku, Product.name, Product.brand_id)
            .limit(10)
        )
        rows = result.all()

        # Fetch brand names
        brand_ids = {r[3] for r in rows if r[3]}
        brand_map = {}
        if brand_ids:
            brand_rows = (await db.execute(
                select(Brand.id, Brand.name).where(Brand.id.in_(brand_ids))
            )).all()
            brand_map = {r[0]: r[1] for r in brand_rows}

        for r in rows:
            qty = r[4] or 0
            safety = r[5] or 0
            if qty <= 0:
                stock_status = "out_of_stock"
            elif qty <= safety:
                stock_status = "low_stock"
            else:
                stock_status = "in_stock"
            matched_products.append({
                "id": r[0],
                "sku": r[1],
                "name": r[2],
                "brand_name": brand_map.get(r[3]),
                "stock_qty": qty,
                "stock_status": stock_status,
                "unit_price": float(r[6]) if r[6] is not None else None,
            })
    else:
        # No MPN — brand keyword search
        brand_result = await db.execute(
            select(Brand.id, Brand.name).where(Brand.deleted_at.is_(None)).limit(5)
        )
        brand_rows = brand_result.all()
        for br in brand_rows:
            if br[1] and br[1].lower() in inquiry_text.lower():
                prod_result = await db.execute(
                    select(
                        Product.id, Product.sku, Product.name, Product.brand_id,
                        func.coalesce(func.sum(Inventory.quantity), 0).label("qty"),
                        func.coalesce(func.sum(Inventory.safety_stock), 0).label("safety"),
                        func.min(Inventory.unit_price).label("unit_price"),
                    )
                    .outerjoin(Inventory, Product.id == Inventory.product_id)
                    .where(Product.brand_id == br[0], Product.deleted_at.is_(None))
                    .group_by(Product.id, Product.sku, Product.name, Product.brand_id)
                    .limit(5)
                )
                for r in prod_result.all():
                    qty = r[4] or 0
                    safety = r[5] or 0
                    stock_status = "out_of_stock" if qty <= 0 else ("low_stock" if qty <= safety else "in_stock")
                    matched_products.append({
                        "id": r[0], "sku": r[1], "name": r[2],
                        "brand_name": br[1], "stock_qty": qty,
                        "stock_status": stock_status,
                        "unit_price": float(r[6]) if r[6] is not None else None,
                    })

    # --- C4: Find alternatives for out-of-stock matched products ---
    all_alternatives = []
    seen_alt_ids = set()
    out_of_stock_ids = [p["id"] for p in matched_products if p["stock_status"] == "out_of_stock"]
    for pid in out_of_stock_ids:
        try:
            alt_result = await suggest_eol_alternatives(db, pid)
            logger.info(f"[C4] suggest_eol_alternatives({pid}): {len(alt_result.get('alternatives', []))} alts")
            for alt in alt_result.get("alternatives", []):
                if alt["product_id"] not in seen_alt_ids:
                    seen_alt_ids.add(alt["product_id"])
                    all_alternatives.append(alt)
        except Exception as e:
            logger.warning(f"[C4] suggest_eol_alternatives({pid}) failed: {e}")
    all_alternatives = all_alternatives[:5]

    # --- Step 3: Build product context for AI (include price if available) ---
    if matched_products:
        lines = []
        for p in matched_products:
            price_str = f"，含税参考价 ¥{p['unit_price']:.2f}/件" if p.get("unit_price") else ""
            stock_label = "有货" if p["stock_status"] == "in_stock" else ("库存紧张" if p["stock_status"] == "low_stock" else "缺货")
            lines.append(
                f"- [{p['brand_name'] or '未知品牌'}] {p['name']} "
                f"(型号: {p['sku'] or 'N/A'}, 库存: {p['stock_qty']}件, 状态: {stock_label}{price_str})"
            )
        product_context = "\n".join(lines)
        product_summary = f"找到 {len(matched_products)} 个匹配产品"
    else:
        product_context = "未能在产品目录中找到匹配型号，请人工跟进。"
        product_summary = "未匹配到产品目录"

    # --- Step 4: Customer context ---
    customer_context = ""
    if customer_id:
        cust = (await db.execute(
            select(Customer).where(Customer.id == customer_id)
        )).scalars().first()
        if cust:
            customer_context = (
                f"客户：{cust.name}，行业：{cust.industry or '未知'}，"
                f"等级：{cust.level or '未知'}，最近跟进：{cust.updated_at or '无'}"
            )

    # --- Step 5: Generate AI reply ---
    system_prompt = (
        "你是一个专业的电子元器件分销商客服代表。你的职责是快速、准确地回复客户询价，"
        "并引导客户进入下一步采购流程。\n\n"
        "回复要求：\n"
        "- 专业、友好、有耐心\n"
        "- 如产品有含税参考价，可直接告知客户（单位：元/件），无需估算\n"
        "- 库存状态：明确说明有货/缺货/库存紧张\n"
        "- 缺货时说明预计到货时间或建议替代\n"
        "- 缺少信息时，主动询问：交期要求\n"
        "- 引导客户留下联系方式以便销售跟进\n"
        "- 回复控制在150字以内\n"
        "- 以【AI辅助回复】开头，末尾注明\"以上仅供参考，价格以我司正式报价单为准\""
    )

    user_prompt = (
        f"客户询价内容：\n{inquiry_text}\n\n"
        f"{customer_context}\n\n"
        f"匹配产品信息：\n{product_context}"
    )

    try:
        reply_text = await ai_client.chat(
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": user_prompt}],
            temperature=0.4,
            max_tokens=500,
        )
    except Exception:
        logger.exception("inquiry_auto_reply AI failed")
        reply_text = None

    if not reply_text:
        reply_text = (
            f"感谢您的询价！您的需求已收到，{product_summary}。"
            f"我们的销售团队将在1个工作日内与您联系，请留下您的联系方式以便更快跟进。"
        )
    else:
        # Hallucination guard: fix common small-model artefacts
        reply_text = re.sub(r'\d{9,}', 'X', reply_text)
        reply_text = re.sub(r'\$[\d\-NGn]+-\d+', '含税价请询价', reply_text)
        reply_text = re.sub(r'(\d)\1{5,}', 'X', reply_text)

        if reply_text:
            char_counts = Counter(reply_text.replace(' ', '').replace('\n', ''))
            if char_counts:
                top_char, top_count = char_counts.most_common(1)[0]
                total_chars = sum(char_counts.values())
                if top_count / max(total_chars, 1) > 0.30:
                    product_names = ', '.join(p['sku'] for p in matched_products) if matched_products else inquiry_text[:20]
                    reply_text = (
                        f"【AI辅助回复】感谢您的询价！您的需求（{product_names}）已收到，"
                        f"我们的销售团队将在1个工作日内与您联系确认库存和报价，请保持联系方式畅通。以上仅供参考，价格以我司正式报价单为准。"
                    )

    # Confidence
    if matched_products:
        in_stock = any(p["stock_status"] == "in_stock" for p in matched_products)
        confidence = 0.85 if in_stock else 0.60
    else:
        confidence = 0.30

    # --- Step 6: Persist Inquiry record ---
    inquiry = Inquiry(
        customer_id=customer_id,
        channel=channel,
        contact_name=contact_name,
        contact_info=contact_info,
        inquiry_text=inquiry_text,
        reply_text=reply_text,
        status="replied",
        matched_products=json.dumps(matched_products, ensure_ascii=False),
        ai_confidence=confidence,
    )
    db.add(inquiry)
    await db.flush()

    summary = f"新询价：{inquiry_text[:30]}{'...' if len(inquiry_text) > 30 else ''}"

    return {
        "inquiry_id": inquiry.id,
        "reply_text": reply_text,
        "confidence": confidence,
        "matched_products": matched_products,
        "alternatives": all_alternatives,
        "created_opportunity_id": None,
        "summary": summary,
    }
