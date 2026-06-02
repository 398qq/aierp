"""Finance domain events — emitted by the journal entry and period aggregates."""

from dataclasses import dataclass

from app.domain.shared.events import DomainEvent


@dataclass(frozen=True)
class PeriodClosed(DomainEvent):
    """Emitted when an accounting period is closed.

    Subscribers should:
    - Generate financial reports (P&L, balance sheet) for the period
    - Post an audit log entry
    - Trigger cache invalidation for any period-bound dashboards
    """

    aggregate_type: str = "AccountingPeriod"
    period_key: str = ""
    closed_by: int = 0


@dataclass(frozen=True)
class PeriodReopened(DomainEvent):
    """Emitted when a closed period is reopened by an admin."""

    aggregate_type: str = "AccountingPeriod"
    period_key: str = ""
    reopened_by: int = 0
    reason: str = ""
