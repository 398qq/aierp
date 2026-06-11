"""Customer AI — work-queue scoring and next-action decision rules.

Pure functions used by ``work_queue.py``. The legacy monolithic module
inlined this logic; here it is extracted so the scoring can be unit
tested in isolation and reused by other recommendation engines.
"""

from __future__ import annotations

from typing import Any


_LEVEL_BASE: dict[str, float] = {"A": 92.0, "B": 72.0, "C": 50.0, "D": 32.0}
_CREDIT_BASE: dict[str, float] = {"AAA": 10.0, "AA": 8.0, "A": 6.0, "B": 3.0, "C": 0.0}


def derive_value_score(
    level: str | None, monetary_180d: float, credit_level: str | None
) -> float:
    base = _LEVEL_BASE.get((level or "").upper(), 55.0)
    revenue_bonus = min(28.0, monetary_180d / 50_000.0 * 8.0)
    credit_bonus = _CREDIT_BASE.get((credit_level or "").upper(), 2.0)
    return max(0.0, min(100.0, round(base * 0.72 + revenue_bonus + credit_bonus, 1)))


def derive_risk_score(
    churn_risk_score: float,
    last_order_days: int,
    overdue_followups: int,
    outstanding_ratio: float,
) -> float:
    order_risk = min(100.0, last_order_days / 120.0 * 100.0)
    overdue_risk = min(100.0, overdue_followups * 25.0)
    credit_risk = min(100.0, outstanding_ratio * 120.0)
    score = (
        churn_risk_score * 0.5
        + order_risk * 0.2
        + overdue_risk * 0.2
        + credit_risk * 0.1
    )
    return max(0.0, min(100.0, round(score, 1)))


def derive_urgency_score(
    days_since_contact: int, overdue_followups: int, open_opportunities: int
) -> float:
    contact_term = max(0.0, (days_since_contact - 30) * 0.9)
    overdue_term = overdue_followups * 20.0
    opportunity_term = 18.0 if open_opportunities > 0 else 0.0
    score = contact_term + overdue_term + opportunity_term
    return max(0.0, min(100.0, round(score, 1)))


def next_action(
    *,
    customer_name: str,
    overdue_followups: int,
    days_since_contact: int,
    open_opportunities: int,
    outstanding_ratio: float,
    outstanding_amount: float,
    risk_score: float,
) -> dict[str, Any]:
    if outstanding_ratio >= 0.85:
        return {
            "action_type": "credit_review",
            "title": "信用额度复核与回款推进",
            "reason": f"{customer_name} 当前应收占授信比例较高（{outstanding_ratio * 100:.0f}%），建议优先推进回款并复核授信。",
            "confidence": 0.87,
            "due_days": 1,
            "expected_impact": round(outstanding_amount * 0.15, 2),
        }
    if overdue_followups > 0:
        return {
            "action_type": "follow_up_call",
            "title": "逾期跟进回访",
            "reason": f"{customer_name} 存在 {overdue_followups} 条逾期跟进，建议立即电话或拜访回访。",
            "confidence": 0.83,
            "due_days": 1,
            "expected_impact": None,
        }
    if days_since_contact >= 45:
        return {
            "action_type": "relationship_reactivate",
            "title": "关系激活跟进",
            "reason": f"{customer_name} 已 {days_since_contact} 天未联系，建议发起关系激活动作并安排下一次沟通。",
            "confidence": 0.8,
            "due_days": 2,
            "expected_impact": None,
        }
    if open_opportunities > 0:
        return {
            "action_type": "opportunity_push",
            "title": "推进在途商机",
            "reason": f"{customer_name} 当前有 {open_opportunities} 个活跃商机，建议推进样品/报价/商务确认。",
            "confidence": 0.78,
            "due_days": 2,
            "expected_impact": None,
        }
    if risk_score >= 70:
        return {
            "action_type": "retention_plan",
            "title": "流失挽回方案",
            "reason": f"{customer_name} 综合流失风险较高，建议启动客户挽回计划并指定责任人。",
            "confidence": 0.74,
            "due_days": 3,
            "expected_impact": None,
        }
    return {
        "action_type": "routine_touch",
        "title": "常规经营触达",
        "reason": f"{customer_name} 当前风险可控，建议保持周期性触达并更新客户需求。",
        "confidence": 0.68,
        "due_days": 5,
        "expected_impact": None,
    }


# Back-compat private aliases
_derive_value_score = derive_value_score
_derive_risk_score = derive_risk_score
_derive_urgency_score = derive_urgency_score
_next_action = next_action


__all__ = [
    "derive_value_score",
    "derive_risk_score",
    "derive_urgency_score",
    "next_action",
    "_derive_value_score",
    "_derive_risk_score",
    "_derive_urgency_score",
    "_next_action",
]
