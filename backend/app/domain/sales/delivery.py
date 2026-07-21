"""DeliveryNote aggregate — shipment document with state machine.

Emits events that drive inventory deduction (stock_out + lock release).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)


class DeliveryStatus(str, Enum):
    DRAFT = "pending"  # Map to ORM "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"  # Customer confirmed receipt
    CANCELLED = "cancelled"


@dataclass
class DeliveryLine:
    """A single line item on a delivery note."""

    product_id: Optional[int]
    product_name: str
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise BusinessRuleViolation("发货单明细数量必须大于零")


@dataclass
class DeliveryNote:
    """Delivery note aggregate root.

    Lifecycle:
    - DRAFT → SHIPPED (stock is deducted here)
    - SHIPPED → DELIVERED (customer confirms)
    - DRAFT → CANCELLED (no inventory side effect)
    - SHIPPED → CANCELLED (requires reversing the stock-out — out of scope here)
    """

    sales_order_id: int
    customer_id: int
    lines: List[DeliveryLine] = field(default_factory=list)
    id: Optional[int] = None
    delivery_no: Optional[str] = None
    status: DeliveryStatus = DeliveryStatus.DRAFT
    delivery_date: Optional["datetime"] = None
    received_date: Optional["datetime"] = None
    notes: Optional[str] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def add_line(self, line: DeliveryLine) -> None:
        if self.status != DeliveryStatus.DRAFT:
            raise InvalidStateTransition(
                f"发货单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        self.lines.append(line)

    @property
    def total_quantity(self) -> int:
        return sum(line.quantity for line in self.lines)

    def ship(self) -> None:
        """Mark the delivery as shipped. Emits event for inventory deduction."""
        if self.status != DeliveryStatus.DRAFT:
            raise InvalidStateTransition(
                f"发货单 {self.id}: {self.status.value} → shipped 不允许"
            )
        if not self.lines:
            raise BusinessRuleViolation("空发货单不能发货")

        from app.domain.sales.events import DeliveryShipped

        self.status = DeliveryStatus.SHIPPED
        from datetime import datetime, timezone

        if self.delivery_date is None:
            self.delivery_date = datetime.now(timezone.utc)
        self._events.append(
            DeliveryShipped(
                aggregate_id=self.id or 0,
                aggregate_type="DeliveryNote",
                sales_order_id=self.sales_order_id,
                customer_id=self.customer_id,
                lines=tuple((line.product_id, line.quantity) for line in self.lines),
            )
        )

    def confirm_receipt(self) -> None:
        """Customer confirms receipt."""
        if self.status != DeliveryStatus.SHIPPED:
            raise InvalidStateTransition(
                f"发货单 {self.id}: {self.status.value} → delivered 不允许"
            )
        from datetime import datetime, timezone

        self.status = DeliveryStatus.DELIVERED
        self.received_date = datetime.now(timezone.utc)

    def cancel(self, reason: str) -> None:
        """Cancel the delivery. Stock reversal is a separate operation
        (only needed for SHIPPED deliveries; for DRAFT no stock was deducted)."""
        if self.status not in (DeliveryStatus.DRAFT, DeliveryStatus.SHIPPED):
            raise InvalidStateTransition(
                f"发货单 {self.id}: {self.status.value} 状态不可取消"
            )
        self.status = DeliveryStatus.CANCELLED

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
