"""Finance Intelligence Service — AI-powered payment predictions, cash flow forecasting,
dunning strategies, and credit risk assessment."""

import datetime as dt
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Invoice, PaymentRecord
from app.models.sales import SalesOrder
from app.models.transaction import Payment as TransactionPayment, PurchaseOrder
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    cash_flow_forecast_prompt,
    credit_risk_prompt,
    dunning_strategy_prompt,
    payment_prediction_prompt,
)

logger = logging.getLogger(__name__)

FINANCE_INTEL_SYSTEM = """你是一个电子元器件分销行业的财务智能分析专家。你分析应收账款、现金流、催款策略和信用风险。

## 背景知识
- 电子元器件分销行业通常给予客户30-90天账期，大客户可达120天
- 逾期付款是行业常见痛点，需区分暂时性逾期和趋势性恶化
- 客户信用评估需综合考虑交易历史、回款记录、当前经营状况和行业地位
- DSO（应收账款周转天数）是核心财务健康指标

## 输出要求
- 使用中文
- 数据驱动，引用具体数字
- 给出可操作的建议
- 保持专业但务实的语调
"""


async def _get_customer_payment_stats(db: AsyncSession, customer_id: int) -> dict:
    """Fetch payment statistics for a single customer."""
    now = dt.datetime.now(dt.timezone.utc)
    twelve_months_ago = now - dt.timedelta(days=365)

    # Late count in last 12 months
    late_count = (
        await db.execute(
            select(func.count(PaymentRecord.id)).where(
                PaymentRecord.customer_id == customer_id,
                PaymentRecord.status == "overdue",
                PaymentRecord.created_at >= twelve_months_ago,
            )
        )
    ).scalar() or 0

    # Average payment days (payment_date - order created_at)
    pay_rows = (
        await db.execute(
            select(PaymentRecord.payment_date, SalesOrder.created_at)
            .join(SalesOrder, PaymentRecord.sales_order_id == SalesOrder.id)
            .where(
                PaymentRecord.customer_id == customer_id,
                PaymentRecord.payment_date.is_not(None),
            )
        )
    ).all()
    diffs = [(p - s).days for p, s in pay_rows if p and s]
    avg_days = round(sum(diffs) / len(diffs), 1) if diffs else None

    # Max overdue amount (largest overdue invoice or payment record)
    max_overdue_record = (
        await db.execute(
            select(func.max(Invoice.amount)).where(
                Invoice.customer_id == customer_id, Invoice.status == "overdue"
            )
        )
    ).scalar()
    max_overdue = float(max_overdue_record) if max_overdue_record else 0.0

    # Current AR (open invoices)
    current_ar = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                    Invoice.customer_id == customer_id,
                    Invoice.status.not_in(["paid", "draft", "cancelled"]),
                )
            )
        ).scalar()
        or 0
    )

    # Current overdue
    current_overdue = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                    Invoice.customer_id == customer_id, Invoice.status == "overdue"
                )
            )
        ).scalar()
        or 0
    )

    return {
        "late_count": late_count,
        "avg_payment_days": avg_days,
        "max_overdue": max_overdue,
        "current_ar": current_ar,
        "current_overdue": current_overdue,
    }


# ---------------------------------------------------------------------------
# 1. predict_payment_delays
# ---------------------------------------------------------------------------


