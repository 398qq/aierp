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
    lead_time_days_total = 0
    quality_issues = 0
    for po in pos_12m:
        if po[1] in ("completed", "received", "delivered"):
            total_completed += 1
            # Lead time = created_at → (expected or arrival)
            if po[2] and po[4]:
                lt = (po[2] - po[4]).days
                if lt >= 0:
                    lead_time_days_total += lt
            # On-time: positive or zero late days
            if po[2] and po[4] and po[2] >= po[4]:
                on_time_count += 1
            elif po[1] == "completed":
                # If no expected_date, treat as on-time
                if po[2] is None:
                    on_time_count += 1
            # Quality issues from notes
            if po[3] and any(kw in (po[3] or "").lower() for kw in ("quality", "defect", "damage", "退货", "质量问题", "次品", "不良")):
                quality_issues += 1

    on_time_rate = round(on_time_count / total_completed * 100, 1) if total_completed > 0 else None
    avg_lead_time = round(lead_time_days_total / total_completed, 1) if total_completed > 0 else None

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
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链管理专家，擅长供应商绩效评估和评分卡设计。"},
         {"role": "user", "content": supplier_scorecard_prompt(sc_data)}],
        schema,
    )
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

    for po in recent_pos:
        if po[1] in ("completed", "received", "delivered") and po[2] and po[3]:
            delay = (po[2] - po[3]).days
            if delay < 0:
                recent_delays += 1
                total_delay_days += abs(delay)
            last_delivery_date = po[2] if last_delivery_date is None else max(last_delivery_date, po[2])

    avg_delay_days = round(total_delay_days / recent_delays, 1) if recent_delays > 0 else 0

    # Delay trend: compare first 3 months vs last 3 months
    three_months_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
    early_delays = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered")
                       and po[2] and po[3] and (po[2] - po[3]).days < 0 and po[3] < three_months_ago)
    late_delays = sum(1 for po in recent_pos if po[1] in ("completed", "received", "delivered")
                      and po[2] and po[3] and (po[2] - po[3]).days < 0 and po[3] >= three_months_ago)

    delay_trend = "稳定"
    if late_delays > early_delays * 1.5:
        delay_trend = "恶化中"
    elif late_delays < early_delays * 0.5:
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
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链风险分析师，擅长预测交付延迟和制定缓解方案。"},
         {"role": "user", "content": supplier_delay_prediction_prompt(delay_data)}],
        schema,
    )
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

    # Count products that are single-source (only this supplier)
    single_source_count = 0
    if current_product_ids:
        for pid in current_product_ids:
            count = (await db.execute(
                select(func.count(SupplierProduct.id)).where(
                    SupplierProduct.product_id == pid,
                    SupplierProduct.deleted_at.is_(None),
                )
            )).scalar() or 0
            if count <= 1:
                single_source_count += 1

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
                "avg_cost": f"¥{float(r[4]):.2f}" if r[4] else "无数据",
                "avg_lead_time": f"{round(float(r[5]), 1)}天" if r[5] else "无数据",
            })

    # Quick score assessment for current supplier (simplified for alternatives context)
    score_text = "未评估"
    datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365)
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
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件供应链优化专家，擅长供应商替代分析和多元化策略。"},
         {"role": "user", "content": supplier_alternatives_prompt(alt_data)}],
        schema,
    )
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

    # Price change rate
    price_change_pct = "无数据"
    if current_price and price_6m_ago and float(price_6m_ago) > 0:
        change = (float(current_price) - float(price_6m_ago)) / float(price_6m_ago) * 100
        price_change_pct = f"{change:.1f}"

    # Market benchmark (peer avg price for same products from other suppliers)
    product_ids = [r[0] for r in (await db.execute(
        select(SupplierProduct.product_id).where(
            SupplierProduct.supplier_id == supplier_id,
            SupplierProduct.deleted_at.is_(None),
        )
    )).all()]

    peer_avg_price = None
    if product_ids:
        peer_avg_price = (await db.execute(
            select(func.avg(SupplierProduct.cost_price)).where(
                SupplierProduct.product_id.in_(product_ids),
                SupplierProduct.supplier_id != supplier_id,
                SupplierProduct.cost_price.isnot(None),
                SupplierProduct.deleted_at.is_(None),
            )
        )).scalar()

    premium_discount = "无数据"
    if current_price and peer_avg_price and float(peer_avg_price) > 0:
        diff = (float(current_price) - float(peer_avg_price)) / float(peer_avg_price) * 100
        sign = "溢价" if diff > 0 else "折价"
        premium_discount = f"{sign}{abs(diff):.1f}%"

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
        "market_benchmark": f"¥{float(peer_avg_price):.4f}" if peer_avg_price else "无市场基准数据",
        "peer_avg_price": f"¥{float(peer_avg_price):.4f}" if peer_avg_price else "无数据",
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
    result = await ai_client.chat_structured(
        [{"role": "system", "content": "你是一个电子元器件采购成本分析师，擅长价格异常检测和降本策略。"},
         {"role": "user", "content": supplier_price_variance_prompt(variance_data)}],
        schema,
    )
    result["context"] = variance_data
    return result
