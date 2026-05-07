"""Ticket Intelligence Service — AI-powered ticket classification, response, prediction, and clustering."""

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Ticket
from app.models.customer import Customer
from app.models.product import Product
from app.services.ai.client import ai_client
from app.services.ai.prompts import (
    ticket_classify_prompt,
    ticket_response_prompt,
    ticket_resolution_prediction_prompt,
    ticket_cluster_prompt,
)

logger = logging.getLogger(__name__)


async def classify_ticket(db: AsyncSession, ticket_id: int) -> dict:
    """Classify a ticket with AI: category, priority, severity, routing suggestion."""
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.deleted_at.is_(None))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found"}

    customer_name = None
    customer_level = None
    ticket_history = 0

    if ticket.customer_id:
        cust_result = await db.execute(
            select(Customer.name, Customer.level).where(
                Customer.id == ticket.customer_id, Customer.deleted_at.is_(None)
            )
        )
        cust_row = cust_result.first()
        if cust_row:
            customer_name = cust_row[0]
            customer_level = cust_row[1]

        history_result = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.customer_id == ticket.customer_id,
                Ticket.deleted_at.is_(None),
            )
        )
        ticket_history = history_result.scalar() or 0

    ticket_data = {
        "title": ticket.title,
        "description": ticket.description or "",
        "customer_name": customer_name or "未知",
        "category": ticket.category or "未分类",
        "priority": ticket.priority or "medium",
        "customer_level": customer_level or "未知",
        "ticket_history": ticket_history,
    }

    schema = {
        "category": "string: 技术咨询/质量问题/交付问题/商务问题/样品申请/其他",
        "subcategory": "list of strings",
        "priority": "string: urgent/high/medium/low",
        "priority_reason": "string",
        "assigned_to": "string",
        "estimated_resolution_hours": "integer",
        "severity": "integer 0-100",
        "escalation_needed": "boolean",
        "auto_response_suggestion": "string",
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件技术支持专家。"},
                {"role": "user", "content": ticket_classify_prompt(ticket_data)},
            ],
            schema,
        )
        result["ticket_id"] = ticket_id
        return result
    except Exception as e:
        logger.error(f"Ticket classify failed for ticket {ticket_id}: {e}")
        return {
            "ticket_id": ticket_id,
            "category": ticket.category or "未分类",
            "subcategory": [],
            "priority": ticket.priority or "medium",
            "priority_reason": "AI分析失败",
            "assigned_to": "",
            "estimated_resolution_hours": 0,
            "severity": 0,
            "escalation_needed": False,
            "auto_response_suggestion": f"AI分析暂时不可用: {e}",
        }


async def suggest_ticket_response(db: AsyncSession, ticket_id: int) -> dict:
    """Generate AI-suggested response for a ticket, with product and similar-ticket context."""
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.deleted_at.is_(None))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found"}

    # Attempt to match product names mentioned in the description
    product_info = "无数据"
    if ticket.description:
        # Extract potential product name fragments by splitting on common delimiters
        import re
        words = re.split(r'[,，。；;、\s\n]+', ticket.description)
        # Filter out short words and build LIKE patterns
        meaningful = [w.strip() for w in words if len(w.strip()) >= 3]
        if meaningful:
            # Try matching against product names
            conditions = [Product.name.ilike(f"%{w}%") for w in meaningful[:20]]
            if conditions:
                from sqlalchemy import or_
                prod_result = await db.execute(
                    select(Product.name, Product.sku, Product.category, Product.specs)
                    .where(or_(*conditions))
                    .limit(10)
                )
                prod_rows = prod_result.all()
                if prod_rows:
                    lines = []
                    for pr in prod_rows:
                        lines.append(f"- {pr[0]} (SKU: {pr[1] or 'N/A'}, 分类: {pr[2] or 'N/A'}, 规格: {pr[3] or 'N/A'})")
                    product_info = "\n".join(lines)

    # Find similar resolved tickets (same category, has resolution)
    similar_solutions = "无相似工单"
    if ticket.category:
        sim_result = await db.execute(
            select(Ticket.title, Ticket.resolution, Ticket.resolved_at)
            .where(
                Ticket.category == ticket.category,
                Ticket.resolution.isnot(None),
                Ticket.resolution != "",
                Ticket.id != ticket_id,
                Ticket.deleted_at.is_(None),
            )
            .order_by(Ticket.resolved_at.desc().nullslast())
            .limit(5)
        )
        sim_rows = sim_result.all()
        if sim_rows:
            lines = []
            for sr in sim_rows:
                lines.append(f"- [{sr[0]}] 解决方案: {sr[2]}")
            similar_solutions = "\n".join(lines)

    ticket_data = {
        "title": ticket.title,
        "description": ticket.description or "",
        "category": ticket.category or "未分类",
        "product_info": product_info,
        "similar_solutions": similar_solutions,
        "kb_matches": "无匹配",
    }

    schema = {
        "diagnosis": "string",
        "root_cause": "string",
        "solution_steps": "list of strings",
        "reply_template": "string",
        "followup_questions": "list of strings",
        "internal_notes": "string",
        "faq_candidate": "boolean",
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个电子元器件技术支持工程师。"},
                {"role": "user", "content": ticket_response_prompt(ticket_data)},
            ],
            schema,
        )
        result["ticket_id"] = ticket_id
        return result
    except Exception as e:
        logger.error(f"Ticket response suggestion failed for ticket {ticket_id}: {e}")
        return {
            "ticket_id": ticket_id,
            "diagnosis": "AI分析失败",
            "root_cause": "",
            "solution_steps": [],
            "reply_template": "",
            "followup_questions": [],
            "internal_notes": f"AI分析暂时不可用: {e}",
            "faq_candidate": False,
        }


