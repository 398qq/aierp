"""Sales domain events — emitted by the order and quotation aggregates."""

from dataclasses import dataclass, field

from app.domain.shared.events import DomainEvent


@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    """Emitted when a sales order moves to CONFIRMED.

    Inventory handlers should reserve stock for each line.
    """

    aggregate_type: str = "SalesOrder"
    customer_id: int = 0
    total_amount: float = 0.0
    lines: tuple = field(default_factory=tuple)
    warehouse_id: int = 0


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    """Emitted when a sales order is cancelled.

    Inventory handlers should release any reserved stock.
    """

    aggregate_type: str = "SalesOrder"
    previous_status: str = ""
    lines: tuple = field(default_factory=tuple)
    reason: str = ""


@dataclass(frozen=True)
class OrderShipped(DomainEvent):
    """Emitted when an order (or part of it) is shipped."""

    aggregate_type: str = "SalesOrder"
    lines: tuple = field(default_factory=tuple)
    is_full: bool = False


@dataclass(frozen=True)
class QuotationSent(DomainEvent):
    """Emitted when a quotation is sent to a customer.

    Notification handlers should email / WeCom / SMS the document.
    """

    aggregate_type: str = "Quotation"
    customer_id: int = 0
    quotation_no: str = ""
    total: float = 0.0


@dataclass(frozen=True)
class QuotationAccepted(DomainEvent):
    """Emitted when a customer accepts a quotation."""

    aggregate_type: str = "Quotation"
    customer_id: int = 0
    quotation_no: str = ""


@dataclass(frozen=True)
class DeliveryShipped(DomainEvent):
    """Emitted when a delivery note is shipped.

    Inventory handlers should deduct stock and release the corresponding
    portion of the sales order reservation.
    """

    aggregate_type: str = "DeliveryNote"
    sales_order_id: int = 0
    customer_id: int = 0
    lines: tuple = field(default_factory=tuple)
