"""Sales domain state machines.

Opportunity: active → won | lost
Quotation:   draft → sent → accepted | rejected | expired | lost → won
SalesOrder:  pending → confirmed → shipped → delivered → completed | cancelled
Delivery:    pending → shipped → delivered | cancelled
Customer:    new_lead → active → converted → vip | inactive → churned
"""

from app.domain.shared.errors import InvalidStateTransition

# ── Opportunity ──────────────────────────────────────────────

OPPORTUNITY_TRANSITIONS: dict[str, set[str]] = {
    "active": {"won", "lost"},
    "won": set(),
    "lost": {"active"},  # can reopen
}


def assert_can_transition_opportunity(current: str, target: str) -> None:
    allowed = OPPORTUNITY_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"商机状态转换非法: {current} → {target}",
            entity="Opportunity",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Quotation ────────────────────────────────────────────────

QUOTATION_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent", "rejected"},
    "sent": {"accepted", "rejected", "expired", "lost", "won"},
    "accepted": {"won"},
    "rejected": set(),
    "expired": set(),
    "lost": set(),
    "won": set(),
}


def assert_can_transition_quotation(current: str, target: str) -> None:
    allowed = QUOTATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"报价单状态转换非法: {current} → {target}",
            entity="Quotation",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── SalesOrder ───────────────────────────────────────────────

SALES_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"confirmed", "cancelled"},
    "draft": {"confirmed", "cancelled"},  # legacy v1 aggregate — synonym for pending
    "confirmed": {"shipped", "partially_shipped", "cancelled"},
    "partially_shipped": {"shipped", "cancelled"},
    "shipped": {"delivered", "completed"},
    "delivered": {"completed"},
    "invoiced": {"completed"},  # legacy v1 aggregate — synonym for delivered
    "completed": set(),
    "cancelled": set(),
}


def assert_can_transition_sales_order(current: str, target: str) -> None:
    allowed = SALES_ORDER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"销售订单状态转换非法: {current} → {target}",
            entity="SalesOrder",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── DeliveryNote ─────────────────────────────────────────────

DELIVERY_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"shipped", "delivered", "cancelled"},
    "shipped": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}


def assert_can_transition_delivery(current: str, target: str) -> None:
    allowed = DELIVERY_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"发货单状态转换非法: {current} → {target}",
            entity="DeliveryNote",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── ReturnNote ─────────────────────────────────────────────────

RETURN_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected"},
    "approved": {"completed", "rejected"},
    "completed": set(),
    "rejected": set(),
}


def assert_can_transition_return(current: str, target: str) -> None:
    allowed = RETURN_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"退货单状态转换非法: {current} → {target}",
            entity="ReturnNote",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Customer ──────────────────────────────────────────────────
# 7 状态全自动转换:
#   new_lead → active → converted → vip | inactive → churned
#
# 转换规则（定时 + 事件驱动）:
#   创建首个机会 → new_lead → active (实时)
#   完成首个订单 → active → converted (实时)
#   12月交易>¥50万 → converted → vip (定时每日02:00)
#   最后互动>90天 → active/converted → inactive (定时每日02:00)
#   手动标记流失 → 任何 → churned (手动)
#   重新互动 → inactive → active (实时)

CUSTOMER_STATUS_LABELS: dict[str, str] = {
    "new_lead": "新潜客",
    "active": "活跃",
    "converted": "已成交",
    "vip": "VIP",
    "inactive": "不活跃",
    "churned": "流失",
}

CUSTOMER_TRANSITIONS: dict[str, set[str]] = {
    "new_lead": {"active", "churned"},
    "active": {"converted", "inactive", "churned"},
    "converted": {"vip", "inactive", "churned"},
    "vip": {"inactive", "churned"},
    "inactive": {"active", "churned"},
    "churned": {"active"},  # 可重新激活
}


def assert_can_transition_customer(current: str, target: str) -> None:
    allowed = CUSTOMER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"客户状态转换非法: {current} → {target}",
            entity="Customer",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )
