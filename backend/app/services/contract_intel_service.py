"""Contract Intelligence Service — AI-powered contract analysis, risk assessment,
expiry scanning, and rebate tracking for electronics distribution ERP."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Contract, PaymentRecord
from app.models.sales import SalesOrder
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    contract_extract_prompt,
    contract_expiry_prompt,
    contract_rebate_prompt,
    contract_risk_prompt,
)

logger = logging.getLogger(__name__)

CONTRACT_EXTRACT_SYSTEM = (
    "你是一个商业合同分析专家，精通电子元器件分销行业合同审核。"
    "你必须返回符合要求的有效 JSON，不要输出任何解释。"
)

CONTRACT_RISK_SYSTEM = (
    "你是一个商业合同风险审核专家，精通电子元器件分销行业的合同风险评估。"
    "你必须返回符合要求的有效 JSON，不要输出任何解释。"
)

CONTRACT_EXPIRY_SYSTEM = (
    "你是一个合同管理专家，精通电子元器件分销行业合同的续约策略。"
    "你必须返回符合要求的有效 JSON，不要输出任何解释。"
)

CONTRACT_REBATE_SYSTEM = (
    "你是一个销售激励分析专家，精通电子元器件分销行业返利与激励方案。"
    "你必须返回符合要求的有效 JSON，不要输出任何解释。"
)

EXTRACT_SCHEMA = {
    "contract_type": "string",
    "key_terms": "list of dicts: {clause: string, content: string, importance: string, risk_flag: string}",
    "payment_terms": "string",
    "delivery_terms": "string",
    "warranty_terms": "string",
    "liability_clauses": "string",
    "termination_clauses": "string",
    "special_conditions": "string",
    "missing_clauses": "list of strings",
    "overall_risk": "string: 低/中/高",
}

RISK_SCHEMA = {
    "risk_score": "integer 0-100",
    "risk_level": "string: 低/中/高",
    "financial_risk": "string",
    "legal_risk": "string",
    "operational_risk": "string",
    "risk_items": "list of dicts: {item: string, risk: string, impact: string, mitigation: string}",
    "recommendation": "string: 建议签署/修改后签署/不建议签署",
    "negotiation_priority": "list of strings",
}

EXPIRY_SCHEMA = {
    "expiring_soon": "list of dicts: {contract_no: string, customer_name: string, amount: number, expire_date: string, days_left: integer, renewal_probability: integer, action: string}",
    "high_risk_expiries": "list of strings",
    "renewal_opportunities": "list of strings",
    "total_at_risk_amount": "number",
    "priority_actions": "list of strings",
    "auto_renewal_candidates": "list of strings",
}

REBATE_SCHEMA = {
    "rebate_achieved": "number",
    "rebate_projected": "number",
    "rebate_tier_progress": "string",
    "gap_to_next_tier": "number",
    "optimization_suggestions": "list of strings",
    "upsell_opportunities": "list of strings",
    "margin_impact": "string",
}


def _build_credit_rating(
    avg_payment_days: float,
    late_count: int,
    fulfillment_rate: float,
) -> str:
    """Derive a human-readable credit rating string from payment and order data."""
    if avg_payment_days <= 15 and late_count <= 2 and fulfillment_rate >= 90:
        rating = "AAA"
    elif avg_payment_days <= 30 and late_count <= 5:
        rating = "AA"
    elif avg_payment_days <= 45 and late_count <= 10:
        rating = "A"
    elif avg_payment_days <= 60:
        rating = "B"
    elif avg_payment_days <= 90:
        rating = "C"
    else:
        rating = "D"
    return f"{rating} (平均回款{avg_payment_days}天, 逾期{late_count}次, 履约率{fulfillment_rate}%)"


async def extract_contract_terms(db: AsyncSession, contract_id: int) -> dict:
    """Query Contract with customer info and linked sales orders, then call AI to
    analyze the notes field for key contract terms."""
    datetime.now(timezone.utc)

    result = await db.execute(
        select(Contract, Customer)
        .join(Customer, Contract.customer_id == Customer.id)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.first()
    if not row:
        return {"error": f"合同 #{contract_id} 不存在"}

    contract, customer = row

    # Build linked order summary
    linked_orders_text = "无关联订单"
    if contract.sales_order_id:
        so_result = await db.execute(
            select(SalesOrder).where(
                SalesOrder.id == contract.sales_order_id,
                SalesOrder.deleted_at.is_(None),
            )
        )
        so = so_result.scalar_one_or_none()
        if so:
            linked_orders_text = f"订单号: {so.order_no or '—'}, 金额: {float(so.total_amount):.2f}, 状态: {so.status}"

    contract_data = {
        "title": contract.title,
        "contract_no": contract.contract_no or "无",
        "customer_name": customer.name,
        "amount": float(contract.amount),
        "signed_date": contract.signed_date.strftime("%Y-%m-%d")
        if contract.signed_date
        else "无数据",
        "expire_date": contract.expire_date.strftime("%Y-%m-%d")
        if contract.expire_date
        else "无数据",
        "notes": contract.notes or "无",
        "linked_orders": linked_orders_text,
    }

    try:
        return await ai_client.chat_structured(
            [
                {"role": "system", "content": CONTRACT_EXTRACT_SYSTEM},
                {"role": "user", "content": contract_extract_prompt(contract_data)},
            ],
            EXTRACT_SCHEMA,
        )
    except Exception as e:
        logger.error(f"合同条款提取失败 #{contract_id}: {e}")
        return {
            "contract_type": "未知",
            "key_terms": [],
            "payment_terms": "",
            "delivery_terms": "",
            "warranty_terms": "",
            "liability_clauses": "",
            "termination_clauses": "",
            "special_conditions": "",
            "missing_clauses": [],
            "overall_risk": f"AI分析失败: {e}",
        }


async def assess_contract_risk(db: AsyncSession, contract_id: int) -> dict:
    """Query Contract, customer payment history for credit_rating (avg payment days,
    late count), fulfillment_rate (completed orders / total orders), then call AI
    with contract_risk_prompt."""
    datetime.now(timezone.utc)

    result = await db.execute(
        select(Contract, Customer)
        .join(Customer, Contract.customer_id == Customer.id)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.first()
    if not row:
        return {"error": f"合同 #{contract_id} 不存在"}

    contract, customer = row
    cid = contract.customer_id

    # --- Payment history stats ---
    pmt_result = await db.execute(
        select(PaymentRecord).where(
            PaymentRecord.customer_id == cid,
            PaymentRecord.payment_date.isnot(None),
            PaymentRecord.deleted_at.is_(None),
        )
    )
    payments = pmt_result.scalars().all()

    so_result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == cid,
            SalesOrder.deleted_at.is_(None),
        )
    )
    sales_orders = so_result.scalars().all()
    so_map: dict[int, SalesOrder] = {so.id: so for so in sales_orders}

    payment_days: list[int] = []
    late_count = 0
    for p in payments:
        so = so_map.get(p.sales_order_id)
        if so and p.payment_date:
            days = (p.payment_date - so.created_at).days
            payment_days.append(days)
            if days > 30:
                late_count += 1

    avg_payment_days = (
        round(sum(payment_days) / len(payment_days), 1) if payment_days else 0
    )

    # --- Fulfillment rate ---
    total_orders = len(sales_orders)
    completed = sum(1 for so in sales_orders if so.status == "completed")
    fulfillment_rate = (
        round(completed / total_orders * 100, 1) if total_orders > 0 else 0
    )

    credit_rating_str = _build_credit_rating(
        avg_payment_days, late_count, fulfillment_rate
    )

    # Extract key terms for AI context (from notes if available, otherwise summary)
    key_terms_text = contract.notes or (
        f"合同金额{float(contract.amount):.2f}元, 签署日{contract.signed_date}, 到期日{contract.expire_date}"
    )

    contract_data = {
        "title": contract.title,
        "customer_name": customer.name,
        "amount": float(contract.amount),
        "key_terms": key_terms_text,
        "credit_rating": credit_rating_str,
        "fulfillment_rate": fulfillment_rate,
    }

    try:
        return await ai_client.chat_structured(
            [
                {"role": "system", "content": CONTRACT_RISK_SYSTEM},
                {"role": "user", "content": contract_risk_prompt(contract_data)},
            ],
            RISK_SCHEMA,
        )
    except Exception as e:
        logger.error(f"合同风险评估失败 #{contract_id}: {e}")
        return {
            "risk_score": 0,
            "risk_level": "未知",
            "financial_risk": f"AI分析失败: {e}",
            "legal_risk": "",
            "operational_risk": "",
            "risk_items": [],
            "recommendation": "",
            "negotiation_priority": [],
        }


async def scan_contract_expiry(db: AsyncSession) -> dict:
    """Query all contracts expiring within 60 days, customer renewal history
    (previous contracts), then call AI with contract_expiry_prompt."""
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=60)

    # --- Expiring contracts ---
    exp_result = await db.execute(
        select(Contract)
        .where(
            Contract.expire_date.isnot(None),
            Contract.expire_date >= now,
            Contract.expire_date <= cutoff,
            Contract.deleted_at.is_(None),
        )
        .order_by(Contract.expire_date)
    )
    expiring = exp_result.scalars().all()

    expiring_lines: list[str] = []
    customer_ids: list[int] = []
    for c in expiring:
        cust_result = await db.execute(
            select(Customer.name).where(
                Customer.id == c.customer_id,
                Customer.deleted_at.is_(None),
            )
        )
        cname = cust_result.scalar_one_or_none() or f"客户#{c.customer_id}"
        days_left = (c.expire_date - now).days if c.expire_date else 0
        expiring_lines.append(
            f"合同号: {c.contract_no or '—'}, 客户: {cname}, 金额: {float(c.amount):.2f}, "
            f"到期日: {c.expire_date.strftime('%Y-%m-%d') if c.expire_date else '未知'}, "
            f"剩余{days_left}天, 状态: {c.status}"
        )
        customer_ids.append(c.customer_id)

    # --- Renewal history for those customers ---
    renewal_lines: list[str] = []
    if customer_ids:
        unique_ids = list(set(customer_ids))
        hist_result = await db.execute(
            select(Contract, Customer.name)
            .join(Customer, Contract.customer_id == Customer.id)
            .where(
                Contract.customer_id.in_(unique_ids),
                Contract.deleted_at.is_(None),
                Contract.status.in_(["expired", "completed"]),
            )
            .order_by(Contract.expire_date.desc())
        )
        for hc, hname in hist_result.all():
            ed = hc.expire_date.strftime("%Y-%m-%d") if hc.expire_date else "未知"
            renewal_lines.append(
                f"客户: {hname}, 历史合同: {hc.contract_no or '—'}, "
                f"金额: {float(hc.amount):.2f}, 到期日: {ed}"
            )

    contract_data = {
        "expiring_contracts": "\n".join(expiring_lines)
        if expiring_lines
        else "无即将到期合同",
        "renewal_history": "\n".join(renewal_lines) if renewal_lines else "无续约历史",
    }

    try:
        return await ai_client.chat_structured(
            [
                {"role": "system", "content": CONTRACT_EXPIRY_SYSTEM},
                {"role": "user", "content": contract_expiry_prompt(contract_data)},
            ],
            EXPIRY_SCHEMA,
        )
    except Exception as e:
        logger.error(f"合同到期扫描失败: {e}")
        return {
            "expiring_soon": [],
            "high_risk_expiries": [],
            "renewal_opportunities": [],
            "total_at_risk_amount": 0,
            "priority_actions": [f"AI分析失败: {e}"],
            "auto_renewal_candidates": [],
        }


async def track_contract_rebate(db: AsyncSession, contract_id: int) -> dict:
    """Query Contract, customer annual/quarterly purchase totals from sales_orders,
    purchase trend, then call AI with contract_rebate_prompt."""
    now = datetime.now(timezone.utc)
    q_start = now - timedelta(days=90)
    a_start = now - timedelta(days=365)

    result = await db.execute(
        select(Contract, Customer.name)
        .join(Customer, Contract.customer_id == Customer.id)
        .where(Contract.id == contract_id, Contract.deleted_at.is_(None))
    )
    row = result.first()
    if not row:
        return {"error": f"合同 #{contract_id} 不存在"}

    contract, cname = row
    cid = contract.customer_id

    # --- Annual purchase total ---
    annual_val = await db.execute(
        select(func.sum(SalesOrder.total_amount)).where(
            SalesOrder.customer_id == cid,
            SalesOrder.created_at >= a_start,
            SalesOrder.deleted_at.is_(None),
        )
    )
    annual_purchase = float(annual_val.scalar() or 0)

    # --- Quarterly purchase total ---
    quarterly_val = await db.execute(
        select(func.sum(SalesOrder.total_amount)).where(
            SalesOrder.customer_id == cid,
            SalesOrder.created_at >= q_start,
            SalesOrder.deleted_at.is_(None),
        )
    )
    quarterly_purchase = float(quarterly_val.scalar() or 0)

    # --- Purchase trend: compare recent 3 months vs previous 3 months ---
    recent_3m_ago = now - timedelta(days=90)
    prev_3m_ago = now - timedelta(days=180)

    recent_val = await db.execute(
        select(func.sum(SalesOrder.total_amount)).where(
            SalesOrder.customer_id == cid,
            SalesOrder.created_at >= recent_3m_ago,
            SalesOrder.deleted_at.is_(None),
        )
    )
    prev_val = await db.execute(
        select(func.sum(SalesOrder.total_amount)).where(
            SalesOrder.customer_id == cid,
            SalesOrder.created_at >= prev_3m_ago,
            SalesOrder.created_at < recent_3m_ago,
            SalesOrder.deleted_at.is_(None),
        )
    )

    recent_total = float(recent_val.scalar() or 0)
    prev_total = float(prev_val.scalar() or 0)

    if prev_total > 0:
        pct = round((recent_total - prev_total) / prev_total * 100, 1)
        purchase_trend = (
            f"近3月采购{recent_total:.2f}元 vs 前3月{prev_total:.2f}元, 变化{pct}%"
        )
    elif recent_total > 0:
        purchase_trend = f"近3月新采购{recent_total:.2f}元 (前期无采购)"
    else:
        purchase_trend = "近6月无采购记录"

    # Reconcile: annual_purchase should include both quarters + more
    if annual_purchase < (recent_total + prev_total):
        annual_purchase = recent_total + prev_total

    # Extract rebate terms from contract notes
    rebate_terms_text = contract.notes or "无明确返利条款"

    contract_data = {
        "title": contract.title,
        "customer_name": cname,
        "amount": float(contract.amount),
        "annual_purchase": round(annual_purchase, 2),
        "quarterly_purchase": round(quarterly_purchase, 2),
        "purchase_trend": purchase_trend,
        "rebate_terms": rebate_terms_text,
    }

    try:
        return await ai_client.chat_structured(
            [
                {"role": "system", "content": CONTRACT_REBATE_SYSTEM},
                {"role": "user", "content": contract_rebate_prompt(contract_data)},
            ],
            REBATE_SCHEMA,
        )
    except Exception as e:
        logger.error(f"合同返利跟踪失败 #{contract_id}: {e}")
        return {
            "rebate_achieved": 0,
            "rebate_projected": 0,
            "rebate_tier_progress": f"AI分析失败: {e}",
            "gap_to_next_tier": 0,
            "optimization_suggestions": [],
            "upsell_opportunities": [],
            "margin_impact": "",
        }
