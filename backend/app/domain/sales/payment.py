"""PaymentRecord aggregate — money-in with state machine.

The payment is the canonical "did the customer actually pay us" record.
When a payment is completed, it auto-reconciles the linked invoice.

Lifecycle:

  PENDING ──complete──▶ COMPLETED
     │                       │
     │                       └─reverse──▶ REVERSED (out of scope)
     │
     └─overdue──▶ OVERDUE (time-based, set by daily job)

Emits events:
- PaymentReceived: Invoice aggregate listens and updates its paid_amount
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.domain.shared.errors import BusinessRuleViolation
from app.domain.sales.events import PaymentReceived
from app.domain.states.finance import assert_can_transition_payment


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    REVERSED = "reversed"


@dataclass
class PaymentRecord:
    """Payment record aggregate root.

    Stage 2: state machine + invoice auto-reconciliation. Service layer
    uses this for state transitions; ORM-level code (finance_service.py)
    wraps for persistence.
    """

    customer_id: int
    amount: float
    id: Optional[int] = None
    payment_no: Optional[str] = None
    invoice_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    delivery_note_id: Optional[int] = None
    status: PaymentStatus = PaymentStatus.PENDING
    payment_method: str = "bank_transfer"
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise BusinessRuleViolation("付款金额必须大于零")
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def _check_transition(self, target: PaymentStatus) -> None:
        assert_can_transition_payment(self.status.value, target.value)

    def complete(self) -> None:
        """Mark payment as completed (money received) → COMPLETED.

        Emits PaymentReceived: Invoice aggregate listens and updates
        its paid_amount, potentially auto-completing the invoice.
        """
        self._check_transition(PaymentStatus.COMPLETED)
        if not self.payment_method:
            raise BusinessRuleViolation("付款方式不能为空")

        self.status = PaymentStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        if self.payment_date is None:
            self.payment_date = self.completed_at
        self._events.append(
            PaymentReceived(
                aggregate_id=self.id or 0,
                payment_id=self.id or 0,
                invoice_id=self.invoice_id or 0,
                customer_id=self.customer_id,
                amount=self.amount,
                method=self.payment_method,
            )
        )

    def mark_overdue(self) -> None:
        """Time-based overdue transition. Called by daily job."""
        if self.status != PaymentStatus.PENDING:
            return  # Only PENDING payments can become overdue
        self.status = PaymentStatus.OVERDUE

    def reverse(self, reason: str) -> None:
        """Reverse a completed payment (refund/chargeback).

        Stage 2: implemented but not wired up to invoice reconciliation
        (would need negative payment record support).
        """
        self._check_transition(PaymentStatus.REVERSED)
        if not reason or not reason.strip():
            raise BusinessRuleViolation("冲销付款必须填写原因")
        self.status = PaymentStatus.REVERSED
        self.notes = (self.notes or "") + f"\n[冲销原因] {reason.strip()}"

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
