"""Quotation aggregate — pre-sales pricing document with state machine."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import (
    BusinessRuleViolation,
    InvalidStateTransition,
)
from app.domain.sales.events import QuotationSent, QuotationAccepted


class QuotationStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


_QUOTATION_TRANSITIONS: dict[QuotationStatus, set[QuotationStatus]] = {
    QuotationStatus.DRAFT: {
        QuotationStatus.SENT,
        QuotationStatus.REJECTED,
    },
    QuotationStatus.SENT: {
        QuotationStatus.ACCEPTED,
        QuotationStatus.REJECTED,
        QuotationStatus.EXPIRED,
        QuotationStatus.CONVERTED,
    },
    QuotationStatus.ACCEPTED: {QuotationStatus.CONVERTED},
}


@dataclass
class QuotationLine:
    """A single line item on a quotation."""

    product_id: Optional[int]
    product_name: str
    quantity: int
    unit_price: Decimal
    cost_price: Optional[Decimal] = None

    @property
    def subtotal(self) -> Decimal:
        return Decimal(self.quantity) * self.unit_price

    @property
    def margin(self) -> Decimal | None:
        """Profit per unit. None if cost unknown."""
        if self.cost_price is None or self.cost_price == 0:
            return None
        return self.unit_price - self.cost_price

    @property
    def margin_pct(self) -> float | None:
        """Margin as a fraction (0.0 - 1.0). None if cost unknown."""
        if self.cost_price is None or self.cost_price == 0:
            return None
        return float(self.margin / self.cost_price)  # type: ignore[operator]

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise BusinessRuleViolation("报价单明细数量必须大于零")
        if self.unit_price < 0:
            raise BusinessRuleViolation("报价单明细单价不能为负")


@dataclass
class Quotation:
    """Quotation aggregate root.

    Lifecycle: DRAFT → SENT → (ACCEPTED | REJECTED | EXPIRED | CONVERTED).
    Once CONVERTED, the quotation is locked because the corresponding sales
    order inherits its line items.
    """

    customer_id: int
    lines: List[QuotationLine] = field(default_factory=list)
    id: Optional[int] = None
    quotation_no: Optional[str] = None
    title: Optional[str] = None
    opportunity_id: Optional[int] = None
    status: QuotationStatus = QuotationStatus.DRAFT
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    tax_rate: Decimal = Decimal("0.13")
    _events: list = field(default_factory=list, init=False, repr=False)

    DEFAULT_VALIDITY_DAYS = 30

    def __post_init__(self) -> None:
        if self.valid_until is None:
            self.valid_until = datetime.now(timezone.utc) + timedelta(
                days=self.DEFAULT_VALIDITY_DAYS
            )

    @property
    def subtotal(self) -> Decimal:
        return sum((line.subtotal for line in self.lines), Decimal("0"))

    @property
    def tax_amount(self) -> Decimal:
        return (self.subtotal * self.tax_rate).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.tax_amount

    @property
    def is_expired(self) -> bool:
        if self.valid_until is None:
            return False
        return datetime.now(timezone.utc) > self.valid_until

    def add_line(self, line: QuotationLine) -> None:
        if self.status != QuotationStatus.DRAFT:
            raise InvalidStateTransition(
                f"报价单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        self.lines.append(line)

    def remove_line(self, index: int) -> None:
        if self.status != QuotationStatus.DRAFT:
            raise InvalidStateTransition(
                f"报价单 {self.id}: {self.status.value} 状态不可修改明细"
            )
        if not 0 <= index < len(self.lines):
            raise IndexError(f"line index {index} out of range")
        self.lines.pop(index)

    def _check_transition(self, target: QuotationStatus) -> None:
        allowed = _QUOTATION_TRANSITIONS.get(self.status, set())
        if target not in allowed:
            raise InvalidStateTransition(
                f"报价单 {self.id}: {self.status.value} → {target.value} 不允许"
            )

    def send(self) -> None:
        """Send the quotation to the customer.

        Emits QuotationSent so notification handlers (email, WeCom) can
        deliver the document.
        """
        self._check_transition(QuotationStatus.SENT)
        if not self.lines:
            raise BusinessRuleViolation("空报价单不能发送")

        self.status = QuotationStatus.SENT
        self._events.append(
            QuotationSent(
                aggregate_id=self.id or 0,
                aggregate_type="Quotation",
                customer_id=self.customer_id,
                quotation_no=self.quotation_no or "",
                total=float(self.total),
            )
        )

    def accept(self) -> None:
        """Customer accepts the quotation."""
        self._check_transition(QuotationStatus.ACCEPTED)
        if self.is_expired:
            raise BusinessRuleViolation("已过期的报价单不能被接受")

        self.status = QuotationStatus.ACCEPTED
        self._events.append(
            QuotationAccepted(
                aggregate_id=self.id or 0,
                aggregate_type="Quotation",
                customer_id=self.customer_id,
                quotation_no=self.quotation_no or "",
            )
        )

    def reject(self, reason: str) -> None:
        """Customer rejects the quotation."""
        self._check_transition(QuotationStatus.REJECTED)
        self.status = QuotationStatus.REJECTED

    def mark_expired(self) -> None:
        """Time-based expiration. Called by a daily job."""
        if self.status != QuotationStatus.SENT:
            return  # Only SENT quotations can expire
        if not self.is_expired:
            return
        self.status = QuotationStatus.EXPIRED

    def convert_to_order(self) -> None:
        """Mark the quotation as converted (after order created)."""
        self._check_transition(QuotationStatus.CONVERTED)
        self.status = QuotationStatus.CONVERTED

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
