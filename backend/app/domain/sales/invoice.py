"""Invoice aggregate — billing document with state machine.

The invoice is the canonical "how much does the customer owe us" record
that downstream payment records all reference. When all linked
payments are completed, the invoice is automatically marked paid.

Lifecycle:

  DRAFT ──issue──▶ ISSUED ──pay_partial──▶ ISSUED
                      │                       │
                      │                       └──pay_full──▶ PAID
                      │
                      └─cancel──▶ CANCELLED

Emits events:
- InvoiceIssued:  notification handlers should email the PDF
- InvoicePaid:   triggers commission accrual (for sales)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)
from app.domain.sales.events import (
    InvoiceIssued,
    InvoicePaid,
)


class InvoiceStatus(str, Enum):
    DRAFT = "draft"  # Created, not yet sent
    ISSUED = "issued"  # Sent to customer, payment pending
    PAID = "paid"  # Fully paid
    CANCELLED = "cancelled"


_INVOICE_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.DRAFT: {
        InvoiceStatus.ISSUED,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.ISSUED: {
        InvoiceStatus.PAID,
        InvoiceStatus.CANCELLED,
    },
    InvoiceStatus.PAID: set(),  # terminal
    InvoiceStatus.CANCELLED: set(),  # terminal
}


@dataclass
class InvoiceLine:
    """A single line item on an invoice."""

    product_id: Optional[int]
    product_name: str
    quantity: int
    unit_price: float

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise BusinessRuleViolation("发票明细数量必须大于零")
        if self.unit_price < 0:
            raise BusinessRuleViolation("发票明细单价不能为负")

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Invoice:
    """Invoice aggregate root.

    Stage 2: full state machine + payment-driven auto-completion.
    Service layer uses this for state transitions. ORM-level code
    (finance_service.py) wraps this for persistence.
    """

    customer_id: int
    lines: List[InvoiceLine] = field(default_factory=list)
    id: Optional[int] = None
    invoice_no: Optional[str] = None
    sales_order_id: Optional[int] = None
    status: InvoiceStatus = InvoiceStatus.DRAFT
    amount: float = 0.0
    tax_rate: float = 0.13
    tax_amount: float = 0.0
    total: float = 0.0
    issued_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    paid_amount: float = 0.0  # Sum of completed payments
    notes: Optional[str] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.lines and self.amount == 0:
            self._recalc()

    def add_line(self, line: InvoiceLine) -> None:
        if self.status != InvoiceStatus.DRAFT:
            raise InvalidStateTransition(
                f"发票 {self.id}: {self.status.value} 状态不可修改明细"
            )
        self.lines.append(line)
        self._recalc()

    def _recalc(self) -> None:
        self.amount = sum(line.subtotal for line in self.lines)
        self.tax_amount = round(self.amount * self.tax_rate, 2)
        self.total = self.amount + self.tax_amount

    def _check_transition(self, target: InvoiceStatus) -> None:
        allowed = _INVOICE_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidStateTransition(
                f"发票 {self.id}: {self.status.value} → {target.value} 不允许"
            )

    def issue(self) -> None:
        """Issue the invoice to the customer → ISSUED.

        Emits InvoiceIssued for notification.
        """
        self._check_transition(InvoiceStatus.ISSUED)
        if not self.lines:
            raise BusinessRuleViolation("空发票不能开具")
        if self.amount <= 0:
            raise BusinessRuleViolation("金额为 0 的发票不能开具")

        self.status = InvoiceStatus.ISSUED
        self.issued_at = datetime.now(timezone.utc)
        self._events.append(
            InvoiceIssued(
                aggregate_id=self.id or 0,
                aggregate_type="Invoice",
                invoice_no=self.invoice_no or "",
                customer_id=self.customer_id,
                total=self.total,
            )
        )

    def record_payment(self, amount: float) -> None:
        """Record a payment against this invoice.

        Stage 2 helper: called by PaymentService when a payment linked
        to this invoice is completed. Auto-transitions to PAID when
        cumulative paid_amount >= total.
        """
        if self.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PAID):
            raise InvalidStateTransition(
                f"发票 {self.id}: {self.status.value} 状态不能记录付款"
            )
        if amount <= 0:
            raise BusinessRuleViolation("付款金额必须大于零")

        self.paid_amount += amount
        if self.paid_amount >= self.total and self.status != InvoiceStatus.PAID:
            self._check_transition(InvoiceStatus.PAID)
            self.status = InvoiceStatus.PAID
            self.paid_at = datetime.now(timezone.utc)
            self._events.append(
                InvoicePaid(
                    aggregate_id=self.id or 0,
                    aggregate_type="Invoice",
                    invoice_no=self.invoice_no or "",
                    customer_id=self.customer_id,
                    total=self.total,
                )
            )

    def cancel(self, reason: str) -> None:
        """Cancel the invoice. Only allowed from DRAFT or ISSUED.

        PAID invoices cannot be cancelled through this method (use a
        credit note process).
        """
        self._check_transition(InvoiceStatus.CANCELLED)
        if not reason or not reason.strip():
            raise BusinessRuleViolation("取消发票必须填写原因")
        self.status = InvoiceStatus.CANCELLED
        self.notes = (self.notes or "") + f"\n[取消原因] {reason.strip()}"

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
