"""Customer 360 orchestrator — aggregates all-domain data for a single customer."""

import datetime
import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.finance import Contract, Invoice
from app.models.sales import Opportunity, SalesOrder
from app.models.transaction import Sample, Ticket, Visit
from app.services.ai.client import ai_client
from app.services.ai.prompts import orchestrate_customer_prompt
from app.services.orchestration.helpers import _safe_json

logger = logging.getLogger(__name__)


async def orchestrate_customer_360(db: AsyncSession, customer_id: int) -> dict:
    """Aggregate all-domain data for a single customer, then invoke AI for cross-domain insights."""

    now = datetime.datetime.now(datetime.timezone.utc)
    three_months_ago = now - datetime.timedelta(days=90)

    # --- 1. Transaction Health: recent sales orders + revenue trend ---
    recent_orders_result = await db.execute(
        select(SalesOrder)
        .where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
            SalesOrder.created_at >= three_months_ago,
        )
        .order_by(SalesOrder.created_at.desc())
        .limit(20)
    )
    recent_orders = recent_orders_result.scalars().all()

    total_orders_result = await db.execute(
        select(
            func.count(SalesOrder.id),
            func.coalesce(func.sum(SalesOrder.total_amount), 0),
        ).where(
            SalesOrder.customer_id == customer_id,
            SalesOrder.deleted_at.is_(None),
        )
    )
    total_orders_row = total_orders_result.one()

    recent_revenue = sum(float(o.total_amount) for o in recent_orders)
    transaction_health = json.dumps(
        {
            "recent_order_count": len(recent_orders),
            "recent_total_revenue": round(recent_revenue, 2),
            "total_order_count": total_orders_row[0],
            "total_revenue": round(float(total_orders_row[1]), 2),
            "recent_orders": [
                {
                    "order_no": o.order_no,
                    "amount": float(o.total_amount),
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in recent_orders[:5]
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 2. Opportunity Pipeline: open opportunities ---
    opps_result = await db.execute(
        select(Opportunity)
        .where(
            Opportunity.customer_id == customer_id,
            Opportunity.deleted_at.is_(None),
            Opportunity.stage.not_in(["won", "lost", "closed"]),
        )
        .order_by(Opportunity.amount.desc())
    )
    open_opps = opps_result.scalars().all()

    opportunity_pipeline = json.dumps(
        {
            "open_count": len(open_opps),
            "total_pipeline_value": round(sum(float(o.amount) for o in open_opps), 2),
            "opportunities": [
                {
                    "name": o.name,
                    "amount": float(o.amount),
                    "stage": o.stage,
                    "probability": o.probability,
                    "expected_close_date": o.expected_close_date.isoformat()
                    if o.expected_close_date
                    else None,
                }
                for o in open_opps
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 3. AR Status: open invoices, total AR, overdue ---
    invoices_result = await db.execute(
        select(Invoice)
        .where(
            Invoice.customer_id == customer_id,
            Invoice.deleted_at.is_(None),
            Invoice.status != "paid",
        )
        .order_by(Invoice.invoice_date.desc().nulls_last())
    )
    open_invoices = invoices_result.scalars().all()

    total_ar = sum(float(inv.amount) for inv in open_invoices)
    overdue_invoices = [
        inv for inv in open_invoices if inv.invoice_date and inv.invoice_date < now
    ]
    overdue_amount = sum(float(inv.amount) for inv in overdue_invoices)

    ar_status = json.dumps(
        {
            "open_invoice_count": len(open_invoices),
            "total_ar": round(total_ar, 2),
            "overdue_invoice_count": len(overdue_invoices),
            "overdue_amount": round(overdue_amount, 2),
            "invoices": [
                {
                    "invoice_no": inv.invoice_no,
                    "amount": float(inv.amount),
                    "invoice_date": inv.invoice_date.isoformat()
                    if inv.invoice_date
                    else None,
                    "status": inv.status,
                }
                for inv in open_invoices[:5]
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 4. Recent Visits: last 3 ---
    visits_result = await db.execute(
        select(Visit)
        .where(
            Visit.customer_id == customer_id,
            Visit.deleted_at.is_(None),
        )
        .order_by(Visit.visit_date.desc().nulls_last())
        .limit(3)
    )
    recent_visits = visits_result.scalars().all()

    recent_visits_str = json.dumps(
        {
            "count": len(recent_visits),
            "visits": [
                {
                    "title": v.title,
                    "type": v.type,
                    "visit_date": v.visit_date.isoformat() if v.visit_date else None,
                    "status": v.status,
                    "purpose": v.purpose,
                    "result": v.result,
                    "next_plan": v.next_plan,
                }
                for v in recent_visits
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 5. Active Tickets: open tickets ---
    tickets_result = await db.execute(
        select(Ticket)
        .where(
            Ticket.customer_id == customer_id,
            Ticket.deleted_at.is_(None),
            Ticket.status == "open",
        )
        .order_by(Ticket.priority.desc())
    )
    active_tickets = tickets_result.scalars().all()

    active_tickets_str = json.dumps(
        {
            "open_count": len(active_tickets),
            "tickets": [
                {
                    "ticket_no": t.ticket_no,
                    "title": t.title,
                    "priority": t.priority,
                    "category": t.category,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in active_tickets
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 6. Contract Status: active contracts ---
    contracts_result = await db.execute(
        select(Contract)
        .where(
            Contract.customer_id == customer_id,
            Contract.deleted_at.is_(None),
            Contract.status.not_in(["cancelled", "expired"]),
        )
        .order_by(Contract.expire_date.desc().nulls_last())
    )
    active_contracts = contracts_result.scalars().all()

    contract_status = json.dumps(
        {
            "active_count": len(active_contracts),
            "contracts": [
                {
                    "contract_no": c.contract_no,
                    "title": c.title,
                    "amount": float(c.amount),
                    "status": c.status,
                    "signed_date": c.signed_date.isoformat() if c.signed_date else None,
                    "expire_date": c.expire_date.isoformat() if c.expire_date else None,
                }
                for c in active_contracts
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- 7. Sample Status: recent sample requests ---
    samples_result = await db.execute(
        select(Sample)
        .where(
            Sample.customer_id == customer_id,
            Sample.deleted_at.is_(None),
        )
        .order_by(Sample.created_at.desc())
        .limit(10)
    )
    recent_samples = samples_result.scalars().all()

    sample_status = json.dumps(
        {
            "recent_count": len(recent_samples),
            "samples": [
                {
                    "product_id": s.product_id,
                    "quantity": s.quantity,
                    "status": s.status,
                    "apply_date": s.apply_date.isoformat() if s.apply_date else None,
                    "ship_date": s.ship_date.isoformat() if s.ship_date else None,
                    "receive_date": s.receive_date.isoformat()
                    if s.receive_date
                    else None,
                }
                for s in recent_samples[:5]
            ],
        },
        ensure_ascii=False,
        default=_safe_json,
    )

    # --- Get customer basic info ---
    cust_result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id, Customer.deleted_at.is_(None)
        )
    )
    customer = cust_result.scalar_one_or_none()
    customer_name = customer.name if customer else f"#{customer_id}"
    customer_level = customer.level if customer else "未知"

    # --- Build AI prompt data ---
    ai_input = {
        "name": customer_name,
        "level": customer_level,
        "transaction_health": transaction_health,
        "opportunity_pipeline": opportunity_pipeline,
        "ar_status": ar_status,
        "recent_visits": recent_visits_str,
        "active_tickets": active_tickets_str,
        "contract_status": contract_status,
        "sample_status": sample_status,
    }

    # --- AI Output Schema ---
    output_schema = {
        "customer_360_score": "integer 0-100",
        "health_summary": "string, 2-3 sentence overview",
        "revenue_health": "string, revenue dimension assessment",
        "relationship_health": "string, relationship dimension assessment",
        "risk_health": "string, risk dimension assessment",
        "cross_domain_insights": [
            {
                "domain": "string",
                "finding": "string",
                "impact": "string",
                "action": "string",
            }
        ],
        "prioritized_actions": [
            {
                "action": "string",
                "domain": "string",
                "priority": "string",
                "expected_impact": "string",
            }
        ],
        "opportunity_score": "integer 0-100",
        "risk_score": "integer 0-100",
        "next_best_action": "string",
    }

    ai_insights = {}
    try:
        ai_insights = await ai_client.chat_structured(
            [
                {
                    "role": "system",
                    "content": "你是一个电子元器件ERP系统智能总控。整合分析客户全维度数据。",
                },
                {"role": "user", "content": orchestrate_customer_prompt(ai_input)},
            ],
            output_schema,
            max_tokens=8192,
        )
    except Exception as e:
        logger.error(
            f"Customer 360 AI orchestration failed for customer {customer_id}: {e}"
        )
        ai_insights = {
            "customer_360_score": 0,
            "health_summary": "AI分析暂时不可用",
            "revenue_health": "未知",
            "relationship_health": "未知",
            "risk_health": "未知",
            "cross_domain_insights": [],
            "prioritized_actions": [],
            "opportunity_score": 0,
            "risk_score": 0,
            "next_best_action": "",
        }

    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "data": {
            "transaction_health": json.loads(transaction_health),
            "opportunity_pipeline": json.loads(opportunity_pipeline),
            "ar_status": json.loads(ar_status),
            "recent_visits": json.loads(recent_visits_str),
            "active_tickets": json.loads(active_tickets_str),
            "contract_status": json.loads(contract_status),
            "sample_status": json.loads(sample_status),
        },
        "insights": ai_insights,
    }
