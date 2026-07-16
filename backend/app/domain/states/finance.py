"""Finance domain state machines.

Invoice:       draft → issued → paid | cancelled (terminal)
               issued → overdue → paid
PaymentRecord: pending → completed | overdue
Contract:      draft → signed → active → expired | terminated (terminal)
Commission:    draft → pending_approval → approved → paid | rejected | cancelled
"""

from app.domain.shared.errors import InvalidStateTransition

# ── Invoice ──────────────────────────────────────────────────

INVOICE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"issued", "cancelled"},
    "issued": {"paid", "cancelled", "overdue"},
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
    "draft": {"signed", "cancelled"},
    "signed": {"active", "cancelled"},
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


# ── CreditNote ─────────────────────────────────────────────────

CREDIT_NOTE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"issued", "cancelled"},
    "issued": set(),
    "cancelled": set(),
}


def assert_can_transition_credit_note(current: str, target: str) -> None:
    allowed = CREDIT_NOTE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"冲红发票状态转换非法: {current} → {target}",
            entity="CreditNote",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )
