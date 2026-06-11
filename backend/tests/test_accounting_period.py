"""Tests for AccountingPeriod aggregate — period-close invariants."""

import pytest

from app.domain.finance.events import PeriodClosed, PeriodReopened
from app.domain.finance.period import AccountingPeriod, PeriodStatus
from app.domain.shared.errors import BusinessRuleViolation


class TestAccountingPeriodConstruction:
    def test_valid_period_constructs(self):
        p = AccountingPeriod(year=2026, month=6)
        assert p.year == 2026
        assert p.month == 6
        assert p.status == PeriodStatus.OPEN
        assert p.is_closed is False
        assert p.closed_at is None
        assert p.closed_by is None

    def test_period_key_format(self):
        p = AccountingPeriod(year=2026, month=6)
        assert p.period_key == "2026-06"
        p2 = AccountingPeriod(year=2026, month=12)
        assert p2.period_key == "2026-12"

    def test_rejects_invalid_month_zero(self):
        with pytest.raises(BusinessRuleViolation, match="Invalid month"):
            AccountingPeriod(year=2026, month=0)

    def test_rejects_invalid_month_thirteen(self):
        with pytest.raises(BusinessRuleViolation, match="Invalid month"):
            AccountingPeriod(year=2026, month=13)

    def test_rejects_year_too_old(self):
        with pytest.raises(BusinessRuleViolation, match="Invalid year"):
            AccountingPeriod(year=1999, month=1)

    def test_rejects_year_too_future(self):
        with pytest.raises(BusinessRuleViolation, match="Invalid year"):
            AccountingPeriod(year=2150, month=1)


class TestPeriodDateRange:
    def test_start_date_is_first_of_month(self):
        p = AccountingPeriod(year=2026, month=6)
        from datetime import date

        assert p.start_date == date(2026, 6, 1)

    def test_end_date_30_days_for_june(self):
        p = AccountingPeriod(year=2026, month=6)
        from datetime import date

        assert p.end_date == date(2026, 6, 30)

    def test_end_date_31_days_for_july(self):
        p = AccountingPeriod(year=2026, month=7)
        from datetime import date

        assert p.end_date == date(2026, 7, 31)

    def test_end_date_31_days_for_december(self):
        p = AccountingPeriod(year=2026, month=12)
        from datetime import date

        assert p.end_date == date(2026, 12, 31)

    def test_end_date_handles_leap_year_february(self):
        p = AccountingPeriod(year=2024, month=2)
        from datetime import date

        assert p.end_date == date(2024, 2, 29)

    def test_end_date_handles_non_leap_year_february(self):
        p = AccountingPeriod(year=2026, month=2)
        from datetime import date

        assert p.end_date == date(2026, 2, 28)


class TestPeriodClose:
    def test_close_open_period(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=42)
        assert p.status == PeriodStatus.CLOSED
        assert p.is_closed is True
        assert p.closed_at is not None
        assert p.closed_by == 42

    def test_close_emits_event(self):
        p = AccountingPeriod(year=2026, month=6, id=1)
        p.close(user_id=42)
        events = p.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], PeriodClosed)
        assert events[0].period_key == "2026-06"
        assert events[0].closed_by == 42

    def test_double_close_raises(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation, match="已结账"):
            p.close(user_id=1)

    def test_assert_open_raises_after_close(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation, match="已结账"):
            p.assert_open()

    def test_assert_open_passes_when_open(self):
        p = AccountingPeriod(year=2026, month=6)
        p.assert_open()  # Should not raise

    def test_close_during_closing_raises(self):
        p = AccountingPeriod(year=2026, month=6, status=PeriodStatus.CLOSING)
        with pytest.raises(BusinessRuleViolation, match="正在结账"):
            p.close(user_id=1)

    def test_close_reopened_period_raises(self):
        """A reopened period must call reopen() first then close again."""
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        p.reopen(user_id=2, reason="correction")
        with pytest.raises(BusinessRuleViolation, match="重开"):
            p.close(user_id=3)


class TestPeriodReopen:
    def test_reopen_closed_period(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        p.reopen(user_id=99, reason="error in inventory accrual")
        assert p.status == PeriodStatus.REOPENED
        assert p.reopen_reason == "error in inventory accrual"

    def test_reopen_emits_event(self):
        p = AccountingPeriod(year=2026, month=6, id=1)
        p.close(user_id=1)
        p.reopen(user_id=2, reason="auditor request")
        events = p.collect_events()
        assert any(isinstance(e, PeriodReopened) for e in events)

    def test_reopen_requires_reason(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation, match="原因必填"):
            p.reopen(user_id=2, reason="")
        with pytest.raises(BusinessRuleViolation, match="原因必填"):
            p.reopen(user_id=2, reason="   ")

    def test_reopen_open_period_raises(self):
        p = AccountingPeriod(year=2026, month=6)  # never closed
        with pytest.raises(BusinessRuleViolation, match="只能重新打开已结账的期间"):
            p.reopen(user_id=2, reason="test")

    def test_reopen_already_reopened_raises(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        p.reopen(user_id=2, reason="first")
        with pytest.raises(BusinessRuleViolation, match="只能重新打开已结账的期间"):
            p.reopen(user_id=3, reason="second")

    def test_reopen_preserves_original_close_metadata(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        original_closed_at = p.closed_at
        original_closed_by = p.closed_by
        p.reopen(user_id=2, reason="correction")
        # Reopening doesn't erase the original close
        assert p.closed_at == original_closed_at
        assert p.closed_by == original_closed_by


class TestEventBuffer:
    def test_collect_clears_buffer(self):
        p = AccountingPeriod(year=2026, month=6)
        p.close(user_id=1)
        assert len(p.collect_events()) == 1
        assert p.collect_events() == []
