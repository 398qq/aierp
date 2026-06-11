"""Journal entry aggregate — double-entry bookkeeping rules.

A journal entry is the atomic unit of accounting. It must satisfy:
1. At least one line
2. Sum(debit) == Sum(credit) (always)
3. Each line has either debit or credit, never both
4. Once posted, immutable
5. Reversal creates a new entry that swaps debit/credit of the original
"""

from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from app.domain.shared.errors import BusinessRuleViolation


class JournalStatus(str, Enum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class UnbalancedEntryError(BusinessRuleViolation):
    """Sum of debits does not equal sum of credits."""

    code = "UNBALANCED_JOURNAL_ENTRY"


class InvalidLineError(BusinessRuleViolation):
    """A line has both debit and credit, or neither."""

    code = "INVALID_JOURNAL_LINE"


@dataclass
class JournalLine:
    """A single debit/credit line on a journal entry."""

    account_id: int
    description: str = ""
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        # Coerce to Decimal
        self.debit = Decimal(str(self.debit))
        self.credit = Decimal(str(self.credit))

        if self.debit < 0 or self.credit < 0:
            raise InvalidLineError("金额不能为负")
        if self.debit > 0 and self.credit > 0:
            raise InvalidLineError(
                f"明细借贷不能同时非零 (借={self.debit}, 贷={self.credit})"
            )
        if self.debit == 0 and self.credit == 0:
            raise InvalidLineError("明细借贷不能同时为零")

    @property
    def net(self) -> Decimal:
        """Net amount (debit - credit). For balance-sheet accounts."""
        return self.debit - self.credit


@dataclass
class JournalEntry:
    """Journal entry aggregate root.

    Encapsulates double-entry invariants. Once `post()` is called, no
    further mutations are allowed except `reverse()` which creates a new
    opposite entry.
    """

    entry_date: date_type
    description: str
    lines: List[JournalLine] = field(default_factory=list)
    id: Optional[int] = None
    entry_no: Optional[str] = None
    status: JournalStatus = JournalStatus.DRAFT
    posted_at: Optional[datetime] = None
    posted_by: Optional[int] = None
    reverses_id: Optional[int] = None  # For reversal entries
    _events: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.lines:
            raise UnbalancedEntryError("分录必须至少有一条明细")
        self._validate_balance()

    def _validate_balance(self) -> None:
        total_debit = sum((line.debit for line in self.lines), Decimal("0"))
        total_credit = sum((line.credit for line in self.lines), Decimal("0"))
        if total_debit != total_credit:
            raise UnbalancedEntryError(
                f"借贷不平衡: 借={total_debit}, 贷={total_credit}",
                total_debit=float(total_debit),
                total_credit=float(total_credit),
            )

    def add_line(self, line: JournalLine) -> None:
        if self.status != JournalStatus.DRAFT:
            raise BusinessRuleViolation(
                f"分录 {self.id}: {self.status.value} 状态不可修改"
            )
        self.lines.append(line)
        self._validate_balance()

    @property
    def total_debit(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0"))

    @property
    def total_credit(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0"))

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit

    def post(self, posted_by: int) -> None:
        """Post the entry. Once posted, lines are immutable."""
        if self.status != JournalStatus.DRAFT:
            raise BusinessRuleViolation(
                f"分录 {self.id}: 状态 {self.status.value} 不可过账"
            )
        if not self.is_balanced:
            raise UnbalancedEntryError(
                f"分录 {self.id} 借贷不平衡: 借={self.total_debit}, 贷={self.total_credit}"
            )
        self.status = JournalStatus.POSTED
        self.posted_at = datetime.now(timezone.utc)
        self.posted_by = posted_by

    def reverse(self, posted_by: int, reason: str) -> "JournalEntry":
        """Create a reversing entry with debit/credit swapped.

        The original entry's status moves to REVERSED. The new entry
        references the original via `reverses_id`.
        """
        if self.status != JournalStatus.POSTED:
            raise BusinessRuleViolation(
                f"分录 {self.id}: 只有已过账分录可冲销 (current={self.status.value})"
            )
        if not reason or not reason.strip():
            raise BusinessRuleViolation("冲销原因必填")

        reversed_lines = [
            JournalLine(
                account_id=line.account_id,
                description=f"冲销: {line.description}" if line.description else "冲销",
                debit=line.credit,  # Swap
                credit=line.debit,
            )
            for line in self.lines
        ]
        new_entry = JournalEntry(
            entry_date=date_type.today(),
            description=f"冲销 #{self.entry_no or self.id}: {reason}",
            lines=reversed_lines,
            reverses_id=self.id,
        )
        new_entry.post(posted_by)

        self.status = JournalStatus.REVERSED
        return new_entry

    def collect_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events
