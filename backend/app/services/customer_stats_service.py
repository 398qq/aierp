"""Customer statistics service.

Stage 1 refactor: extracts the 9 business endpoints previously inlined in
``api/v1/customers/stats.py`` into a dedicated service so the route layer
becomes a thin proxy (endpoint → service → serialize).

All methods take an explicit ``db: AsyncSession``; the service does not
hold session state. This keeps service methods easy to compose and test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import days_since, safe_float, to_utc
from app.models.customer import Customer, CustomerFollowUp, CustomerLog
from app.models.finance import PaymentRecord
from app.models.sales import Opportunity, SalesOrder
from app.services.base_crud import BaseCRUDService


# ── RFM / tier helpers (pure functions, no DB) ─────────────────────────


def rfm_bucket(
    days_since_contact: int,
    order_count: int,
    total_amount: float,
) -> tuple[int, int, int, str]:
    """Compute Recency/Frequency/Monetary (1-5 each) and a tier label.

    Tier rules follow the marketing convention: 重要价值 / 重要发展 /
    重要保持 / 流失风险 / 一般价值.
    """
    if days_since_contact <= 30:
        recency = 5
    elif days_since_contact <= 60:
        recency = 4
    elif days_since_contact <= 120:
        recency = 3
    elif days_since_contact <= 180:
        recency = 2
    else:
        recency = 1

    if order_count >= 12:
        frequency = 5
    elif order_count >= 6:
        frequency = 4
    elif order_count >= 3:
        frequency = 3
    elif order_count >= 1:
        frequency = 2
    else:
        frequency = 1

    if total_amount >= 1_000_000:
        monetary = 5
    elif total_amount >= 500_000:
        monetary = 4
    elif total_amount >= 100_000:
        monetary = 3
    elif total_amount >= 20_000:
        monetary = 2
    else:
        monetary = 1

    if recency >= 4 and frequency >= 4 and monetary >= 4:
        tier = "重要价值"
    elif recency >= 3 and (frequency >= 3 or monetary >= 3):
        tier = "重要发展"
    elif recency <= 2 and (frequency >= 3 or monetary >= 3):
        tier = "重要保持"
    elif recency <= 2 and frequency <= 2 and monetary <= 2:
        tier = "流失风险"
    else:
        tier = "一般价值"

    return recency, frequency, monetary, tier


def health_label(score: float) -> str:
    """Translate a 0-100 health score into a Chinese label."""
    if score >= 80:
        return "优秀"
    if score >= 60:
        return "良好"
    if score >= 40:
        return "一般"
    return "差"


# Follow-up status considered "terminal" (no further action expected).
TERMINAL_FOLLOWUP_STATUSES = ("completed", "cancelled")


# ── Service ────────────────────────────────────────────────────────────


class CustomerStatsService(BaseCRUDService):
    """Customer-related read aggregations and business calculations.

    CRUD methods (list/get/create/update/delete) are inherited from
    BaseCRUDService. Stats endpoints live as additional class methods.
    """

    model = Customer  # base_crud needs a model; we use the primary entity

    # ── single-customer stats ──────────────────────────────────────────

    async def get_customer_stats(
        self, db: AsyncSession, customer_id: int
    ) -> dict[str, Any] | None:
        """Aggregate order / payment / credit / health / RFM for one customer."""
        customer_obj = await self.get(db, customer_id)
        if customer_obj is None:
            return None
        customer = cast(Customer, customer_obj)

        now = datetime.now(timezone.utc)
        created_at = to_utc(customer.created_at) or now
        created_days = max(0, (now - created_at).days)

        order_agg = (
            await db.execute(
                select(
                    func.count(SalesOrder.id),
                    func.coalesce(func.sum(SalesOrder.total_amount), 0),
                    func.max(
                        func.coalesce(SalesOrder.order_date, SalesOrder.created_at)
                    ),
                ).where(
                    SalesOrder.customer_id == customer_id,
                    SalesOrder.deleted_at.is_(None),
                )
            )
        ).first()

        order_count = int(order_agg[0] or 0) if order_agg else 0
        total_revenue = safe_float(order_agg[1]) if order_agg else 0.0
        last_order_at = to_utc(order_agg[2]) if order_agg else None

        paid_total = safe_float(
            (
                await db.execute(
                    select(func.coalesce(func.sum(PaymentRecord.amount), 0)).where(
                        PaymentRecord.customer_id == customer_id,
                        PaymentRecord.deleted_at.is_(None),
                    )
                )
            ).scalar()
        )
        outstanding = max(0.0, round(total_revenue - paid_total, 2))

        credit_limit = safe_float(customer.credit_limit)
        credit_usage_pct = (
            round((outstanding / credit_limit) * 100, 1) if credit_limit > 0 else 0.0
        )

        # Lazy import to avoid a circular dependency at module load.
        from app.domain.states import CUSTOMER_STATUS_LABELS

        lifecycle = CUSTOMER_STATUS_LABELS.get(
            customer.status, customer.status or "未知"
        )

        ai_insights = (
            customer.ai_insights if isinstance(customer.ai_insights, dict) else {}
        )
        health_score = safe_float(ai_insights.get("health_score"))
        health_label_text = ai_insights.get("health_label")
        if health_score <= 0:
            score = self._compute_health_score(
                order_count=order_count,
                total_revenue=total_revenue,
                days_since_contact=days_since(customer.last_contacted_at, now),
                level=customer.level,
                credit_usage_pct=credit_usage_pct,
            )
            health_score = round(score, 1)
            health_label_text = health_label(health_score)
        else:
            health_score = round(health_score, 1)
            health_label_text = health_label_text or health_label(health_score)

        aging = self.build_aging(outstanding, last_order_at)

        return {
            "customer_id": customer_id,
            "created_days": created_days,
            "lifecycle": lifecycle,
            "order_count": order_count,
            "total_revenue": round(total_revenue, 2),
            "last_order_date": last_order_at,
            "credit_limit": round(credit_limit, 2),
            "outstanding": round(outstanding, 2),
            "paid_total": round(paid_total, 2),
            "credit_usage_pct": credit_usage_pct,
            "aging": aging,
            "health_score": health_score,
            "health_label": health_label_text,
        }

    # ── customer timeline ──────────────────────────────────────────────

    async def get_customer_timeline(
        self, db: AsyncSession, customer_id: int
    ) -> list[dict[str, Any]] | None:
        """Build a unified timeline of contact / follow-up / order events."""
        customer_obj = await self.get(db, customer_id)
        if customer_obj is None:
            return None
        customer = cast(Customer, customer_obj)

        followups = (
            (
                await db.execute(
                    select(CustomerFollowUp)
                    .where(
                        CustomerFollowUp.customer_id == customer_id,
                        CustomerFollowUp.deleted_at.is_(None),
                    )
                    .order_by(CustomerFollowUp.created_at.desc())
                    .limit(30)
                )
            )
            .scalars()
            .all()
        )

        orders = (
            (
                await db.execute(
                    select(SalesOrder)
                    .where(
                        SalesOrder.customer_id == customer_id,
                        SalesOrder.deleted_at.is_(None),
                    )
                    .order_by(SalesOrder.created_at.desc())
                    .limit(30)
                )
            )
            .scalars()
            .all()
        )

        events: list[dict] = []
        if customer.last_contacted_at:
            events.append(
                {
                    "id": 2_000_000_000 + customer.id,
                    "type": "contact",
                    "title": "客户联系记录",
                    "detail": "客户最近联系时间已更新",
                    "time": str(customer.last_contacted_at),
                }
            )

        for fu in followups:
            event_time = fu.completed_at or fu.planned_at or fu.created_at
            if event_time is None:
                continue
            detail_parts = [part for part in [fu.content, fu.result] if part]
            detail = (
                "；".join(detail_parts) if detail_parts else (fu.status or "跟进记录")
            )
            events.append(
                {
                    "id": fu.id,
                    "type": "followup",
                    "title": f"客户跟进（{fu.method or '记录'}）",
                    "detail": detail,
                    "time": str(event_time),
                }
            )

        for order in orders:
            event_time = order.order_date or order.created_at
            if event_time is None:
                continue
            amount = safe_float(order.total_amount)
            events.append(
                {
                    "id": 1_000_000_000 + order.id,
                    "type": "order",
                    "title": f"销售订单 {order.order_no or f'#{order.id}'}",
                    "detail": f"金额 ¥{amount:.2f}，状态 {order.status or 'unknown'}",
                    "time": str(event_time),
                }
            )

        events.sort(key=lambda item: item["time"], reverse=True)
        return events[:50]

    # ── dashboard / aggregate stats ───────────────────────────────────

    async def get_dashboard_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Group-by counts (industry/level/region/source/type) + monthly trend."""

        async def _agg(field: str) -> list[dict[str, Any]]:
            col = getattr(Customer, field)
            r = await db.execute(
                select(col, func.count(Customer.id))
                .where(Customer.deleted_at.is_(None))
                .group_by(col)
            )
            return sorted(
                [{"name": row[0] or "未设置", "value": row[1]} for row in r.all()],
                key=lambda x: -x["value"],
            )

        async def _monthly() -> list[dict[str, Any]]:
            month_expr = func.date_trunc("month", Customer.created_at)
            r = await db.execute(
                select(month_expr, func.count(Customer.id))
                .where(Customer.deleted_at.is_(None), Customer.created_at.isnot(None))
                .group_by(month_expr)
                .order_by(month_expr.desc())
                .limit(12)
            )
            rows = list(r.all())
            rows.reverse()
            return [{"month": str(row[0])[:7], "count": row[1]} for row in rows]

        total_r = await db.execute(
            select(func.count(Customer.id)).where(Customer.deleted_at.is_(None))
        )

        return {
            "total": total_r.scalar() or 0,
            "by_industry": await _agg("industry"),
            "by_level": await _agg("level"),
            "by_region": await _agg("region"),
            "by_source": await _agg("source"),
            "by_type": await _agg("customer_type"),
            "monthly": await _monthly(),
        }

    # ── AI intelligence stats ─────────────────────────────────────────

    async def get_ai_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Health, churn, RFM tier distributions + lifecycle overview."""
        from app.domain.states import CUSTOMER_STATUS_LABELS

        now = datetime.now(timezone.utc)
        days_30 = now - timedelta(days=30)
        stale_cutoff = now - timedelta(days=60)

        customers = (
            await db.execute(
                select(
                    Customer.id,
                    Customer.level,
                    Customer.status,
                    Customer.last_contacted_at,
                    Customer.ai_insights,
                ).where(Customer.deleted_at.is_(None))
            )
        ).all()

        total = len(customers)
        ai_computed = 0
        never_contacted = 0
        stale_high_value = 0
        high_churn_count = 0
        rfm_tiers: dict[str, int] = {}
        churn_dist: dict[str, int] = {}
        lifecycle_map: dict[str, int] = {}
        health_scores: list[float] = []

        for _id, level, status, last_contacted_at, ai_insights in customers:
            lifecycle_key = CUSTOMER_STATUS_LABELS.get(status, status or "未设置")
            lifecycle_map[lifecycle_key] = lifecycle_map.get(lifecycle_key, 0) + 1

            if last_contacted_at is None:
                never_contacted += 1

            last_contacted_utc = to_utc(last_contacted_at)
            if (
                (level or "").upper() == "A"
                and last_contacted_utc
                and last_contacted_utc < stale_cutoff
            ):
                stale_high_value += 1

            if not isinstance(ai_insights, dict):
                continue

            ai_computed += 1
            tier = (ai_insights.get("rfm") or {}).get("tier") or "未分析"
            rfm_tiers[tier] = rfm_tiers.get(tier, 0) + 1

            churn = ai_insights.get("churn") or ai_insights.get("churn_risk") or {}
            risk_level = churn.get("risk_level") or "未知"
            churn_dist[risk_level] = churn_dist.get(risk_level, 0) + 1

            risk_score = safe_float(churn.get("risk_score"))
            if risk_score >= 70:
                high_churn_count += 1

            health_score = safe_float(ai_insights.get("health_score"))
            if health_score > 0:
                health_scores.append(health_score)

        recent_orders_cus = await db.execute(
            select(SalesOrder.customer_id)
            .where(
                SalesOrder.deleted_at.is_(None),
                SalesOrder.created_at >= days_30,
            )
            .distinct()
        )
        recent_cus_ids = set(recent_orders_cus.scalars().all())
        followup_cus = await db.execute(
            select(CustomerFollowUp.customer_id)
            .where(
                CustomerFollowUp.deleted_at.is_(None),
                CustomerFollowUp.created_at >= days_30,
            )
            .distinct()
        )
        recent_cus_ids |= set(followup_cus.scalars().all())
        active_30d = len(recent_cus_ids)

        avg_health = (
            round(sum(health_scores) / len(health_scores), 1) if health_scores else 0
        )

        by_lifecycle = [
            {"stage": stage, "count": count}
            for stage, count in sorted(
                lifecycle_map.items(), key=lambda item: (-item[1], item[0])
            )
        ]

        return {
            "total": total,
            "ai_computed": ai_computed,
            "ai_coverage_pct": round(ai_computed / total * 100, 1) if total > 0 else 0,
            "rfm_tiers": rfm_tiers,
            "churn_dist": churn_dist,
            "never_contacted": never_contacted,
            "stale_high_value": stale_high_value,
            "active_30d": active_30d,
            "avg_health_score": avg_health,
            "by_lifecycle": by_lifecycle,
            "high_churn_count": high_churn_count,
        }

    # ── batch AI scoring (mutates Customer.ai_insights) ───────────────

    async def batch_score_ai(
        self, db: AsyncSession, customer_ids: list[int] | None = None
    ) -> dict[str, int]:
        """Refresh lightweight AI insights (RFM, health, churn) in bulk.

        Returns counts: ``{"scored": n, "errors": n, "total": n}``.
        """
        import logging

        logger = logging.getLogger(__name__)

        now = datetime.now(timezone.utc)
        d90 = now - timedelta(days=90)

        customer_stmt = select(Customer).where(Customer.deleted_at.is_(None))
        if customer_ids:
            customer_stmt = customer_stmt.where(Customer.id.in_(customer_ids))
        customers = (await db.execute(customer_stmt)).scalars().all()

        if not customers:
            return {"scored": 0, "errors": 0, "total": 0}

        customer_ids = [c.id for c in customers]

        order_rows = (
            await db.execute(
                select(
                    SalesOrder.customer_id,
                    func.count(SalesOrder.id),
                    func.coalesce(func.sum(SalesOrder.total_amount), 0),
                    func.max(SalesOrder.created_at),
                    func.count(SalesOrder.id).filter(SalesOrder.created_at >= d90),
                )
                .where(
                    SalesOrder.deleted_at.is_(None),
                    SalesOrder.customer_id.in_(customer_ids),
                )
                .group_by(SalesOrder.customer_id)
            )
        ).all()
        order_map: dict[int, dict[str, Any]] = {
            int(row[0]): {
                "count": int(row[1] or 0),
                "amount": safe_float(row[2]),
                "last_order_at": to_utc(row[3]),
                "count_90d": int(row[4] or 0),
            }
            for row in order_rows
        }

        latest_followup_rows = (
            await db.execute(
                select(
                    CustomerFollowUp.customer_id, func.max(CustomerFollowUp.created_at)
                )
                .where(
                    CustomerFollowUp.deleted_at.is_(None),
                    CustomerFollowUp.customer_id.in_(customer_ids),
                )
                .group_by(CustomerFollowUp.customer_id)
            )
        ).all()
        followup_last_map = {
            int(row[0]): to_utc(row[1]) for row in latest_followup_rows
        }

        opp_rows = (
            await db.execute(
                select(Opportunity.customer_id, func.count(Opportunity.id))
                .where(
                    Opportunity.deleted_at.is_(None),
                    Opportunity.customer_id.in_(customer_ids),
                    Opportunity.stage.in_(
                        ["lead", "qualification", "proposal", "negotiation"]
                    ),
                )
                .group_by(Opportunity.customer_id)
            )
        ).all()
        opp_map = {int(row[0]): int(row[1] or 0) for row in opp_rows}

        scored = 0
        errors = 0

        for customer in customers:
            try:
                stats = order_map.get(customer.id, {})
                order_count = int(stats.get("count", 0))
                total_amount = safe_float(stats.get("amount"))
                last_order_at = stats.get("last_order_at")
                order_count_90d = int(stats.get("count_90d", 0))

                last_contact_at = to_utc(
                    customer.last_contacted_at
                ) or followup_last_map.get(customer.id)
                days_since_contact_v = days_since(last_contact_at, now)
                days_since_order_v = days_since(last_order_at, now)
                open_opportunities = opp_map.get(customer.id, 0)

                recency, frequency, monetary, tier = rfm_bucket(
                    days_since_contact_v, order_count, total_amount
                )

                level_bonus = {"A": 12.0, "B": 6.0, "C": 0.0, "D": -6.0}.get(
                    (customer.level or "").upper(), 0.0
                )
                contact_term = max(0.0, min(30.0, (120 - days_since_contact_v) * 0.25))
                order_term = max(0.0, min(24.0, order_count_90d * 4.0))
                health_score = max(
                    0.0,
                    min(
                        100.0, round(46.0 + level_bonus + contact_term + order_term, 1)
                    ),
                )

                if health_score >= 80:
                    health_label_text = "健康"
                elif health_score >= 60:
                    health_label_text = "关注"
                else:
                    health_label_text = "风险"

                order_risk = min(100.0, days_since_order_v / 120.0 * 100.0)
                contact_risk = min(100.0, days_since_contact_v / 120.0 * 100.0)
                opp_risk = 0.0 if open_opportunities > 0 else 10.0
                churn_risk = max(
                    0.0,
                    min(
                        100.0,
                        round(order_risk * 0.55 + contact_risk * 0.35 + opp_risk, 1),
                    ),
                )

                if churn_risk >= 70:
                    risk_level = "高"
                elif churn_risk >= 40:
                    risk_level = "中"
                else:
                    risk_level = "低"

                churn_payload = {
                    "risk_score": churn_risk,
                    "risk_level": risk_level,
                    "days_since_contact": days_since_contact_v,
                    "days_since_order": days_since_order_v,
                    "open_opportunities": open_opportunities,
                }

                merged_insights = (
                    dict(customer.ai_insights)
                    if isinstance(customer.ai_insights, dict)
                    else {}
                )
                merged_insights.update(
                    {
                        "updated_at": now.isoformat(),
                        "health_score": health_score,
                        "health_label": health_label_text,
                        "rfm": {
                            "recency": recency,
                            "frequency": frequency,
                            "monetary": monetary,
                            "tier": tier,
                        },
                        "churn": churn_payload,
                        "churn_risk": churn_payload,
                    }
                )
                customer.ai_insights = merged_insights
                scored += 1
            except Exception as exc:  # noqa: BLE001
                errors += 1
                logger.warning(
                    "batch-score-ai failed for customer_id=%s: %s", customer.id, exc
                )

        await db.flush()
        return {"scored": scored, "errors": errors, "total": len(customers)}

    # ── recent activity feed ──────────────────────────────────────────

    async def get_recent_activity(
        self, db: AsyncSession, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Tail customer log entries across all customers."""
        logs = (
            await db.execute(
                select(CustomerLog, Customer.name)
                .join(Customer, CustomerLog.customer_id == Customer.id)
                .where(
                    CustomerLog.deleted_at.is_(None),
                    Customer.deleted_at.is_(None),
                )
                .order_by(CustomerLog.created_at.desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "id": row[0].id,
                "customer_id": row[0].customer_id,
                "customer_name": row[1],
                "action": row[0].action,
                "field_name": row[0].field_name,
                "old_value": row[0].old_value,
                "new_value": row[0].new_value,
                "operator": row[0].operator,
                "summary": row[0].summary,
                "created_at": str(row[0].created_at) if row[0].created_at else None,
            }
            for row in logs
        ]

    # ── follow-up queries ─────────────────────────────────────────────

    async def get_overdue_followups(self, db: AsyncSession) -> dict[str, Any]:
        """Overdue follow-ups (planned_at < now and not terminal)."""
        now = datetime.now(timezone.utc)
        rows = (
            await db.execute(
                select(CustomerFollowUp, Customer)
                .join(Customer, CustomerFollowUp.customer_id == Customer.id)
                .where(
                    CustomerFollowUp.deleted_at.is_(None),
                    Customer.deleted_at.is_(None),
                    CustomerFollowUp.planned_at < now,
                    or_(
                        CustomerFollowUp.status.is_(None),
                        CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
                    ),
                )
                .order_by(CustomerFollowUp.planned_at.asc())
                .limit(50)
            )
        ).all()

        items: list[dict[str, Any]] = []
        for fu, cust in rows:
            overdue_days = (now - fu.planned_at.replace(tzinfo=timezone.utc)).days
            items.append(
                {
                    "id": fu.id,
                    "opportunity_id": fu.opportunity_id,
                    "customer_id": cust.id,
                    "customer_name": cust.name,
                    "owner": cust.owner,
                    "method": fu.method,
                    "priority": fu.priority,
                    "planned_at": str(fu.planned_at),
                    "status": fu.status,
                    "content": fu.content,
                    "overdue_days": overdue_days,
                }
            )

        items.sort(key=lambda x: -x["overdue_days"])
        return {"total": len(items), "items": items}

    async def get_follow_up_reminders(
        self, db: AsyncSession, days_ahead: int = 14
    ) -> dict[str, Any]:
        """Bucket upcoming/overdue/today follow-ups within a window."""
        now = datetime.now(timezone.utc)
        today = now.date()
        window_end = now + timedelta(days=days_ahead)
        rows = (
            await db.execute(
                select(CustomerFollowUp, Customer)
                .join(Customer, CustomerFollowUp.customer_id == Customer.id)
                .where(
                    CustomerFollowUp.deleted_at.is_(None),
                    Customer.deleted_at.is_(None),
                    CustomerFollowUp.planned_at.is_not(None),
                    CustomerFollowUp.planned_at <= window_end,
                    or_(
                        CustomerFollowUp.status.is_(None),
                        CustomerFollowUp.status.not_in(TERMINAL_FOLLOWUP_STATUSES),
                    ),
                )
                .order_by(CustomerFollowUp.planned_at.asc())
                .limit(100)
            )
        ).all()

        items: list[dict[str, Any]] = []
        for fu, cust in rows:
            planned_at = fu.planned_at.replace(tzinfo=timezone.utc)
            planned_date = planned_at.date()
            if planned_date < today:
                due_bucket = "overdue"
                overdue_days = (today - planned_date).days
                days_until = None
            elif planned_date == today:
                due_bucket = "today"
                overdue_days = 0
                days_until = 0
            else:
                due_bucket = "upcoming"
                overdue_days = 0
                days_until = (planned_date - today).days

            items.append(
                {
                    "id": fu.id,
                    "opportunity_id": fu.opportunity_id,
                    "customer_id": cust.id,
                    "customer_name": cust.name,
                    "owner": cust.owner,
                    "method": fu.method,
                    "priority": fu.priority,
                    "planned_at": str(fu.planned_at),
                    "status": fu.status,
                    "content": fu.content,
                    "overdue_days": overdue_days,
                    "days_until": days_until,
                    "due_bucket": due_bucket,
                }
            )

        bucket_order = {"overdue": 0, "today": 1, "upcoming": 2}
        items.sort(key=lambda x: (bucket_order[x["due_bucket"]], x["planned_at"]))
        counts = {
            "overdue": sum(1 for item in items if item["due_bucket"] == "overdue"),
            "today": sum(1 for item in items if item["due_bucket"] == "today"),
            "upcoming": sum(1 for item in items if item["due_bucket"] == "upcoming"),
        }
        return {"total": len(items), "counts": counts, "items": items}

    async def get_global_follow_ups(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        priority: str | None = None,
        due_bucket: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        """Global follow-up list with pagination + due-bucket filtering."""
        now = datetime.now(timezone.utc)
        today = now.date()

        conditions: list[ColumnElement[bool]] = [
            CustomerFollowUp.deleted_at.is_(None),
            Customer.deleted_at.is_(None),
        ]
        if status:
            conditions.append(CustomerFollowUp.status == status)
        if priority:
            conditions.append(CustomerFollowUp.priority == priority)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            conditions.append(
                or_(
                    Customer.name.ilike(pattern),
                    Customer.short_name.ilike(pattern),
                    Customer.code.ilike(pattern),
                    Customer.contact_person.ilike(pattern),
                    CustomerFollowUp.content.ilike(pattern),
                    CustomerFollowUp.result.ilike(pattern),
                    CustomerFollowUp.assigned_to.ilike(pattern),
                )
            )

        rows = (
            await db.execute(
                select(CustomerFollowUp, Customer)
                .join(Customer, CustomerFollowUp.customer_id == Customer.id)
                .where(*conditions)
                .order_by(
                    CustomerFollowUp.planned_at.asc().nulls_last(),
                    CustomerFollowUp.created_at.desc(),
                )
            )
        ).all()

        items: list[dict[str, Any]] = []
        for fu, cust in rows:
            planned_at = to_utc(fu.planned_at)
            planned_date = planned_at.date() if planned_at else None
            if fu.status in TERMINAL_FOLLOWUP_STATUSES:
                bucket = "closed"
                overdue_days = 0
                days_until = None
            elif planned_date is None:
                bucket = "unscheduled"
                overdue_days = 0
                days_until = None
            elif planned_date < today and (
                fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES
            ):
                bucket = "overdue"
                overdue_days = (today - planned_date).days
                days_until = None
            elif planned_date == today and (
                fu.status is None or fu.status not in TERMINAL_FOLLOWUP_STATUSES
            ):
                bucket = "today"
                overdue_days = 0
                days_until = 0
            else:
                bucket = "upcoming"
                overdue_days = 0
                days_until = (planned_date - today).days

            items.append(
                {
                    "id": fu.id,
                    "opportunity_id": fu.opportunity_id,
                    "customer_id": cust.id,
                    "customer_name": cust.name,
                    "owner": cust.owner,
                    "method": fu.method,
                    "priority": fu.priority,
                    "planned_at": str(fu.planned_at) if fu.planned_at else None,
                    "completed_at": str(fu.completed_at) if fu.completed_at else None,
                    "created_at": str(fu.created_at) if fu.created_at else None,
                    "status": fu.status,
                    "content": fu.content,
                    "result": fu.result,
                    "assigned_to": fu.assigned_to,
                    "overdue_days": overdue_days,
                    "days_until": days_until,
                    "due_bucket": bucket,
                }
            )

        bucket_order = {
            "overdue": 0,
            "today": 1,
            "upcoming": 2,
            "unscheduled": 3,
            "closed": 4,
        }
        items.sort(
            key=lambda item: (
                bucket_order.get(item["due_bucket"], 9),
                item["planned_at"] or "",
                item["created_at"] or "",
            )
        )
        counts = {
            "all": len(items),
            "overdue": sum(1 for item in items if item["due_bucket"] == "overdue"),
            "today": sum(1 for item in items if item["due_bucket"] == "today"),
            "upcoming": sum(1 for item in items if item["due_bucket"] == "upcoming"),
            "unscheduled": sum(
                1 for item in items if item["due_bucket"] == "unscheduled"
            ),
            "closed": sum(1 for item in items if item["due_bucket"] == "closed"),
        }
        if due_bucket:
            items = [item for item in items if item["due_bucket"] == due_bucket]
        start = (page - 1) * page_size
        paged = items[start : start + page_size]
        return {
            "list": paged,
            "total": len(items),
            "page": page,
            "page_size": page_size,
            "counts": counts,
        }

    # ── private helpers ───────────────────────────────────────────────

    @staticmethod
    def _compute_health_score(
        *,
        order_count: int,
        total_revenue: float,
        days_since_contact: int,
        level: str | None,
        credit_usage_pct: float,
    ) -> float:
        """Heuristic health score (0-100) when AI insights are not present."""
        score = 50.0
        if order_count >= 8:
            score += 20
        elif order_count >= 3:
            score += 12
        elif order_count >= 1:
            score += 6

        if total_revenue >= 500_000:
            score += 15
        elif total_revenue >= 100_000:
            score += 10
        elif total_revenue >= 20_000:
            score += 5

        if days_since_contact <= 30:
            score += 12
        elif days_since_contact <= 90:
            score += 6
        elif days_since_contact >= 365:
            score -= 8

        normalized_level = (level or "").upper()
        if normalized_level == "A":
            score += 5
        elif normalized_level == "B":
            score += 2
        elif normalized_level == "D":
            score -= 5

        if credit_usage_pct >= 95:
            score -= 12
        elif credit_usage_pct >= 80:
            score -= 6
        return max(0.0, min(100.0, score))

    @staticmethod
    def build_aging(
        outstanding: float, last_order_at: datetime | None
    ) -> dict[str, float]:
        """Public aging helper — kept separate for reuse and testing."""
        aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        if outstanding <= 0 or last_order_at is None:
            return aging
        now = datetime.now(timezone.utc)
        age_days = (now - last_order_at).days
        if age_days <= 30:
            aging["0-30"] = outstanding
        elif age_days <= 60:
            aging["31-60"] = outstanding
        elif age_days <= 90:
            aging["61-90"] = outstanding
        else:
            aging["90+"] = outstanding
        return aging


# Module-level singleton for easy import in routes.
customer_stats_service = CustomerStatsService()
