"""Finance domain state machines.

Invoice:       draft → sent → paid | cancelled (terminal)
               sent → overdue → paid
PaymentRecord: pending → completed | overdue
Contract:      draft → active → expired | terminated (terminal)
Commission:    draft → pending_approval → approved → paid | rejected | cancelled
"""

from app.domain.shared.errors import InvalidStateTransition

# ── Invoice ──────────────────────────────────────────────────

INVOICE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"sent", "cancelled"},
    "sent": {"paid", "cancelled", "overdue"},
    "overdue": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}


def assert_can_transition_invoice(current: str, target: str) -> None:
    allowed = INVOICE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"发票状态转换非法: {current} → {target}",
            entity="Invoice",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── PaymentRecord ────────────────────────────────────────────

PAYMENT_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"completed", "overdue"},
    "completed": set(),
    "overdue": {"completed"},
}


def assert_can_transition_payment(current: str, target: str) -> None:
    allowed = PAYMENT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"付款记录状态转换非法: {current} → {target}",
            entity="PaymentRecord",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Contract ─────────────────────────────────────────────────

CONTRACT_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "cancelled"},
    "active": {"expired", "terminated"},
    "expired": set(),
    "terminated": set(),
    "cancelled": set(),
}


def assert_can_transition_contract(current: str, target: str) -> None:
    allowed = CONTRACT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"合同状态转换非法: {current} → {target}",
            entity="Contract",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Commission ───────────────────────────────────────────────

COMMISSION_STATUSES = (
    "draft",
    "pending_approval",
    "approved",
    "paid",
    "rejected",
    "cancelled",
)

COMMISSION_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_approval", "cancelled"},
    "pending_approval": {"approved", "rejected", "draft"},
    "approved": {"paid", "cancelled"},
    "paid": set(),
    "rejected": {"draft"},
    "cancelled": set(),
}


def assert_can_transition_commission(current: str, target: str) -> None:
    allowed = COMMISSION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"佣金状态转换非法: {current} → {target}",
            entity="Commission",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )
