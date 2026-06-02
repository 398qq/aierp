"""Tests for JournalEntry aggregate — double-entry bookkeeping rules."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.finance.journal import (
    InvalidLineError,
    JournalEntry,
    JournalLine,
    JournalStatus,
    UnbalancedEntryError,
)
from app.domain.shared.errors import BusinessRuleViolation


def _line(
    account_id: int = 1,
    debit: str = "0",
    credit: str = "0",
    description: str = "",
) -> JournalLine:
    return JournalLine(
        account_id=account_id,
        debit=Decimal(debit),
        credit=Decimal(credit),
        description=description,
    )


def _balanced_lines(amount: str = "100.0") -> list[JournalLine]:
    return [
        _line(account_id=1, debit=amount, credit="0", description="Cash"),
        _line(account_id=2, debit="0", credit=amount, description="Revenue"),
    ]


class TestJournalLine:
    def test_debit_only_valid(self):
        line = _line(debit="100")
        assert line.net == Decimal("100")

    def test_credit_only_valid(self):
        line = _line(credit="100")
        assert line.net == Decimal("-100")

    def test_rejects_negative_debit(self):
        with pytest.raises(InvalidLineError):
            _line(debit="-50")

    def test_rejects_negative_credit(self):
        with pytest.raises(InvalidLineError):
            _line(credit="-50")

    def test_rejects_both_debit_and_credit(self):
        with pytest.raises(InvalidLineError, match="同时非零"):
            _line(debit="50", credit="50")

    def test_rejects_neither_debit_nor_credit(self):
        with pytest.raises(InvalidLineError, match="同时为零"):
            _line()


class TestJournalEntryConstruction:
    def test_constructs_with_balanced_lines(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines(),
        )
        assert entry.is_balanced
        assert entry.status == JournalStatus.DRAFT

    def test_constructs_with_unbalanced_lines_raises(self):
        with pytest.raises(UnbalancedEntryError) as ei:
            JournalEntry(
                entry_date=date(2026, 6, 1),
                description="Bad",
                lines=[
                    _line(debit="100"),
                    _line(credit="50"),  # 100 ≠ 50
                ],
            )
        assert ei.value.context["total_debit"] == 100.0
        assert ei.value.context["total_credit"] == 50.0

    def test_constructs_with_no_lines_raises(self):
        with pytest.raises(UnbalancedEntryError, match="至少有一条"):
            JournalEntry(
                entry_date=date(2026, 6, 1),
                description="Empty",
                lines=[],
            )

    def test_totals(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=[
                _line(debit="200"),
                _line(debit="300"),
                _line(credit="500"),
            ],
        )
        assert entry.total_debit == Decimal("500")
        assert entry.total_credit == Decimal("500")


class TestJournalEntryAddLine:
    def test_add_line_keeps_balance(self):
        # Start balanced: 100 debit + 100 credit
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Multi",
            lines=[_line(debit="100"), _line(credit="100")],
        )
        assert entry.is_balanced
        # Add a balanced pair
        entry.lines.extend([
            _line(account_id=3, debit="50"),
            _line(account_id=4, credit="50"),
        ])
        assert entry.is_balanced
        assert len(entry.lines) == 4

    def test_add_unbalanced_line_rejected(self):
        # Start balanced: 100 debit + 100 credit
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Test",
            lines=[_line(debit="100"), _line(credit="100")],
        )
        # Try to add unbalanced line — must raise
        with pytest.raises(UnbalancedEntryError):
            entry.add_line(_line(account_id=3, debit="50"))

    def test_add_line_after_post_raises(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Test",
            lines=_balanced_lines(),
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation):
            entry.add_line(_line(debit="50"))


class TestJournalEntryPost:
    def test_post_draft_entry(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines(),
        )
        entry.post(posted_by=42)
        assert entry.status == JournalStatus.POSTED
        assert entry.posted_by == 42
        assert entry.posted_at is not None

    def test_post_already_posted_raises(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines(),
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation):
            entry.post(posted_by=2)

    def test_post_unbalanced_raises(self):
        # Construct via __post_init__ validation, then break it via unvalidated mutation
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Test",
            lines=_balanced_lines(),
        )
        # Manually break the balance (bypassing add_line validation)
        entry.lines[0].debit = Decimal("200")  # Was 100
        with pytest.raises(UnbalancedEntryError):
            entry.post(posted_by=1)


class TestJournalEntryReverse:
    def test_reverse_posted_creates_new_entry(self):
        original = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines("200.0"),
        )
        original.post(posted_by=1)

        reversal = original.reverse(posted_by=2, reason="error correction")
        assert reversal.status == JournalStatus.POSTED
        assert reversal.reverses_id == original.id
        assert original.status == JournalStatus.REVERSED

    def test_reversal_swaps_debit_and_credit(self):
        original = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=[
                _line(account_id=1, debit="200", description="Cash"),
                _line(account_id=2, credit="200", description="Revenue"),
            ],
        )
        original.post(posted_by=1)

        reversal = original.reverse(posted_by=2, reason="test")
        # Original: account 1 debit 200, account 2 credit 200
        # Reversal: account 1 credit 200, account 2 debit 200
        assert reversal.lines[0].account_id == 1
        assert reversal.lines[0].debit == Decimal("0")
        assert reversal.lines[0].credit == Decimal("200")
        assert reversal.lines[1].account_id == 2
        assert reversal.lines[1].debit == Decimal("200")
        assert reversal.lines[1].credit == Decimal("0")

    def test_reverse_draft_raises(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Draft",
            lines=_balanced_lines(),
        )
        with pytest.raises(BusinessRuleViolation, match="已过账"):
            entry.reverse(posted_by=1, reason="test")

    def test_reverse_requires_reason(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines(),
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation, match="原因必填"):
            entry.reverse(posted_by=2, reason="")
        with pytest.raises(BusinessRuleViolation, match="原因必填"):
            entry.reverse(posted_by=2, reason="   ")

    def test_reverse_twice_raises(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Sale",
            lines=_balanced_lines(),
        )
        entry.post(posted_by=1)
        entry.reverse(posted_by=2, reason="first")
        with pytest.raises(BusinessRuleViolation):
            entry.reverse(posted_by=3, reason="second")


class TestDecimalPrecision:
    def test_handles_decimal_precision(self):
        # 0.1 + 0.2 != 0.3 in float; Decimal handles it
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Precision test",
            lines=[
                _line(debit="0.1"),
                _line(debit="0.2"),
                _line(credit="0.3"),
            ],
        )
        assert entry.is_balanced

    def test_very_small_amounts(self):
        entry = JournalEntry(
            entry_date=date(2026, 6, 1),
            description="Small",
            lines=[
                _line(debit="0.0001"),
                _line(credit="0.0001"),
            ],
        )
        assert entry.is_balanced
