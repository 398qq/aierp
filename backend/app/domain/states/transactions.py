"""Transaction domain state machines.

PurchaseOrder:  draft → approved → ordered → partially_received → received | cancelled
GoodsReceipt:   received → inspected → accepted | rejected
SupplierInvoice:pending → matched → approved → paid | cancelled
Ticket:         open → in_progress → resolved → closed | cancelled
Sample:         requested → shipped → received → evaluated | cancelled
"""

from app.domain.shared.errors import InvalidStateTransition

# ── PurchaseOrder ────────────────────────────────────────────

PURCHASE_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"approved", "cancelled"},
    "approved": {"ordered", "cancelled"},
    "ordered": {"partially_received", "received", "cancelled"},
    "partially_received": {"received", "cancelled"},
    "received": set(),
    "cancelled": set(),
}

PURCHASE_ORDER_OPEN_STATUSES = frozenset(
    {"draft", "approved", "ordered", "partially_received"}
)
PURCHASE_ORDER_EXPECTED_ARRIVAL_STATUSES = frozenset(
    {"approved", "ordered", "partially_received"}
)
PURCHASE_ORDER_PAYABLE_STATUSES = frozenset(
    {"approved", "ordered", "partially_received", "received"}
)


def assert_can_transition_purchase_order(current: str, target: str) -> None:
    allowed = PURCHASE_ORDER_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"采购单状态转换非法: {current} → {target}",
            entity="PurchaseOrder",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── GoodsReceipt ─────────────────────────────────────────────

GOODS_RECEIPT_TRANSITIONS: dict[str, set[str]] = {
    "received": {"inspected", "accepted", "rejected"},
    "inspected": {"accepted", "rejected"},
    "accepted": set(),
    "rejected": {"received"},  # can re-receive after rejection
}


def assert_can_transition_goods_receipt(current: str, target: str) -> None:
    allowed = GOODS_RECEIPT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"收货单状态转换非法: {current} → {target}",
            entity="GoodsReceipt",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── SupplierInvoice ──────────────────────────────────────────

SUPPLIER_INVOICE_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"matched", "cancelled"},
    "matched": {"approved", "cancelled"},
    "approved": {"paid", "cancelled"},
    "paid": set(),
    "cancelled": set(),
}


def assert_can_transition_supplier_invoice(current: str, target: str) -> None:
    allowed = SUPPLIER_INVOICE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"供应商发票状态转换非法: {current} → {target}",
            entity="SupplierInvoice",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Ticket ───────────────────────────────────────────────────

TICKET_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "cancelled"},
    "in_progress": {"resolved", "cancelled"},
    "resolved": {"closed", "open"},  # can reopen
    "closed": set(),
    "cancelled": set(),
}


def assert_can_transition_ticket(current: str, target: str) -> None:
    allowed = TICKET_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"工单状态转换非法: {current} → {target}",
            entity="Ticket",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )


# ── Sample ───────────────────────────────────────────────────

SAMPLE_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"shipped", "cancelled"},
    "shipped": {"received", "cancelled"},
    "received": {"evaluated"},
    "evaluated": set(),
    "cancelled": set(),
}


def assert_can_transition_sample(current: str, target: str) -> None:
    allowed = SAMPLE_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransition(
            f"样品状态转换非法: {current} → {target}",
            entity="Sample",
            current=current,
            target=target,
            allowed=sorted(allowed),
        )