async def predict_payment_delays(db: AsyncSession) -> dict:
    """Query all open invoices with customer info and payment history, then
    call AI to predict which invoices are at risk of late payment."""

    result = await db.execute(
        select(Invoice, Customer)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.status.not_in(["paid", "draft", "cancelled"]))
        .order_by(Invoice.customer_id)
    )
    rows = result.all()

    if not rows:
        return {
            "overall_risk": "低",
            "risk_score": 0,
            "late_invoice_predictions": [],
            "dso_forecast": 0,
            "cash_flow_impact": "无未结发票",
            "recommendations": [],
            "context": {"total_ar": 0, "total_overdue": 0, "open_invoice_count": 0},
        }

    customer_ids = list({inv.customer_id for inv, _ in rows})

    # Collect per-customer stats
    late_counts: dict[int, int] = {}
    avg_days_map: dict[int, float | None] = {}
    total_ar_map: dict[int, float] = {}

    for cid in customer_ids:
        stats = await _get_customer_payment_stats(db, cid)
        late_counts[cid] = stats["late_count"]
        avg_days_map[cid] = stats["avg_payment_days"]
        total_ar_map[cid] = stats["current_ar"]

    open_invoices_list: list[dict] = []
    total_ar = 0.0
    total_overdue = 0.0

    for inv, cust in rows:
        amount = float(inv.amount)
        total_ar += amount
        if inv.status == "overdue":
            total_overdue += amount
        open_invoices_list.append(
            {
                "invoice_no": inv.invoice_no or f"INV-{inv.id}",
                "customer_name": cust.name,
                "amount": amount,
                "due_date": inv.invoice_date.isoformat()
                if inv.invoice_date
                else "未知",
                "status": inv.status,
                "customer_level": cust.level or "未知",
                "credit_level": cust.credit_level or "未知",
                "late_count_12m": late_counts.get(inv.customer_id, 0),
                "avg_payment_days": avg_days_map.get(inv.customer_id),
            }
        )

    # Aggregate context for the AI prompt
    active_days = [d for d in avg_days_map.values() if d is not None]
    avg_days_str = (
        f"{round(sum(active_days) / len(active_days), 1)}天（平均）"
        if active_days
        else "无数据"
    )

    context = {
        "customer_name": "多客户汇总",
        "avg_payment_days": avg_days_str,
        "late_count_12m": sum(late_counts.values()),
        "total_ar": total_ar,
        "overdue_amount": total_overdue,
        "customer_level": "汇总",
        "credit_rating": "汇总",
        "recent_order_freq": f"{len(customer_ids)}个客户有未结发票",
        "open_invoices": json.dumps(
            open_invoices_list, ensure_ascii=False, default=str
        ),
    }

    output_schema = {
        "overall_risk": "string: 低/中/高",
        "risk_score": "integer 0-100",
        "late_invoice_predictions": "list of dicts: {{invoice_no, amount, due_date, predicted_delay_days, probability, reason}}",
        "dso_forecast": "integer: 预计DSO天数",
        "cash_flow_impact": "string",
        "recommendations": "list of strings (2-3条)",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": FINANCE_INTEL_SYSTEM},
                {"role": "user", "content": payment_prediction_prompt(context)},
            ],
            output_schema,
        )
        ai_result["context"] = {
            "total_ar": total_ar,
            "total_overdue": total_overdue,
            "open_invoice_count": len(open_invoices_list),
        }
        return ai_result
    except Exception as e:
        logger.error(f"Payment delay prediction failed: {e}")
        return {
            "overall_risk": "中",
            "risk_score": 50,
            "late_invoice_predictions": [],
            "dso_forecast": 0,
            "cash_flow_impact": f"AI分析暂时不可用: {e}",
            "recommendations": [],
            "context": {
                "total_ar": total_ar,
                "total_overdue": total_overdue,
                "open_invoice_count": len(open_invoices_list),
                "error": str(e),
            },
        }


# ---------------------------------------------------------------------------
# 2. forecast_cash_flow
# ---------------------------------------------------------------------------


