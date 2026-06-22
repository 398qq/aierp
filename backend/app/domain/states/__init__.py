"""State machine definitions for all business aggregates.

Each module exports:
- Status constants (str Enum where applicable)
- TRANSITIONS dict: {from_status: {to_status, ...}}
- assert_can_transition_*(current, target) → raises InvalidStateTransition

Usage in services:
    from app.domain.states import assert_can_transition_quotation
    assert_can_transition_quotation(obj.status, new_status)
"""

from app.domain.states.sales import (
    CUSTOMER_STATUS_LABELS,
    CUSTOMER_TRANSITIONS,
    DELIVERY_TRANSITIONS,
    OPPORTUNITY_TRANSITIONS,
    QUOTATION_TRANSITIONS,
    RETURN_TRANSITIONS,
    SALES_ORDER_TRANSITIONS,
    assert_can_transition_customer,
    assert_can_transition_delivery,
    assert_can_transition_opportunity,
    assert_can_transition_quotation,
    assert_can_transition_return,
    assert_can_transition_sales_order,
)

from app.domain.states.finance import (
    COMMISSION_STATUSES,
    INVOICE_TRANSITIONS,
    PAYMENT_TRANSITIONS,
    CONTRACT_TRANSITIONS,
    COMMISSION_TRANSITIONS,
    CREDIT_NOTE_TRANSITIONS,
    assert_can_transition_credit_note,
    assert_can_transition_invoice,
    assert_can_transition_payment,
    assert_can_transition_contract,
    assert_can_transition_commission,
)

from app.domain.states.transactions import (
    PURCHASE_ORDER_TRANSITIONS,
    GOODS_RECEIPT_TRANSITIONS,
    SUPPLIER_INVOICE_TRANSITIONS,
    TICKET_TRANSITIONS,
    SAMPLE_TRANSITIONS,
    assert_can_transition_purchase_order,
    assert_can_transition_goods_receipt,
    assert_can_transition_supplier_invoice,
    assert_can_transition_ticket,
    assert_can_transition_sample,
)

__all__ = [
    # Sales
    "CUSTOMER_STATUS_LABELS",
    "CUSTOMER_TRANSITIONS",
    "OPPORTUNITY_TRANSITIONS",
    "QUOTATION_TRANSITIONS",
    "RETURN_TRANSITIONS",
    "SALES_ORDER_TRANSITIONS",
    "DELIVERY_TRANSITIONS",
    "assert_can_transition_customer",
    "assert_can_transition_opportunity",
    "assert_can_transition_quotation",
    "assert_can_transition_return",
    "assert_can_transition_sales_order",
    "assert_can_transition_delivery",
    # Finance
    "COMMISSION_STATUSES",
    "INVOICE_TRANSITIONS",
    "PAYMENT_TRANSITIONS",
    "CONTRACT_TRANSITIONS",
    "COMMISSION_TRANSITIONS",
    "CREDIT_NOTE_TRANSITIONS",
    "assert_can_transition_invoice",
    "assert_can_transition_payment",
    "assert_can_transition_contract",
    "assert_can_transition_commission",
    # Transactions
    "PURCHASE_ORDER_TRANSITIONS",
    "GOODS_RECEIPT_TRANSITIONS",
    "SUPPLIER_INVOICE_TRANSITIONS",
    "TICKET_TRANSITIONS",
    "SAMPLE_TRANSITIONS",
    "assert_can_transition_purchase_order",
    "assert_can_transition_goods_receipt",
    "assert_can_transition_supplier_invoice",
    "assert_can_transition_ticket",
    "assert_can_transition_sample",
]