async def predict_ticket_resolution(db: AsyncSession, ticket_id: int) -> dict:
    """Predict ticket resolution time, stall risk, and escalation probability."""
    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id, Ticket.deleted_at.is_(None))
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        return {"error": f"Ticket {ticket_id} not found"}

    # Calculate elapsed hours since created_at
    now = datetime.now(timezone.utc)
    elapsed_hours = 0
    if ticket.created_at:
        created = ticket.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        elapsed_hours = round((now - created).total_seconds() / 3600, 1)

    # Average resolution time for same category (resolved tickets only)
    avg_resolution_hours = "无数据"
    if ticket.category:
        avg_result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
                )
            ).where(
                Ticket.category == ticket.category,
                Ticket.resolved_at.isnot(None),
                Ticket.created_at.isnot(None),
                Ticket.deleted_at.is_(None),
            )
        )
        avg_val = avg_result.scalar()
        if avg_val is not None:
            avg_resolution_hours = str(round(float(avg_val), 1))

    ticket_data = {
        "title": ticket.title,
        "category": ticket.category or "未分类",
        "priority": ticket.priority or "medium",
        "status": ticket.status or "open",
        "elapsed_hours": elapsed_hours,
        "avg_resolution_hours": avg_resolution_hours,
        "first_contact_resolution_rate": "无数据",
    }

    schema = {
        "predicted_resolution_hours": "number",
        "confidence": "integer 0-100",
        "resolution_barriers": "list of strings",
        "stall_risk": "string: 低/中/高",
        "escalation_probability": "integer 0-100",
        "customer_satisfaction_prediction": "string: 高/中/低",
        "acceleration_suggestions": "list of strings",
    }

    try:
        result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个IT服务管理专家。"},
                {"role": "user", "content": ticket_resolution_prediction_prompt(ticket_data)},
            ],
            schema,
        )
        result["ticket_id"] = ticket_id
        return result
    except Exception as e:
        logger.error(f"Ticket resolution prediction failed for ticket {ticket_id}: {e}")
        return {
            "ticket_id": ticket_id,
            "predicted_resolution_hours": 0,
            "confidence": 0,
            "resolution_barriers": [],
            "stall_risk": "低",
            "escalation_probability": 0,
            "customer_satisfaction_prediction": "中",
            "acceleration_suggestions": [f"AI分析暂时不可用: {e}"],
        }