async def forecast_cash_flow(db: AsyncSession) -> dict:
    """Query payment_records (collected MTD), transaction payments (paid MTD),
    open invoices (expected receivables), and open POs (expected payables),
    then call AI to forecast cash flow."""

    now = dt.datetime.now(dt.timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Collected MTD (customer payments received this month)
    collected_mtd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                    PaymentRecord.payment_date >= start_of_month
                )
            )
        ).scalar()
        or 0
    )

    # Paid MTD (supplier payments made this month)
    paid_mtd = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(TransactionPayment.amount), 0)).where(
                    TransactionPayment.paid_at >= start_of_month,
                    TransactionPayment.type == "payment",
                )
            )
        ).scalar()
        or 0
    )

    # Expected receivables (open invoices)
    invoices_result = await db.execute(
        select(Invoice).where(Invoice.status.not_in(["paid", "draft", "cancelled"]))
    )
    open_invoices_list = invoices_result.scalars().all()
    total_ar = sum(float(inv.amount) for inv in open_invoices_list)
    expected_receivables = [
        {
            "invoice_no": inv.invoice_no or f"INV-{inv.id}",
            "amount": float(inv.amount),
            "due_date": inv.invoice_date.isoformat() if inv.invoice_date else "未知",
            "status": inv.status,
        }
        for inv in open_invoices_list
    ]

    # Expected payables (open purchase orders)
    po_result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.status.not_in(["completed", "cancelled", "draft"])
        )
    )
    open_pos = po_result.scalars().all()
    total_ap = sum(float(po.total_amount) for po in open_pos)
    expected_payables = [
        {
            "order_no": po.order_no or f"PO-{po.id}",
            "amount": float(po.total_amount),
            "expected_date": po.expected_date.isoformat()
            if po.expected_date
            else "未知",
            "status": po.status,
        }
        for po in open_pos
    ]

    context = {
        "cash_balance": 0,  # Not stored in DB; set to 0, AI will work with flows
        "total_ar": total_ar,
        "total_ap": total_ap,
        "collected_mtd": collected_mtd,
        "paid_mtd": paid_mtd,
        "expected_receivables": json.dumps(
            expected_receivables, ensure_ascii=False, default=str
        ),
        "expected_payables": json.dumps(
            expected_payables, ensure_ascii=False, default=str
        ),
    }

    output_schema = {
        "cash_flow_health": "string: 差/一般/良好/优秀",
        "health_score": "integer 0-100",
        "forecast_7d": "number: 7天预测净现金流",
        "forecast_30d": "number: 30天预测净现金流",
        "forecast_90d": "number: 90天预测净现金流",
        "shortage_risk": "string: 低/中/高",
        "shortage_timing": "string: 预计短缺时间点",
        "recommendations": "list of strings (3条)",
        "alerts": "list of strings",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": FINANCE_INTEL_SYSTEM},
                {"role": "user", "content": cash_flow_forecast_prompt(context)},
            ],
            output_schema,
        )
        ai_result["context"] = {
            "collected_mtd": collected_mtd,
            "paid_mtd": paid_mtd,
            "total_ar": total_ar,
            "total_ap": total_ap,
            "open_invoice_count": len(open_invoices_list),
            "open_po_count": len(open_pos),
        }
        return ai_result
    except Exception as e:
        logger.error(f"Cash flow forecast failed: {e}")
        return {
            "cash_flow_health": "一般",
            "health_score": 50,
            "forecast_7d": 0,
            "forecast_30d": 0,
            "forecast_90d": 0,
            "shortage_risk": "中",
            "shortage_timing": "无法判断",
            "recommendations": [],
            "alerts": [f"AI分析暂时不可用: {e}"],
            "context": {
                "collected_mtd": collected_mtd,
                "paid_mtd": paid_mtd,
                "total_ar": total_ar,
                "total_ap": total_ap,
                "error": str(e),
            },
        }


# ---------------------------------------------------------------------------
# 3. generate_dunning_strategy
# ---------------------------------------------------------------------------


