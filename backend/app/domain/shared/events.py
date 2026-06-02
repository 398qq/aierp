"""Domain event base — events that the domain emits when state changes."""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Immutable event emitted by an aggregate.

    `event_name` defaults to the class name so subscribers can dispatch by type.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: int = 0
    aggregate_type: str = ""

    @property
    def event_name(self) -> str:
        return self.__class__.__name__


@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    aggregate_type: str = "SalesOrder"
    customer_id: int = 0
    total_amount: float = 0.0
    lines: tuple = ()
    warehouse_id: int = 0


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    aggregate_type: str = "SalesOrder"
    previous_status: str = ""
    lines: tuple = ()
    reason: str = ""


@dataclass(frozen=True)
class StockReserved(DomainEvent):
    aggregate_type: str = "Inventory"
    product_id: int = 0
    warehouse_id: int = 0
    quantity: int = 0
    reference_type: str = ""
    reference_id: int = 0


@dataclass(frozen=True)
class StockReleased(DomainEvent):
    aggregate_type: str = "Inventory"
    product_id: int = 0
    warehouse_id: int = 0
    quantity: int = 0
    reference_type: str = ""
    reference_id: int = 0
    reason: str = ""