async def cluster_tickets(db: AsyncSession) -> dict:
    """Cluster all tickets from the last 30 days: patterns, hotspots, systemic issues."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Total count
    total_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.created_at >= thirty_days_ago,
            Ticket.deleted_at.is_(None),
        )
    )
    total_tickets = total_result.scalar() or 0

    if total_tickets == 0:
        return {
            "total_tickets": 0,
            "category_distribution": {},
            "priority_distribution": {},
            "avg_resolution_hours": 0,
            "avg_satisfaction": "无数据",
            "hotspot_customers": [],
            "hotspot_products": [],
            "clusters": [],
            "systemic_issues": ["近30天无工单"],
            "product_quality_alerts": [],
            "process_gaps": [],
            "improvement_plan": [],
            "prevention_suggestions": [],
        }

    # Category distribution
    cat_result = await db.execute(
        select(Ticket.category, func.count(Ticket.id))
        .where(Ticket.created_at >= thirty_days_ago, Ticket.deleted_at.is_(None))
        .group_by(Ticket.category)
    )
    category_distribution = {row[0] or "未分类": row[1] for row in cat_result.all()}

    # Priority distribution
    pri_result = await db.execute(
        select(Ticket.priority, func.count(Ticket.id))
        .where(Ticket.created_at >= thirty_days_ago, Ticket.deleted_at.is_(None))
        .group_by(Ticket.priority)
    )
    priority_distribution = {row[0] or "unknown": row[1] for row in pri_result.all()}

    # Average resolution time
    avg_res_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Ticket.resolved_at - Ticket.created_at) / 3600
            )
        ).where(
            Ticket.created_at >= thirty_days_ago,
            Ticket.resolved_at.isnot(None),
            Ticket.created_at.isnot(None),
            Ticket.deleted_at.is_(None),
        )
    )
    avg_res_val = avg_res_result.scalar()
    avg_resolution_hours = str(round(float(avg_res_val), 1)) if avg_res_val is not None else "无数据"

    # Hotspot customers (top 5 by ticket count)
    hot_cust_result = await db.execute(
        select(
            Ticket.customer_id,
            Customer.name,
            func.count(Ticket.id).label("cnt"),
        )
        .join(Customer, Ticket.customer_id == Customer.id, isouter=True)
        .where(Ticket.created_at >= thirty_days_ago, Ticket.deleted_at.is_(None))
        .group_by(Ticket.customer_id, Customer.name)
        .order_by(func.count(Ticket.id).desc())
        .limit(5)
    )
    hotspot_customers = [
        {"customer_id": row[0], "customer_name": row[1] or "未知", "ticket_count": row[2]}
        for row in hot_cust_result.all()
    ]

    # Hotspot products — extract product names from ticket descriptions and count mentions
    # We query all product names and do in-memory matching for simplicity
    all_products_result = await db.execute(select(Product.id, Product.name))
    all_products = all_products_result.all()

    tickets_descriptions = await db.execute(
        select(Ticket.title, Ticket.description).where(
            Ticket.created_at >= thirty_days_ago,
            Ticket.deleted_at.is_(None),
        )
    )
    ticket_texts = [(t[0] or "", t[1] or "") for t in tickets_descriptions.all()]

    product_mention_count: dict[int, dict] = {}
    for title, desc in ticket_texts:
        combined = title + " " + desc
        for pid, pname in all_products:
            if pname and pname in combined:
                if pid not in product_mention_count:
                    product_mention_count[pid] = {"product_id": pid, "product_name": pname, "ticket_count": 0}
                product_mention_count[pid]["ticket_count"] += 1

    hotspot_products = sorted(
        product_mention_count.values(), key=lambda x: -x["ticket_count"]
    )[:5]

    # Build prompt data
    ticket_data = {
        "total_tickets": total_tickets,
        "category_distribution": str(category_distribution),
        "priority_distribution": str(priority_distribution),
        "avg_resolution_hours": avg_resolution_hours,
        "avg_satisfaction": "无数据",
        "hotspot_customers": (
            "\n".join(
                f"- {hc['customer_name']}: {hc['ticket_count']}个工单"
                for hc in hotspot_customers
            )
            if hotspot_customers
            else "无数据"
        ),
        "hotspot_products": (
            "\n".join(
                f"- {hp['product_name']}: {hp['ticket_count']}次提及"
                for hp in hotspot_products
            )
            if hotspot_products
            else "无数据"
        ),
    }

    schema = {
        "clusters": "list of dicts: {cluster_name, ticket_count, root_cause, severity, trend}",
        "systemic_issues": "list of strings",
        "product_quality_alerts": "list of strings",
        "process_gaps": "list of strings",
        "improvement_plan": "list of strings",
        "prevention_suggestions": "list of strings",
    }

    try:
        ai_result = await ai_client.chat_structured(
            [
                {"role": "system", "content": "你是一个服务质量分析专家。"},
                {"role": "user", "content": ticket_cluster_prompt(ticket_data)},
            ],
            schema,
        )
    except Exception as e:
        logger.error(f"Ticket clustering failed: {e}")
        ai_result = {
            "clusters": [],
            "systemic_issues": [f"AI分析暂时不可用: {e}"],
            "product_quality_alerts": [],
            "process_gaps": [],
            "improvement_plan": [],
            "prevention_suggestions": [],
        }

    return {
        "total_tickets": total_tickets,
        "category_distribution": category_distribution,
        "priority_distribution": priority_distribution,
        "avg_resolution_hours": avg_resolution_hours,
        "avg_satisfaction": "无数据",
        "hotspot_customers": hotspot_customers,
        "hotspot_products": hotspot_products,
        **ai_result,
    }