async def generate_dunning_strategy(db: AsyncSession, invoice_id: int) -> dict:
    """Query a single invoice with customer info, payment history, and pending
    orders, then call AI to generate a tailored dunning (催款) strategy."""

    result = await db.execute(
        select(Invoice, Customer)
        .join(Customer, Invoice.customer_id == Customer.id)
        .where(Invoice.id == invoice_id)
    )
    row = result.first()

    if not row:
        return {
            "dunning_level": "标准",
            "suggested_contact": "电话",
            "suggested_timing": "尽快联系",
            "message_template": "",
            "escalation_timeline": "",
            "negotiation_strategy": "",
            "risk_of_default": "发票不存在",
            "context": {"invoice_id": invoice_id, "error": "Invoice not found"},
        }

    inv, cust = row
    stats = await _get_customer_payment_stats(db, cust.id)

    # Pending orders for this customer
    pending_result = await db.execute(
        select(SalesOrder).where(
            SalesOrder.customer_id == cust.id,
            SalesOrder.status.not_in(["completed", "cancelled", "delivered"]),
        )
    )
    pending_orders = pending_result.scalars().all()

    # Payment history summary
    history_result = await db.execute(
        select(PaymentRecord)
        .where(PaymentRecord.customer_id == cust.id)
        .order_by(PaymentRecord.created_at.desc())
        .limit(10)
    )
    recent_payments = history_result.scalars().all()
    dunning_history = [
        {
            "amount": float(p.amount),
            "payment_date": p.payment_date.isoformat() if p.payment_date else "未知",
            "status": p.status,
            "method": p.payment_method,
        }
        for p in recent_payments
    ]

    # Calculate overdue days
    overdue_days = 0
    if inv.invoice_date:
        delta = dt.datetime.now(dt.timezone.utc) - inv.invoice_date
        if inv.invoice_date.tzinfo is None:
            delta = dt.datetime.now(dt.timezone.utc) - inv.invoice_date.replace(
                tzinfo=dt.timezone.utc
            )
        # Assume net-30 terms
        overdue_days = max(0, delta.days - 30)

    # Customer relationship years
    relationship_years = 0
    if cust.created_at:
        created = cust.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        relationship_years = round(
            (dt.datetime.now(dt.timezone.utc) - created).days / 365.25, 1
        )

    context = {
        "customer_name": cust.name,
        "invoice_no": inv.invoice_no or f"INV-{inv.id}",
        "amount": float(inv.amount),
        "due_date": inv.invoice_date.isoformat() if inv.invoice_date else "未知",
        "overdue_days": overdue_days,
        "customer_level": cust.level or "未知",
        "dunning_history": json.dumps(dunning_history, ensure_ascii=False, default=str),
        "pending_orders": (
            json.dumps(
                [
                    {
                        "order_no": so.order_no or f"SO-{so.id}",
                        "amount": float(so.total_amount),
                        "status": so.status,
                    }
                    for so in pending_orders
                ],
                ensure_ascii=False,
                default=str,
            )
            if pending_orders
            else "无在途订单"
        ),
        "relationship_years": relationship_years,
    }

    output_schema = {
        "dunning_level": "string: 温和/标准/加强/法律",
        "suggested_contact": "string: 建议联系方式",
        "suggested_timing": "string: 最佳联系时间",
        "message_template": "string: 催款话术模板",
        "escalation_timeline": "string: 升级时间线",
        "negotiation_strategy": "string: 谈判策略",
        "risk_of_default": "string: 坏账风险评估",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": FINANCE_INTEL_SYSTEM},
                {"role": "user", "content": dunning_strategy_prompt(context)},
            ],
            output_schema,
        )
        ai_result["context"] = {
            "invoice_id": invoice_id,
            "customer_id": cust.id,
            "customer_name": cust.name,
            "amount": float(inv.amount),
            "overdue_days": overdue_days,
            "avg_payment_days": stats["avg_payment_days"],
            "late_count": stats["late_count"],
        }
        return ai_result
    except Exception as e:
        logger.error(f"Dunning strategy generation failed: {e}")
        return {
            "dunning_level": "标准",
            "suggested_contact": "电话",
            "suggested_timing": "尽快联系",
            "message_template": "",
            "escalation_timeline": "",
            "negotiation_strategy": "",
            "risk_of_default": f"AI分析暂时不可用: {e}",
            "context": {
                "invoice_id": invoice_id,
                "customer_id": cust.id,
                "customer_name": cust.name,
                "amount": float(inv.amount),
                "overdue_days": overdue_days,
                "error": str(e),
            },
        }


