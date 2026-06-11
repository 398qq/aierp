"""SalesOrder aggregate — order document with state machine.

Lives between a Quotation (pre-sales) and DeliveryNote (fulfillment).
The order is the canonical "what did the customer agree to buy" record
that downstream documents (delivery, invoice, payment) all reference.

Lifecycle:

  PENDING ──confirm──▶ CONFIRMED ──ship──▶ SHIPPED ──complete──▶ COMPLETED
     │                     │                   │
     │                     │                   └────► CANCELLED (out of scope)
     │                     └─cancel─▶ CANCELLED
     └─cancel──▶ CANCELLED

Emits events:
- OrderConfirmed: triggers inventory reservation
- OrderShipped:   triggers first available ship window
- OrderCompleted: triggers commission accrual (if owner set)
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
    OrderConfirmed,
    OrderShipped,
    OrderCompleted,
)


class OrderStatus(str, Enum):
    PENDING = "pending"      # Just created (or converted from quotation)
    CONFIRMED = "confirmed"  # Customer confirmed (locks inventory)
    SHIPPED = "shipped"      # First shipment dispatched
    COMPLETED = "completed"  # Fully delivered + invoiced
    CANCELLED = "cancelled"  # Cancelled at any stage


_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.CONFIRMED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.CONFIRMED: {
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.SHIPPED: {
        OrderStatus.COMPLETED,
    },
    OrderStatus.COMPLETED: set(),  # terminal
    OrderStatus.CANCELLED: set(),  # terminal
}


@dataclass
class OrderLine:
    """A single line item on a sales order."""

    product_id: Optional[int]
    product_name: str
    quantity: int
    unit_price: float

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise BusinessRuleViolation("订单明细数量必须大于零")
        if self.unit_price < 0:
            raise BusinessRuleViolation("订单明细单价不能为负")

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class SalesOrder:
    """Sales order aggregate root.

    Stage 2: introduces a full state machine + domain events. Service
    layer uses this for state transitions instead of mutating ORM
    directly. ORM-level code (sales_service/orders.py) wraps this for
    persistence.
    """

    customer_id: int
    lines: List[OrderLine] = field(default_factory=list)
    id: Optional[int] = None
    order_no: Optional[str] = None
    quotation_id: Optional[int] = None
    opportunity_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    owner: Optional[str] = None
    total_amount: float = 0.0
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.lines and self.total_amount == 0:
            self._recalc_total()
        elif not self.lines and self.total_amount == 0:
            raise BusinessRuleViolation("订单必须至少有一个明细")

    def add_line(self, line: OrderLine) -> None:
        if self.status != OrderStatus.PENDING:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        self.lines.append(line)
        self._recalc_total()

    def remove_line(self, index: int) -> None:
        if self.status != OrderStatus.PENDING:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        if not 0 <= index < len(self.lines):
            raise IndexError(f"line index {index} out of range")
        self.lines.pop(index)
        self._recalc_total()

    def _recalc_total(self) -> None:
        self.total_amount = sum(line.subtotal for line in self.lines)

    def _check_transition(self, target: OrderStatus) -> None:
        allowed = _ORDER_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} → {target.value} 不允许"
            )

    def confirm(self) -> None:
        """Customer confirmed the order → CONFIRMED.

        Emits OrderConfirmed: inventory layer reserves stock, locking it
        from other orders.
        """
        self._check_transition(OrderStatus.CONFIRMED)
        if not self.lines:
            raise BusinessRuleViolation("空订单不能确认")
        if not self.owner:
            raise BusinessRuleViolation("订单必须有负责人才能确认")

        self.status = OrderStatus.CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)
        self._events.append(
            OrderConfirmed(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                order_no=self.order_no or "",
                customer_id=self.customer_id,
                owner=self.owner,
                lines=tuple(
                    (line.product_id, line.quantity) for line in self.lines
                ),
            )
        )

    def ship(self) -> None:
        """First shipment dispatched → SHIPPED.

        Emits OrderShipped: this is the signal that inventory is being
        deducted (the delivery note handles the actual stock-out).
        """
        self._check_transition(OrderStatus.SHIPPED)
        if not self.lines:
            raise BusinessRuleViolation("空订单不能发货")

        self.status = OrderStatus.SHIPPED
        self.shipped_at = datetime.now(timezone.utc)
        self._events.append(
            OrderShipped(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                order_no=self.order_no or "",
                customer_id=self.customer_id,
            )
        )

    def complete(self) -> None:
        """Order fully delivered + invoiced → COMPLETED.

        Emits OrderCompleted: triggers commission accrual for the owner.
        """
        self._check_transition(OrderStatus.COMPLETED)
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self._events.append(
            OrderCompleted(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                order_no=self.order_no or "",
                customer_id=self.customer_id,
                owner=self.owner or "",
                total_amount=self.total_amount,
            )
        )

    def cancel(self, reason: str) -> None:
        """Cancel the order.

        Allowed from PENDING and CONFIRMED. SHIPPED orders cannot be
        cancelled through this method (use a return process).
        """
        self._check_transition(OrderStatus.CANCELLED)
        if not reason or not reason.strip():
            raise BusinessRuleViolation("取消订单必须填写原因")
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.notes = (self.notes or "") + f"\n[取消原因] {reason.strip()}"

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
