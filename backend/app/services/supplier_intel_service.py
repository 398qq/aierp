"""Supplier intelligence — AI-powered scorecard, delay prediction, alternatives, price variance."""

import datetime
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Supplier, SupplierProduct
from app.models.transaction import PurchaseOrder, PurchaseOrderItem

logger = logging.getLogger(__name__)


async def get_supplier_scorecard(db: AsyncSession, supplier_id: int) -> dict:
    """AI-powered comprehensive supplier scorecard with delivery, quality, price, stability ratings."""

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")

    # Product stats
    product_count = (await db.execute(
        select(func.count(SupplierProduct.id)).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )).scalar() or 0

    avg_price = (await db.execute(
        select(func.avg(SupplierProduct.cost_price)).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
            SupplierProduct.cost_price.isnot(None),
        )
    )).scalar()

    # PO stats — last 12 months
    twelve_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
    po_count = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= twelve_months_ago,
            PurchaseOrder.deleted_at.is_(None),
        )
    )).scalar() or 0

    # On-time delivery rate: count of POs where expected_date was met (or status completed without delay mention)
    pos_12m = (await db.execute(
        select(PurchaseOrder.id, PurchaseOrder.status, PurchaseOrder.expected_date, PurchaseOrder.notes, PurchaseOrder.created_at)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= twelve_months_ago,
            PurchaseOrder.deleted_at.is_(None),
        )
    )).all()

    on_time_count = 0
    total_completed = 0
    # 注意：以下使用 expected_date 而非实际收货日期，on_time_rate 和 avg_lead_time 的计算依赖
    # PO.expected_date 字段。当 PO 只有 created_at（无 expected_date）时，视为准时。
    # 这是当前数据模型的局限，真实 on-time 评估需要实际收货日期字段。
    promised_lead_time_days_total = 0
    quality_issues = 0
    for po in pos_12m:
        if po[1] in ("completed", "received", "delivered"):
            total_completed += 1
            # 计划交期（expected_date - created_at），仅在有 expected_date 时记录
            if po[2] and po[4]:
                lt = (po[2] - po[4]).days
                if lt >= 0:
                    promised_lead_time_days_total += lt
            # 准时判断：expected_date >= created_at（计划不晚于下单）
            # 注意：此条件在 expected_date 有值时几乎总为真，不能真实反映交付是否延误
            if po[2] and po[4] and po[2] >= po[4]:
                on_time_count += 1
            elif po[1] == "completed":
                # 无 expected_date 时保守视为准时
                if po[2] is None:
                    on_time_count += 1
            # 质量问题关键词检测
            if po[3] and any(kw in (po[3] or "").lower() for kw in ("quality", "defect", "damage", "退货", "质量问题", "次品", "不良")):
                quality_issues += 1

    on_time_rate = round(on_time_count / total_completed * 100, 1) if total_completed > 0 else None
    avg_lead_time = round(promised_lead_time_days_total / total_completed, 1) if total_completed > 0 else None

    # Promised lead time from supplier_products
    avg_promised_lt = (await db.execute(
        select(func.avg(SupplierProduct.lead_time_days)).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
            SupplierProduct.lead_time_days.isnot(None),
        )
    )).scalar()
    avg_promised_lt = round(float(avg_promised_lt), 1) if avg_promised_lt else None

    # Price volatility from recent POs vs average
    recent_prices = (await db.execute(
        select(func.avg(PurchaseOrderItem.unit_price))
        .select_from(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= twelve_months_ago,
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).scalar()

    price_volatility = "稳定"
    if avg_price and recent_prices:
        diff_pct = abs(float(recent_prices) - float(avg_price)) / float(avg_price) * 100
        if diff_pct > 20:
            price_volatility = "波动大"
        elif diff_pct > 10:
            price_volatility = "有波动"
        else:
            price_volatility = "稳定"

    sc_data = {
        "name": supplier.name,
        "product_lines": supplier.product_lines or "无数据",
        "product_count": product_count,
        "avg_purchase_price": f"{float(avg_price):.2f}" if avg_price else "无数据",
        "po_count_12m": po_count,
        "on_time_rate": on_time_rate if on_time_rate is not None else "无数据",
        "avg_lead_time": avg_lead_time if avg_lead_time is not None else "无数据",
        "promised_lead_time": avg_promised_lt if avg_promised_lt else "无数据",
        "quality_issues": quality_issues,
        "price_competitiveness": "请根据行业数据评估",
        "price_volatility": price_volatility,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_scorecard_prompt

    schema = {
        "overall_score": "integer 0-100",
        "delivery_score": "integer 0-100",
        "quality_score": "integer 0-100",
        "price_score": "integer 0-100",
        "stability_score": "integer 0-100",
        "assessment": "string",
        "strengths": ["string"],
        "weaknesses": ["string"],
        "tier": "string: A/B/C/D",
        "recommendations": ["string"],
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件供应链管理专家，擅长供应商绩效评估和评分卡设计。"},
             {"role": "user", "content": supplier_scorecard_prompt(sc_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"get_supplier_scorecard AI failed: {e}")
        result = {
            "overall_score": 50,
            "delivery_score": 50,
            "quality_score": 50,
            "price_score": 50,
            "stability_score": 50,
            "assessment": "AI分析暂时不可用",
            "strengths": [],
            "weaknesses": [],
            "tier": "C",
            "recommendations": [],
        }
    result["context"] = sc_data
    return result


async def predict_supplier_delay(db: AsyncSession, supplier_id: int) -> dict:
    """AI predicts delivery delay risk for a supplier using historical PO data."""

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")

    six_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180)

    # Recent orders (6 months)
    recent_pos = (await db.execute(
        select(PurchaseOrder.id, PurchaseOrder.status, PurchaseOrder.expected_date,
               PurchaseOrder.created_at, PurchaseOrder.notes)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= six_months_ago,
            PurchaseOrder.deleted_at.is_(None),
        )
        .order_by(PurchaseOrder.created_at.desc())
    )).all()

    recent_orders = len(recent_pos)
    recent_delays = 0
    total_delay_days = 0
    last_delivery_date = None

    # 注意：以下延迟计算基于 expected_date vs created_at，而非实际收货日期。
    # PO.expected_date 是计划交期字段，无实际收货日期时无法判断真实交付延误。
    # 该指标反映的是"计划交期是否合理"，而非"供应商是否准时"。
    for po in recent_pos:
        if po[1] in ("completed", "received", "delivered") and po[2] and po[3]:
            delay = (po[2] - po[3]).days
            if delay < 0:
                recent_delays += 1
                total_delay_days += abs(delay)
            last_delivery_date = po[2] if last_delivery_date is None else max(last_delivery_date, po[2])

    avg_delay_days = round(total_delay_days / recent_delays, 1) if recent_delays > 0 else 0

    # 延迟趋势：按周期内 PO 数量归一化后比较延迟率，避免周期长度不同导致的误判
    three_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    # 注意：这里的延迟仍是 expected_date vs created_at，与上面同款数据局限
    early_total = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered") and po[3] < three_months_ago)
    late_total = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered") and po[3] >= three_months_ago)
    early_delays = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered")
                       and po[2] and po[3] and (po[2] - po[3]).days < 0 and po[3] < three_months_ago)
    late_delays = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered")
                      and po[2] and po[3] and (po[2] - po[3]).days < 0 and po[3] >= three_months_ago)
    early_rate = (early_delays / early_total * 100) if early_total > 0 else 0
    late_rate = (late_delays / late_total * 100) if late_total > 0 else 0

    delay_trend = "稳定"
    if late_rate > early_rate * 1.5 and late_delays >= 2:
        delay_trend = "恶化中"
    elif late_rate < early_rate * 0.5 and early_delays >= 2:
        delay_trend = "改善中"
    elif early_delays == 0 and late_delays == 0:
        delay_trend = "无延迟记录"
    else:
        delay_trend = "稳定"

    # Pending orders (not yet completed)
    pending_pos = (await db.execute(
        select(func.count(PurchaseOrder.id), func.sum(PurchaseOrder.total_amount))
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.status.in_(["draft", "submitted", "confirmed", "in_transit"]),
            PurchaseOrder.deleted_at.is_(None),
        )
    )).first()

    pending_orders = pending_pos[0] if pending_pos else 0
    pending_amount = float(pending_pos[1]) if pending_pos and pending_pos[1] else 0

    delay_data = {
        "name": supplier.name,
        "recent_orders": recent_orders,
        "recent_delays": recent_delays,
        "avg_delay_days": avg_delay_days,
        "delay_trend": delay_trend,
        "pending_orders": pending_orders,
        "pending_amount": f"¥{pending_amount:,.2f}",
        "last_delivery_date": last_delivery_date.strftime("%Y-%m-%d") if last_delivery_date else "无数据",
        "industry_risk": "请根据实际情况评估",
        "region_risk": "请根据实际情况评估",
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_delay_prediction_prompt

    schema = {
        "delay_risk": "string: 低/中/高",
        "risk_score": "integer 0-100",
        "predicted_delay_days": "integer",
        "probability": "integer 0-100",
        "risk_factors": ["string"],
        "mitigation": ["string"],
        "alternative_suggestion": "string",
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件供应链风险分析师，擅长预测交付延迟和制定缓解方案。"},
             {"role": "user", "content": supplier_delay_prediction_prompt(delay_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"predict_supplier_delay AI failed: {e}")
        result = {
            "delay_risk": "中",
            "risk_score": 50,
            "predicted_delay_days": 7,
            "probability": 50,
            "risk_factors": [],
            "mitigation": [],
            "alternative_suggestion": "AI分析暂时不可用",
        }
    result["context"] = delay_data
    return result


async def get_supplier_alternatives(db: AsyncSession, supplier_id: int) -> dict:
    """Find and evaluate alternative suppliers with overlapping product lines."""

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")

    # Products supplied by this supplier
    current_product_ids = [r[0] for r in (await db.execute(
        select(SupplierProduct.product_id).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )).all()]

    # Count products that are single-source (only this supplier) — 单条 SQL 替代 N+1 循环
    single_source_count = 0
    if current_product_ids:
        counts = dict((await db.execute(
            select(
                SupplierProduct.product_id,
                func.count(SupplierProduct.id),
            ).where(
                SupplierProduct.product_id.in_(current_product_ids),
                SupplierProduct.deleted_at.is_(None),
            ).group_by(SupplierProduct.product_id)
        )).all())
        single_source_count = sum(1 for c in counts.values() if c <= 1)

    # Find other suppliers with overlapping products
    candidates = []
    if current_product_ids:
        candidate_rows = (await db.execute(
            select(
                Supplier.id,
                Supplier.name,
                Supplier.product_lines,
                func.count(func.distinct(SupplierProduct.product_id)).label("overlap_count"),
                func.avg(SupplierProduct.cost_price).label("avg_cost"),
                func.avg(SupplierProduct.lead_time_days).label("avg_lt"),
            )
            .select_from(Supplier)
            .join(SupplierProduct, Supplier.id == SupplierProduct.supplier_id)
            .where(
                SupplierProduct.product_id.in_(current_product_ids),
                SupplierProduct.supplier_id != supplier_id,
                SupplierProduct.deleted_at.is_(None),
                Supplier.deleted_at.is_(None),
            )
            .group_by(Supplier.id)
            .order_by(func.count(func.distinct(SupplierProduct.product_id)).desc())
            .limit(10)
        )).all()

        for r in candidate_rows:
            candidates.append({
                "supplier_id": r[0],
                "name": r[1],
                "product_lines": r[2] or "无数据",
                "overlap_products": r[3],
                "avg_cost": f"¥{float(r[4]):.2f}" if r[4] is not None else "无数据",
                "avg_lead_time": f"{round(float(r[5]), 1)}天" if r[5] is not None else "无数据",
            })

    # Quick score assessment for current supplier (simplified for alternatives context)
    score_text = "未评估"
    total_completed = (await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.status.in_(["completed", "received", "delivered"]),
            PurchaseOrder.deleted_at.is_(None),
        )
    )).scalar() or 0
    if total_completed > 0:
        score_text = f"已完成{total_completed}笔订单"

    candidates_text = "\n".join(
        f"- {c['name']} | 产品线: {c['product_lines']} | 重叠产品: {c['overlap_products']}个 | "
        f"均价: {c['avg_cost']} | 交期: {c['avg_lead_time']}"
        for c in candidates
    ) if candidates else "未找到替代供应商"

    alt_data = {
        "name": supplier.name,
        "product_lines": supplier.product_lines or "无数据",
        "score": score_text,
        "delay_risk": "请根据实际情况评估",
        "price_competitiveness": "请根据实际情况评估",
        "single_source_count": single_source_count,
        "candidates": candidates_text,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_alternatives_prompt

    schema = {
        "urgency": "string: 低/中/高",
        "recommended_alternatives": [
            {"supplier_name": "string", "product_lines": "string", "score": "integer", "advantage": "string", "switch_cost": "string"}
        ],
        "diversification_strategy": ["string"],
        "risk_assessment": "string",
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件供应链优化专家，擅长供应商替代分析和多元化策略。"},
             {"role": "user", "content": supplier_alternatives_prompt(alt_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"get_supplier_alternatives AI failed: {e}")
        result = {
            "urgency": "中",
            "recommended_alternatives": [],
            "diversification_strategy": [],
            "risk_assessment": "AI分析暂时不可用",
        }
    result["context"] = alt_data
    result["candidates"] = candidates
    return result


async def detect_supplier_price_variance(db: AsyncSession, supplier_id: int) -> dict:
    """Detect price anomalies by comparing current vs historical purchase prices."""

    supplier = (await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )).scalar_one_or_none()
    if supplier is None:
        raise ValueError("Supplier not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    three_months_ago = now - datetime.timedelta(days=90)
    six_months_ago = now - datetime.timedelta(days=180)

    # Current average price (last 3 months from PO items)
    current_price = (await db.execute(
        select(func.avg(PurchaseOrderItem.unit_price))
        .select_from(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= three_months_ago,
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).scalar()

    # Price 3-6 months ago
    price_3m_ago = (await db.execute(
        select(func.avg(PurchaseOrderItem.unit_price))
        .select_from(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at.between(six_months_ago, three_months_ago),
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).scalar()

    # Price 6-12 months ago
    twelve_months_ago = now - datetime.timedelta(days=365)
    price_6m_ago = (await db.execute(
        select(func.avg(PurchaseOrderItem.unit_price))
        .select_from(PurchaseOrderItem)
        .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at.between(twelve_months_ago, six_months_ago),
            PurchaseOrder.deleted_at.is_(None),
            PurchaseOrderItem.deleted_at.is_(None),
        )
    )).scalar()

    # Price change rate — 优先用 0-3m vs 3-6m（近期趋势），降级用 0-3m vs 6-12m
    price_change_pct = "无数据"
    if current_price and price_3m_ago and float(price_3m_ago) > 0:
        # 短期趋势：近3个月 vs 3-6个月前
        change = (float(current_price) - float(price_3m_ago)) / float(price_3m_ago) * 100
        price_change_pct = f"{change:.1f}（近3个月 vs 3-6个月前）"
    elif current_price and price_6m_ago and float(price_6m_ago) > 0:
        # 中期趋势：近3个月 vs 6-12个月前
        change = (float(current_price) - float(price_6m_ago)) / float(price_6m_ago) * 100
        price_change_pct = f"{change:.1f}（近3个月 vs 6-12个月前）"

    # Market benchmark (peer avg price for same products from other suppliers)
    product_ids = [r[0] for r in (await db.execute(
        select(SupplierProduct.product_id).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )).all()]

    # 注意：此字段是其他供应商的 catalog 标价（SupplierProduct.cost_price），
    # 而非其实际 PO 成交价。与 current_price（实际采购均价）性质不同，
    # "溢价/折价" 标签仅作参考，不反映真实的同行价格竞争力。
    peer_catalog_price = None
    if product_ids:
        peer_catalog_price = (await db.execute(
            select(func.avg(SupplierProduct.cost_price)).where(
                SupplierProduct.product_id.in_(product_ids),
                SupplierProduct.supplier_id != supplier_id,
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar()

    premium_discount = "无数据（需同行 PO 成交价数据）"
    if current_price and peer_catalog_price and float(peer_catalog_price) > 0:
        diff = (float(current_price) - float(peer_catalog_price)) / float(peer_catalog_price) * 100
        sign = "溢价" if diff > 0 else "折价"
        premium_discount = f"{sign}{abs(diff):.1f}%（参考同行目录价）"

    # Per-product price anomalies (products with significant price changes)
    anomaly_products_text = "无显著异常"
    if current_product_ids := product_ids:
        # Get per-product average unit price from recent POs
        product_price_rows = (await db.execute(
            select(
                PurchaseOrderItem.product_id,
                func.avg(PurchaseOrderItem.unit_price).label("avg_price_recent"),
                func.count(PurchaseOrderItem.id).label("transactions"),
            )
            .select_from(PurchaseOrderItem)
            .join(PurchaseOrder, PurchaseOrderItem.order_id == PurchaseOrder.id)
            .where(
                PurchaseOrder.supplier_id == supplier_id,
                PurchaseOrder.created_at >= six_months_ago,
                PurchaseOrder.deleted_at.is_(None),
                PurchaseOrderItem.deleted_at.is_(None),
                PurchaseOrderItem.product_id.in_(current_product_ids),
            )
            .group_by(PurchaseOrderItem.product_id)
        )).all()

        # Get supplier_product cost for comparison
        sp_costs = dict(
            (await db.execute(
                select(SupplierProduct.product_id, SupplierProduct.cost_price).where(
                    SupplierProduct.supplier_id == supplier_id,
                    SupplierProduct.product_id.in_(current_product_ids),
                    SupplierProduct.cost_price.isnot(None),
                    SupplierProduct.deleted_at.is_(None),
                )
            )).all() or []
        )

        anomaly_parts = []
        for r in product_price_rows:
            pid, avg_recent, _txns = r[0], float(r[1]) if r[1] else 0, r[2]
            base_cost = float(sp_costs.get(pid, 0) or 0)
            if base_cost > 0 and avg_recent > 0:
                variance = (avg_recent - base_cost) / base_cost * 100
                if abs(variance) > 15:  # flag if variance > 15%
                    anomaly_parts.append(
                        f"产品#{pid}: 近期均价¥{avg_recent:.4f} vs 成本¥{base_cost:.4f} (偏差{variance:.1f}%)"
                    )

        if anomaly_parts:
            anomaly_products_text = "\n".join(anomaly_parts[:10])

    variance_data = {
        "name": supplier.name,
        "current_avg_price": f"¥{float(current_price):.4f}" if current_price else "无数据",
        "price_3m_ago": f"¥{float(price_3m_ago):.4f}" if price_3m_ago else "无数据",
        "price_6m_ago": f"¥{float(price_6m_ago):.4f}" if price_6m_ago else "无数据",
        "price_change_pct": price_change_pct,
        "market_benchmark": f"¥{float(peer_catalog_price):.4f}" if peer_catalog_price else "无市场基准数据（需同行 PO 成交价）",
        "peer_avg_price": f"¥{float(peer_catalog_price):.4f}" if peer_catalog_price else "无数据（需同行目录价）",
        "premium_discount": premium_discount,
        "anomaly_products": anomaly_products_text,
    }

    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_price_variance_prompt

    schema = {
        "price_status": "string: 偏高/正常/偏低",
        "variance_score": "integer 0-100",
        "anomaly_products": [
            {"product_name": "string", "current_price": "number", "expected_price": "number", "variance_pct": "number", "reason": "string"}
        ],
        "trend_analysis": "string",
        "cost_saving_opportunities": ["string"],
        "negotiation_points": ["string"],
    }
    try:
        result = await ai_client.chat_structured(
            [{"role": "system", "content": "你是一个电子元器件采购成本分析师，擅长价格异常检测和降本策略。"},
             {"role": "user", "content": supplier_price_variance_prompt(variance_data)}],
            schema,
        )
    except ValueError as e:
        logging.getLogger(__name__).warning(f"Price variance AI failed for supplier {supplier_id}: {e}")
        result = {
            "price_status": "正常",
            "variance_score": 50,
            "anomaly_products": [],
            "trend_analysis": "AI分析暂时不可用",
            "cost_saving_opportunities": [],
            "negotiation_points": [],
        }
    result["context"] = variance_data
    return result


# ---------------------------------------------------------------------------
# 6. get_supplier_360
# ---------------------------------------------------------------------------


async def get_supplier_360(db: AsyncSession, supplier_id: int) -> dict:
    """Comprehensive 360° supplier analysis that aggregates data from all supplier
    intelligence functions into one holistic view."""
    from datetime import datetime, timedelta, timezone

    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise ValueError(f"供应商 #{supplier_id} 不存在")

    now = datetime.now(timezone.utc)
    six_months_ago = now - timedelta(days=180)

    # PO history
    po_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.created_at >= six_months_ago,
            PurchaseOrder.deleted_at.is_(None),
        )
    )
    pos = po_result.scalars().all()
    total_amount = sum(float(po.total_amount) for po in pos)
    delivery_days = []
    for po in pos:
        if po.expected_date and po.created_at:
            d = (po.expected_date - po.created_at).days if hasattr(po.expected_date - po.created_at, 'days') else 0
            delivery_days.append(d)
    on_time = sum(1 for po in pos if po.status == "completed")
    po_history = {
        "total_pos": len(pos),
        "total_amount": total_amount,
        "avg_delivery_days": round(sum(delivery_days) / len(delivery_days), 1) if delivery_days else 0,
        "on_time_rate": round(on_time / len(pos) * 100, 1) if pos else 0,
    }

    # Use a single efficient AI call with pre-computed context data
    from app.services.ai.client import ai_client

    context_data = {
        "name": supplier.name,
        "supplier_type": supplier.supplier_type or "未知",
        "certifications": supplier.certifications or "无",
        "region": supplier.region or "未知",
        "product_lines": supplier.product_lines or "未知",
        "financial_rating": supplier.financial_rating or "C",
        "total_pos": po_history["total_pos"],
        "total_amount": po_history["total_amount"],
        "linked_product_count": (await db.execute(
            select(func.count(SupplierProduct.product_id)).where(SupplierProduct.supplier_id == supplier_id)
        )).scalar() or 0,
    }

    output_schema = {
        "overall_score": "integer 0-100",
        "tier": "string: A/B/C/D",
        "summary": "string",
        "assessment": "string",
        "key_strengths": "list of strings",
        "key_weaknesses": "list of strings",
        "recommendations": "list of strings",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件分销行业供应商管理专家。返回简洁有效的JSON。"},
                {"role": "user", "content": (
                    f"对供应商{context_data['name']}做360度评估。"
                    f"类型:{context_data['supplier_type']}，认证:{context_data['certifications']}，"
                    f"区域:{context_data['region']}，产品线:{context_data['product_lines']}，"
                    f"财务评级:{context_data['financial_rating']}，"
                    f"采购订单{context_data['total_pos']}笔总额{context_data['total_amount']}元，"
                    f"关联产品{context_data['linked_product_count']}个。"
                    f"给出综合评分(0-100)、等级(A/B/C/D)、一句话总结、详细评估(50-100字)、"
                    f"3-5个优势、2-3个劣势、3-5条建议。"
                )},
            ],
            output_schema,
            max_tokens=2048,
        )
        ai_result["po_history_summary"] = po_history
        return ai_result
    except Exception as e:
        logger.error(f"Supplier 360 failed #{supplier_id}: {e}")
        return {
            "overall_score": 50, "tier": "C",
            "summary": "AI分析暂时不可用",
            "assessment": "",
            "key_strengths": [], "key_weaknesses": [], "recommendations": [],
            "po_history_summary": po_history,
        }


# ---------------------------------------------------------------------------
# 7. compare_suppliers
# ---------------------------------------------------------------------------


async def compare_suppliers(db: AsyncSession, supplier_ids: list[int]) -> dict:
    """Compare multiple suppliers across dimensions using local scoring."""

    if len(supplier_ids) < 2:
        raise ValueError("至少需要2个供应商进行比较")

    from collections import defaultdict
    from app.models.transaction import PurchaseOrder

    # 批量查询，避免 N+1
    supplier_rows = await db.execute(
        select(Supplier).where(Supplier.id.in_(supplier_ids), Supplier.deleted_at.is_(None))
    )
    supplier_map = {s.id: s for s in supplier_rows.scalars().all()}

    po_rows = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.supplier_id.in_(supplier_ids),
            PurchaseOrder.deleted_at.is_(None),
        )
    )
    po_by_supplier: dict[int, list] = defaultdict(list)
    for po in po_rows.scalars().all():
        po_by_supplier[po.supplier_id].append(po)

    sp_rows = await db.execute(
        select(SupplierProduct).where(SupplierProduct.supplier_id.in_(supplier_ids))
    )
    sp_by_supplier: dict[int, list] = defaultdict(list)
    for sp in sp_rows.scalars().all():
        sp_by_supplier[sp.supplier_id].append(sp)

    suppliers_data = []
    for sid in supplier_ids:
        supplier = supplier_map.get(sid)
        if not supplier:
            continue

        pos = po_by_supplier.get(sid, [])
        sps = sp_by_supplier.get(sid, [])
        total_po_amount = sum(float(po.total_amount) for po in pos)

        # 评分说明：
        # - 认证资质：证书存在得20分，否则5分（参考ISO9001等认证标准）
        # - 财务评级：A=20/B=15/C=10/D=5（参照标准普尔评级映射）
        # - 采购历史：每张PO 3分，上限20分（历史合作深度指标）
        # - 产品覆盖：每关联1个产品4分，上限20分（供应链广度指标）
        # - 供应商类型：原厂/授权分销商20分，其他12分（供货可靠性保障）
        cert_score = 20 if (supplier.certifications and supplier.certifications not in ("无", "")) else 5
        fin_score = {"A": 20, "B": 15, "C": 10, "D": 5}.get(supplier.financial_rating or "C", 10)
        po_score = min(len(pos) * 3, 20)
        prod_score = min(len(sps) * 4, 20)
        type_score = 20 if supplier.supplier_type in ("授权分销商", "原厂") else 12
        total_score = cert_score + fin_score + po_score + prod_score + type_score

        suppliers_data.append({
            "name": supplier.name,
            "type": supplier.supplier_type or "未知",
            "region": supplier.region or "未知",
            "certifications": supplier.certifications or "无",
            "financial_rating": supplier.financial_rating or "C",
            "product_lines": supplier.product_lines or "未知",
            "total_po_amount": total_po_amount,
            "po_count": len(pos),
            "linked_products": len(sps),
            "total_score": total_score,
            "tier": "A" if total_score >= 80 else "B" if total_score >= 60 else "C" if total_score >= 40 else "D",
        })

    # Sort by total_score descending
    suppliers_data.sort(key=lambda x: x["total_score"], reverse=True)
    ranking = [
        {"rank": i + 1, "supplier_name": s["name"], "total_score": s["total_score"], "tier": s["tier"]}
        for i, s in enumerate(suppliers_data)
    ]

    # Build comparison matrix locally
    dimensions = [
        {"dimension": "认证资质", "weight": 20, "scores": {}},
        {"dimension": "财务评级", "weight": 20, "scores": {}},
        {"dimension": "采购历史", "weight": 20, "scores": {}},
        {"dimension": "产品覆盖", "weight": 20, "scores": {}},
        {"dimension": "供应商类型", "weight": 20, "scores": {}},
    ]
    for s in suppliers_data:
        dimensions[0]["scores"][s["name"]] = 20 if s["certifications"] and s["certifications"] != "无" else 5
        dimensions[1]["scores"][s["name"]] = {"A": 20, "B": 15, "C": 10, "D": 5}.get(s["financial_rating"], 10)
        dimensions[2]["scores"][s["name"]] = min(s["po_count"] * 3, 20)
        dimensions[3]["scores"][s["name"]] = min(s["linked_products"] * 4, 20)
        dimensions[4]["scores"][s["name"]] = 20 if s["type"] in ("授权分销商", "原厂") else 12

    # 空结果保护 — 路由层 ValueError → 404
    if not suppliers_data:
        raise ValueError("未找到有效的供应商数据（所有ID均不存在或已删除）")

    # 每个维度的 winner
    best_in_category = []
    for dim in dimensions:
        if not dim["scores"]:
            continue
        winner_name = max(dim["scores"], key=dim["scores"].get)
        winner_score = dim["scores"][winner_name]
        best_in_category.append({
            "category": dim["dimension"],
            "winner": winner_name,
            "reason": f"得分{winner_score}",
        })

    top = ranking[0]
    summary = f"共比较{len(ranking)}家供应商。{top['supplier_name']}综合评分最高({top['total_score']}分)，在资质、产品覆盖、采购历史等维度表现突出。"
    recommendation = f"推荐首选: {top['supplier_name']} (评分: {top['total_score']})"

    return {
        "comparison_matrix": dimensions,
        "overall_ranking": ranking,
        "best_in_category": best_in_category,
        "recommendation": recommendation,
        "summary": summary,
        "context": {"compared_ids": supplier_ids},
    }


# ---------------------------------------------------------------------------
# 8. get_supplier_negotiation
# ---------------------------------------------------------------------------


async def get_supplier_negotiation(db: AsyncSession, supplier_id: int) -> dict:
    """AI-powered negotiation strategy generator for procurement talks with a supplier."""
    from app.models.transaction import PurchaseOrder
    from app.services.ai.client import ai_client
    from app.services.ai.prompts import supplier_negotiation_prompt

    result = await db.execute(
        select(Supplier).where(Supplier.id == supplier_id, Supplier.deleted_at.is_(None))
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise ValueError(f"供应商 #{supplier_id} 不存在")

    # PO history
    po_result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.supplier_id == supplier_id)
    )
    pos = po_result.scalars().all()
    total_amount = sum(float(po.total_amount) for po in pos)

    # Product count
    sp_count = (await db.execute(
        select(func.count(SupplierProduct.product_id)).where(SupplierProduct.supplier_id == supplier_id)
    )).scalar() or 0

    # Average price from supplier_products
    avg_price_result = await db.execute(
        select(func.avg(SupplierProduct.cost_price)).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.cost_price.is_not(None),
        )
    )
    avg_price = avg_price_result.scalar()
    avg_price_str = f"{float(avg_price):.4f}" if avg_price else "无数据"

    # Alternative count: suppliers with overlapping products
    alt_count = 0
    if sp_count > 0:
        sp_product_ids = (await db.execute(
            select(SupplierProduct.product_id).where(SupplierProduct.supplier_id == supplier_id)
        )).scalars().all()
        if sp_product_ids:
            alt_count = (await db.execute(
                select(func.count(func.distinct(SupplierProduct.supplier_id))).where(
                    SupplierProduct.product_id.in_(sp_product_ids),
                    SupplierProduct.supplier_id != supplier_id,
                )
            )).scalar() or 0

    neg_data = {
        "name": supplier.name,
        "supplier_type": supplier.supplier_type or "未知",
        "product_lines": supplier.product_lines or "未知",
        "financial_rating": supplier.financial_rating or "未知",
        "region": supplier.region or "未知",
        "total_amount": total_amount,
        "po_count": len(pos),
        "product_count": sp_count,
        "avg_price": avg_price_str,
        "alternative_count": alt_count,
        "price_competitiveness": "请根据市场数据评估",
    }

    output_schema = {
        "negotiation_strategy": "string",
        "price_target": "string",
        "talking_points": "list of strings",
        "leverage_points": "list of strings",
        "fallback_plan": "string",
        "suggested_approach": "string",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件采购谈判专家。返回简洁有效的JSON。"},
                {"role": "user", "content": supplier_negotiation_prompt(neg_data)},
            ],
            output_schema,
            max_tokens=2048,
        )
        ai_result["context"] = neg_data
        return ai_result
    except Exception as e:
        logger.error(f"Negotiation assistant failed for #{supplier_id}: {e}")
        return {
            "negotiation_strategy": f"AI分析暂时不可用: {e}",
            "price_target": "",
            "talking_points": [],
            "leverage_points": [],
            "fallback_plan": "",
            "suggested_approach": "",
            "context": {"error": str(e)},
        }
