"""Accounting period aggregate — month-end close with hard lock.

A period in OPEN state accepts new journal entries; once CLOSED it
rejects any modification. This is the cornerstone of GAAP/IFRS
financial reporting integrity — auditors must be able to trust that
data inside a closed period never changes.

The aggregate lives in the domain (zero framework deps) and is
persisted via the AccountingPeriod ORM model. The service layer
orchestrates the close workflow (verify, snapshot, transfer P&L,
close, post audit log).
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from app.domain.shared.errors import BusinessRuleViolation


class PeriodStatus(str, Enum):
    OPEN = "open"
    CLOSING = "closing"  # In-progress close (rarely used, for multi-step workflows)
    CLOSED = "closed"
    REOPENED = "reopened"  # Admin override — tracked in audit log


@dataclass
class AccountingPeriod:
    """Accounting period aggregate root.

    One row per (year, month) — uniquely identified by `period_key`
    in 'YYYY-MM' format. The aggregate enforces the close invariants
    and emits a `PeriodClosed` event for downstream consumers
    (financial reports, audit log).
    """

    year: int
    month: int
    status: PeriodStatus = PeriodStatus.OPEN
    id: Optional[int] = None
    closed_at: Optional[datetime] = None
    closed_by: Optional[int] = None
    reopen_reason: Optional[str] = None
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise BusinessRuleViolation(f"Invalid month: {self.month}")
        if not 2000 <= self.year <= 2100:
            raise BusinessRuleViolation(f"Invalid year: {self.year}")

    @property
    def period_key(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def start_date(self) -> date_type:
        return date_type(self.year, self.month, 1)

    @property
    def end_date(self) -> date_type:
        if self.month == 12:
            return date_type(self.year, 12, 31)
        # Last day of month = day before next month's first day
        next_month_first = date_type(self.year, self.month + 1, 1)
        from datetime import timedelta

        return next_month_first - timedelta(days=1)

    @property
    def is_closed(self) -> bool:
        return self.status == PeriodStatus.CLOSED

    def assert_open(self) -> None:
        """Raise if the period cannot accept new entries."""
        if self.status in (PeriodStatus.CLOSED, PeriodStatus.CLOSING):
            raise BusinessRuleViolation(
                f"会计期间 {self.period_key} 已{'结账' if self.is_closed else '结账中'}，"
                f"无法录入或修改分录"
            )

    def close(self, user_id: int) -> None:
        """Transition OPEN → CLOSED, recording who/when.

        Idempotent at the aggregate level: closing an already-closed
        period raises. Re-opening is a separate operation that requires
        admin authorization and a reason.
        """
        if self.status == PeriodStatus.CLOSED:
            raise BusinessRuleViolation(f"会计期间 {self.period_key} 已结账")
        if self.status == PeriodStatus.CLOSING:
            raise BusinessRuleViolation(f"会计期间 {self.period_key} 正在结账中")
        if self.status == PeriodStatus.REOPENED:
            raise BusinessRuleViolation(
                f"会计期间 {self.period_key} 已重开，需先调用 reopen() 才能再次结账"
            )

        self.status = PeriodStatus.CLOSED
        self.closed_at = datetime.now(timezone.utc)
        self.closed_by = user_id

        from app.domain.finance.events import PeriodClosed

        self._events.append(
            PeriodClosed(
                aggregate_id=self.id or 0,
                aggregate_type="AccountingPeriod",
                period_key=self.period_key,
                closed_by=user_id,
            )
        )

    def reopen(self, user_id: int, reason: str) -> None:
        """Admin override: re-open a closed period for corrections.

        Requires a non-empty reason which is persisted for audit.
        The original close timestamp and user are preserved.
        """
        if self.status != PeriodStatus.CLOSED:
            raise BusinessRuleViolation(
                f"只能重新打开已结账的期间 (current={self.status.value})"
            )
        if not reason or not reason.strip():
            raise BusinessRuleViolation("重开原因必填")

        from app.domain.finance.events import PeriodReopened

        self.status = PeriodStatus.REOPENED
        self.reopen_reason = reason
        self._events.append(
            PeriodReopened(
                aggregate_id=self.id or 0,
                aggregate_type="AccountingPeriod",
                period_key=self.period_key,
                reopened_by=user_id,
                reason=reason,
            )
        )

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
