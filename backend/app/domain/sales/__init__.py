"""Sales domain — order aggregate, business rules, events."""

from app.domain.sales.delivery import (
    DeliveryLine,
    DeliveryNote,
    DeliveryStatus,
)
from app.domain.sales.entities import (
    OrderLine,
    OrderStatus,
    SalesOrder,
)
from app.domain.sales.events import (
    DeliveryShipped,
    InvoiceIssued,
    InvoicePaid,
    OrderCancelled,
    OrderCompleted,
    OrderConfirmed,
    OrderShipped,
    PaymentReceived,
    QuotationAccepted,
    QuotationSent,
)
from app.domain.sales.invoice import (
    Invoice,
    InvoiceLine,
    InvoiceStatus,
)
from app.domain.sales.order import (
    OrderLine as OrderLineV2,
    OrderStatus as OrderStatusV2,
    SalesOrder as SalesOrderV2,
)
from app.domain.sales.payment import (
    PaymentRecord,
    PaymentStatus,
)
from app.domain.sales.quotation import (
    Quotation,
    QuotationLine,
    QuotationStatus,
)

__all__ = [
    # v1 (entities.py — used by application/sales/* use cases, kept for back-compat)
    "OrderLine",
    "OrderStatus",
    "SalesOrder",
    # v2 (order.py — Stage 2: richer state machine, 5 statuses with 7 transitions)
    "OrderLineV2",
    "OrderStatusV2",
    "SalesOrderV2",
    # Stage 2 Day 2: invoice + payment state machines
    "Invoice",
    "InvoiceLine",
    "InvoiceStatus",
    "PaymentRecord",
    "PaymentStatus",
    # events
    "OrderCancelled",
    "OrderCompleted",
    "OrderConfirmed",
    "OrderShipped",
    "InvoiceIssued",
    "InvoicePaid",
    "PaymentReceived",
    "Quotation",
    "QuotationLine",
    "QuotationStatus",
    "QuotationAccepted",
    "QuotationSent",
    "DeliveryLine",
    "DeliveryNote",
    "DeliveryStatus",
    "DeliveryShipped",
]
