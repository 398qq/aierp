"""Procurement domain events — emitted by the purchase order aggregate."""

from dataclasses import dataclass, field

from app.domain.shared.events import DomainEvent


@dataclass(frozen=True)
class PurchaseOrderApproved(DomainEvent):
    """Emitted when a draft PO is approved."""

    aggregate_type: str = "PurchaseOrder"
    supplier_id: int = 0
    order_no: str = ""


@dataclass(frozen=True)
class PurchaseOrderCancelled(DomainEvent):
    """Emitted when a PO is cancelled."""

    aggregate_type: str = "PurchaseOrder"
    previous_status: str = ""
    reason: str = ""


@dataclass(frozen=True)
class GoodsReceived(DomainEvent):
    """Emitted when goods are received against a PO.

    Inventory handlers should add stock for each received line.
    """

    aggregate_type: str = "PurchaseOrder"
    supplier_id: int = 0
    receipts: tuple = field(default_factory=tuple)
