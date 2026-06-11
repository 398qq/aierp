"""Customer statistics service.

Stage 1 refactor: extracts the 9 business endpoints previously inlined in
``api/v1/customers/stats.py`` into a dedicated service so the route layer
becomes a thin proxy (endpoint → service → serialize).

All methods take an explicit ``db: AsyncSession``; the service does not
hold session state. This keeps service methods easy to compose and test.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
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
        """Aggregate order / payment / credit / health / RFM for one customer.

        Returns ``None`` if the customer does not exist (caller maps to 404).
        """
        customer = await self.get(db, customer_id)
        if customer is None:
            return None

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

        # Aging buckets for accounts receivable (0-30 / 31-60 / 61-90 / 90+ days).
        aging = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        if outstanding > 0 and last_order_at is not None:
            age_days = (now - last_order_at).days
            if age_days <= 30:
                aging["0-30"] = outstanding
            elif age_days <= 60:
                aging["31-60"] = outstanding
            elif age_days <= 90:
                aging["61-90"] = outstanding
            else:
                aging["90+"] = outstanding

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
    def build_aging(outstanding: float, last_order_at: datetime | None) -> dict[str, float]:
        """Public aging helper — kept separate for reuse and testing.

        The original endpoint inlined this logic; tests can now hit it
        directly without going through a DB-bound method.
        """
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
