"""Sales order aggregate — encapsulates state machine and business rules.

This is a domain object: it has no database / framework dependencies and
emits domain events when state changes. The infrastructure layer maps between
this object and the SQLAlchemy `SalesOrder` model.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
    NotFoundError,
)
from app.domain.sales.events import (
    OrderCancelled,
    OrderConfirmed,
    OrderShipped,
)


class OrderStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    INVOICED = "invoiced"
    CLOSED = "closed"
    CANCELLED = "cancelled"


_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {
        OrderStatus.PARTIALLY_SHIPPED,
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PARTIALLY_SHIPPED: {
        OrderStatus.SHIPPED,
        OrderStatus.CANCELLED,
    },
    OrderStatus.SHIPPED: {OrderStatus.INVOICED},
    OrderStatus.INVOICED: {OrderStatus.CLOSED},
}


@dataclass
class OrderLine:
    """A single line item on a sales order."""

    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise BusinessRuleViolation("订单明细数量必须大于零")
        if self.unit_price < 0:
            raise BusinessRuleViolation("订单明细单价不能为负")


@dataclass
class SalesOrder:
    """Sales order aggregate root.

    Encapsulates the state machine: which transitions are allowed, and what
    side effects (domain events) each transition triggers. The application
    layer is responsible for persisting this aggregate and dispatching its
    events to the event bus.
    """

    customer_id: int
    lines: List[OrderLine] = field(default_factory=list)
    id: Optional[int] = None
    order_no: Optional[str] = None
    status: OrderStatus = OrderStatus.DRAFT
    quotation_id: Optional[int] = None
    notes: Optional[str] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    @property
    def total(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), Decimal("0"))

    def add_line(self, line: OrderLine) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        self.lines.append(line)

    def confirm(self) -> None:
        """Transition DRAFT/PARTIALLY_SHIPPED → CONFIRMED.

        Requires at least one line. Emits OrderConfirmed so inventory can
        be reserved.
        """
        if self.status != OrderStatus.DRAFT:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} → confirmed 不允许"
            )
        if not self.lines:
            raise BusinessRuleViolation("空订单无法确认")

        self.status = OrderStatus.CONFIRMED
        self._events.append(
            OrderConfirmed(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                customer_id=self.customer_id,
                total_amount=float(self.total),
                lines=tuple(
                    (line.product_id, line.product_name, line.quantity)
                    for line in self.lines
                ),
            )
        )

    def ship(self, shipped_lines: list[tuple[int, int]]) -> None:
        """Apply a shipment event.

        `shipped_lines` is a list of (product_id, qty_shipped). If total
        shipped covers all order lines, status moves to SHIPPED; otherwise
        PARTIALLY_SHIPPED. Emits OrderShipped.
        """
        if self.status not in (
            OrderStatus.CONFIRMED,
            OrderStatus.PARTIALLY_SHIPPED,
        ):
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} 状态不允许发货"
            )
        if not shipped_lines:
            raise BusinessRuleViolation("发货明细不能为空")

        shipped_total = sum(q for _, q in shipped_lines)
        ordered_total = sum(line.quantity for line in self.lines)
        is_full = shipped_total >= ordered_total

        self.status = OrderStatus.SHIPPED if is_full else OrderStatus.PARTIALLY_SHIPPED
        self._events.append(
            OrderShipped(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                lines=tuple((pid, qty) for pid, qty in shipped_lines),
                is_full=is_full,
            )
        )

    def cancel(self, reason: str) -> None:
        """Cancel the order. Emits OrderCancelled so inventory can be released."""
        allowed = _TRANSITIONS.get(self.status, set())
        if OrderStatus.CANCELLED not in allowed:
            raise InvalidStateTransition(
                f"订单 {self.id}: {self.status.value} 状态不可取消"
            )

        previous = self.status
        self.status = OrderStatus.CANCELLED

        self._events.append(
            OrderCancelled(
                aggregate_id=self.id or 0,
                aggregate_type="SalesOrder",
                previous_status=previous.value,
                lines=tuple((line.product_id, line.quantity) for line in self.lines),
                reason=reason,
            )
        )

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events


def ensure_order_found(order: Optional[SalesOrder], order_id: int) -> SalesOrder:
    """Helper to raise NotFoundError if an order is missing."""
    if order is None:
        raise NotFoundError(
            f"销售订单 {order_id} 不存在",
            order_id=order_id,
        )
    return order