# ---------------------------------------------------------------------------
# 4. assess_credit_risk
# ---------------------------------------------------------------------------


async def assess_credit_risk(db: AsyncSession, customer_id: int) -> dict:
    """Query customer revenue history, payment history (avg days, late count,
    max overdue), and current AR, then call AI to assess credit risk."""

    # Customer record
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = cust_result.scalar_one_or_none()

    if not customer:
        return {
            "credit_rating": "C",
            "credit_score": 0,
            "recommended_credit_limit": 0,
            "payment_terms_recommendation": "现款现货",
            "risk_factors": ["客户不存在"],
            "positive_signals": [],
            "watch_list": False,
            "action_recommendation": "核实客户信息",
            "context": {"customer_id": customer_id, "error": "Customer not found"},
        }

    stats = await _get_customer_payment_stats(db, customer_id)

    # Total revenue from all sales orders
    total_revenue = float(
        (
            await db.execute(
                select(func.coalesce(func.sum(SalesOrder.total_amount), 0)).where(
                    SalesOrder.customer_id == customer_id
                )
            )
        ).scalar()
        or 0
    )

    # Relationship years
    relationship_years = 0
    if customer.created_at:
        created = customer.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=dt.timezone.utc)
        relationship_years = round(
            (dt.datetime.now(dt.timezone.utc) - created).days / 365.25, 1
        )

    credit_limit = float(customer.credit_limit or 0)

    context = {
        "customer_name": customer.name,
        "relationship_years": relationship_years,
        "total_revenue": total_revenue,
        "avg_payment_days": (
            f"{stats['avg_payment_days']}天"
            if stats["avg_payment_days"] is not None
            else "无数据"
        ),
        "late_count_12m": stats["late_count"],
        "max_overdue": stats["max_overdue"],
        "current_ar": stats["current_ar"],
        "current_overdue": stats["current_overdue"],
        "credit_limit": f"{credit_limit:,.2f}" if credit_limit > 0 else "未设置",
        "credit_used": stats["current_ar"],
    }

    output_schema = {
        "credit_rating": "string: AAA/AA/A/B/C/D",
        "credit_score": "integer 0-100",
        "recommended_credit_limit": "number: 建议信用额度",
        "payment_terms_recommendation": "string: 建议付款条件",
        "risk_factors": "list of strings",
        "positive_signals": "list of strings",
        "watch_list": "boolean: 是否建议列入关注名单",
        "action_recommendation": "string: 行动建议",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": FINANCE_INTEL_SYSTEM},
                {"role": "user", "content": credit_risk_prompt(context)},
            ],
            output_schema,
        )
        ai_result["context"] = {
            "customer_id": customer_id,
            "customer_name": customer.name,
            "total_revenue": total_revenue,
            "avg_payment_days": stats["avg_payment_days"],
            "late_count_12m": stats["late_count"],
            "max_overdue": stats["max_overdue"],
            "current_ar": stats["current_ar"],
            "current_overdue": stats["current_overdue"],
            "credit_limit": credit_limit,
            "relationship_years": relationship_years,
        }
        return ai_result
    except Exception as e:
        logger.error(f"Credit risk assessment failed: {e}")
        return {
            "credit_rating": "C",
            "credit_score": 0,
            "recommended_credit_limit": credit_limit,
            "payment_terms_recommendation": "标准账期",
            "risk_factors": [f"AI分析暂时不可用: {e}"],
            "positive_signals": [],
            "watch_list": False,
            "action_recommendation": "请人工评估",
            "context": {
                "customer_id": customer_id,
                "customer_name": customer.name,
                "total_revenue": total_revenue,
                "avg_payment_days": stats["avg_payment_days"],
                "late_count_12m": stats["late_count"],
                "max_overdue": stats["max_overdue"],
                "current_ar": stats["current_ar"],
                "error": str(e),
            },
        }
