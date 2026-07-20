"""Domain unit tests — pure aggregate logic, no DB, no FastAPI.

Covers the domain layer that lives under ``app/domain/``. These tests
run in <100ms (no fixtures, no DB session) and act as the safety net
for business rules. The audit report §1.2 flagged this layer as
'skeleton' — these tests push the domain toward full coverage.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.domain.finance.journal import (
    JournalEntry,
    JournalLine,
    JournalStatus,
    UnbalancedEntryError,
    InvalidLineError,
)
from app.domain.finance.period import AccountingPeriod, PeriodStatus
from app.domain.inventory.batch import (
    BatchStatus,
    InventoryBatch,
    allocate_fefo,
    allocate_fifo_by_received,
    mark_expired_batches,
)
from app.domain.inventory.cost_strategy import (
    FIFOCost,
    FIFOCostTracker,
    StandardCost,
    WeightedAverageCost,
    make_cost_strategy,
)
from app.domain.sales.quotation import (
    Quotation,
    QuotationLine,
    QuotationStatus,
)
from app.domain.shared.errors import (
    BusinessRuleViolation,
    ConcurrentModificationError,
    DomainError,
    InsufficientStockError,
    InvalidStateTransition,
    NotFoundError,
)
from app.domain.shared.money import (
    SUPPORTED_CURRENCIES,
    CurrencyConversionError,
    ExchangeRate,
    ExchangeRateProvider,
    Money,
    build_triangulation,
    convert,
)


# ============================================================================
# shared.errors
# ============================================================================


class TestDomainErrors:
    def test_domain_error_carries_message_and_code(self):
        exc = DomainError("boom", foo="bar")
        assert exc.message == "boom"
        assert exc.code == "DOMAIN_ERROR"
        assert exc.http_status == 400
        assert exc.context == {"foo": "bar"}
        assert exc.to_payload() == {"code": "DOMAIN_ERROR", "msg": "boom", "foo": "bar"}

    def test_subclasses_inherit_properly(self):
        assert issubclass(BusinessRuleViolation, DomainError)
        assert issubclass(InvalidStateTransition, DomainError)
        assert issubclass(NotFoundError, DomainError)
        assert issubclass(ConcurrentModificationError, DomainError)
        assert BusinessRuleViolation("x").http_status == 422
        assert NotFoundError("x").http_status == 404
        assert ConcurrentModificationError("x").http_status == 409

    def test_insufficient_stock_error_payload_includes_qty(self):
        exc = InsufficientStockError(product_id=42, requested=100, available=30)
        assert exc.code == "INSUFFICIENT_STOCK"
        assert exc.context == {"product_id": 42, "requested": 100, "available": 30}
        assert "产品 42" in exc.message


# ============================================================================
# shared.money
# ============================================================================


class TestMoney:
    def test_basic_arithmetic_same_currency(self):
        a = Money(amount=Decimal("10"), currency="CNY")
        b = Money(amount=Decimal("3.5"), currency="CNY")
        assert (a + b).amount == Decimal("13.5")
        assert (a - b).amount == Decimal("6.5")
        assert a + b == Money(amount=Decimal("13.5"), currency="CNY")

    def test_float_coercion_prevents_drift(self):
        m = Money(amount=0.1 + 0.2, currency="USD")
        # 0.1 + 0.2 in float is 0.30000000000000004; Money coerces to Decimal
        assert isinstance(m.amount, Decimal)
        assert m.amount == Decimal("0.30000000000000004")
        # cents property rounds properly
        assert m.cents == Decimal("0.30")

    def test_negative_amount_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            Money(amount=Decimal("-1"), currency="CNY")

    def test_unsupported_currency_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            Money(amount=Decimal("1"), currency="XXX")

    def test_currency_normalized_to_upper(self):
        m = Money(amount=Decimal("1"), currency="cny")
        assert m.currency == "CNY"

    def test_invalid_currency_length_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            Money(amount=Decimal("1"), currency="CN")
        with pytest.raises(BusinessRuleViolation):
            Money(amount=Decimal("1"), currency="CNYY")

    def test_cross_currency_add_raises(self):
        a = Money(amount=Decimal("1"), currency="CNY")
        b = Money(amount=Decimal("1"), currency="USD")
        with pytest.raises(CurrencyConversionError):
            _ = a + b

    def test_multiplication_by_negative_rejected(self):
        m = Money(amount=Decimal("10"), currency="USD")
        with pytest.raises(BusinessRuleViolation):
            _ = m * -1

    def test_jpy_has_zero_decimal_places(self):
        m = Money(amount=Decimal("123.456"), currency="JPY")
        assert m.cents == Decimal("123")  # No decimals for JPY

    def test_sortable_by_amount_within_same_currency(self):
        a = Money(amount=Decimal("1"), currency="CNY")
        b = Money(amount=Decimal("2"), currency="CNY")
        assert a < b
        assert b > a
        assert a <= b
        assert b >= a

    def test_cross_currency_compare_raises(self):
        a = Money(amount=Decimal("1"), currency="CNY")
        b = Money(amount=Decimal("1000000"), currency="USD")
        with pytest.raises(CurrencyConversionError):
            _ = a < b

    def test_supported_currencies_iso_codes(self):
        assert "CNY" in SUPPORTED_CURRENCIES
        assert "USD" in SUPPORTED_CURRENCIES
        assert len(SUPPORTED_CURRENCIES) >= 5


class TestExchangeRate:
    def test_valid_rate_accepted(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.2"),
            effective_date=date(2026, 1, 1),
        )
        assert r.rate == Decimal("7.2")

    def test_negative_rate_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            ExchangeRate(
                from_currency="USD",
                to_currency="CNY",
                rate=Decimal("-1"),
                effective_date=date(2026, 1, 1),
            )

    def test_same_currency_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            ExchangeRate(
                from_currency="USD",
                to_currency="USD",
                rate=Decimal("1"),
                effective_date=date(2026, 1, 1),
            )

    def test_convert_applies_rate(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.2"),
            effective_date=date(2026, 1, 1),
        )
        usd_100 = Money(amount=Decimal("100"), currency="USD")
        result = r.convert(usd_100)
        assert result.currency == "CNY"
        assert result.amount == Decimal("720.00")  # 100 × 7.2

    def test_convert_rejects_mismatched_currency(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.2"),
            effective_date=date(2026, 1, 1),
        )
        cny = Money(amount=Decimal("100"), currency="CNY")
        with pytest.raises(CurrencyConversionError):
            r.convert(cny)


class TestExchangeRateProvider:
    def test_lookup_exact_date(self):
        provider = ExchangeRateProvider()
        provider.add(ExchangeRate("USD", "CNY", Decimal("7.2"), date(2026, 1, 1)))
        r = provider.get("USD", "CNY", at=date(2026, 1, 1))
        assert r is not None
        assert r.rate == Decimal("7.2")

    def test_lookup_falls_back_to_most_recent(self):
        provider = ExchangeRateProvider()
        provider.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        provider.add(ExchangeRate("USD", "CNY", Decimal("7.2"), date(2026, 2, 1)))
        r = provider.get("USD", "CNY", at=date(2026, 3, 1))
        assert r is not None
        assert r.rate == Decimal("7.2")  # Most recent before March

    def test_lookup_returns_none_for_missing_pair(self):
        provider = ExchangeRateProvider()
        assert provider.get("USD", "JPY") is None

    def test_same_currency_returns_none(self):
        provider = ExchangeRateProvider()
        assert provider.get("USD", "USD") is None

    def test_convert_function_uses_provider(self):
        provider = ExchangeRateProvider()
        provider.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        result = convert(Money(amount=Decimal("10"), currency="USD"), "CNY", provider)
        assert result.currency == "CNY"
        assert result.amount == Decimal("70.00")


class TestTriangulation:
    def test_builds_rates_via_base(self):
        provider = ExchangeRateProvider()
        # USD→CNY 7, CNY→EUR 0.13
        provider.add(ExchangeRate("USD", "CNY", Decimal("7"), date(2026, 1, 1)))
        provider.add(ExchangeRate("CNY", "EUR", Decimal("0.13"), date(2026, 1, 1)))
        out = build_triangulation(provider, base="CNY")
        # USD→EUR should be triangulated: 7 × 0.13 = 0.91
        r = out.get("USD", "EUR", at=date(2026, 1, 1))
        assert r is not None
        assert r.rate == Decimal("0.91")
        assert r.source == "triangulated"

    def test_preserves_direct_rates(self):
        provider = ExchangeRateProvider()
        provider.add(ExchangeRate("USD", "CNY", Decimal("7"), date(2026, 1, 1)))
        out = build_triangulation(provider, base="CNY")
        r = out.get("USD", "CNY", at=date(2026, 1, 1))
        assert r is not None
        assert r.rate == Decimal("7")


# ============================================================================
# sales.quotation
# ============================================================================


class TestQuotationLine:
    def test_zero_quantity_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            QuotationLine(
                product_id=1, product_name="X", quantity=0, unit_price=Decimal("10")
            )

    def test_negative_unit_price_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            QuotationLine(
                product_id=1, product_name="X", quantity=1, unit_price=Decimal("-1")
            )

    def test_subtotal_is_qty_times_price(self):
        line = QuotationLine(
            product_id=1, product_name="X", quantity=3, unit_price=Decimal("10")
        )
        assert line.subtotal == Decimal("30")

    def test_margin_returns_none_when_cost_unknown(self):
        line = QuotationLine(
            product_id=1, product_name="X", quantity=1, unit_price=Decimal("10")
        )
        assert line.margin is None
        assert line.margin_pct is None

    def test_margin_computed_when_cost_known(self):
        line = QuotationLine(
            product_id=1,
            product_name="X",
            quantity=1,
            unit_price=Decimal("10"),
            cost_price=Decimal("7"),
        )
        assert line.margin == Decimal("3")
        assert line.margin_pct == pytest.approx(3 / 7)

    def test_margin_handles_zero_cost(self):
        line = QuotationLine(
            product_id=1,
            product_name="X",
            quantity=1,
            unit_price=Decimal("10"),
            cost_price=Decimal("0"),
        )
        assert line.margin is None  # cost=0 means unknown


class TestQuotationStateMachine:
    def _make_quotation(self, **kwargs) -> Quotation:
        defaults = dict(customer_id=1, quotation_no="QT-001")
        defaults.update(kwargs)
        return Quotation(**defaults)

    def test_default_validity_is_30_days(self):
        q = self._make_quotation()
        assert q.valid_until is not None
        delta = q.valid_until - datetime.now(timezone.utc)
        assert 29 <= delta.days <= 30

    def test_subtotal_tax_total(self):
        q = self._make_quotation()
        q.lines = [
            QuotationLine(
                product_id=1, product_name="A", quantity=2, unit_price=Decimal("100")
            ),
            QuotationLine(
                product_id=2, product_name="B", quantity=1, unit_price=Decimal("50")
            ),
        ]
        assert q.subtotal == Decimal("250")
        # default tax 13%
        assert q.tax_amount == Decimal("32.50")
        assert q.total == Decimal("282.50")

    def test_can_add_line_in_draft(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        assert len(q.lines) == 1

    def test_cannot_add_line_after_send(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        with pytest.raises(InvalidStateTransition):
            q.add_line(
                QuotationLine(
                    product_id=1, product_name="B", quantity=1, unit_price=Decimal("20")
                )
            )

    def test_send_emits_event(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        events = q.collect_events()
        assert len(events) == 1
        assert events[0].event_name == "QuotationSent"
        # collect_events clears
        assert q.collect_events() == []

    def test_cannot_send_empty_quotation(self):
        q = self._make_quotation()
        with pytest.raises(BusinessRuleViolation):
            q.send()

    def test_send_to_accepted_to_converted_is_valid(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        q.accept()
        q.convert_to_order()
        assert q.status == QuotationStatus.WON

    def test_cannot_accept_draft(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        # DRAFT cannot go to ACCEPTED (must go through SENT)
        with pytest.raises(InvalidStateTransition):
            q.accept()

    def test_cannot_accept_expired_quotation(self):
        q = self._make_quotation(
            valid_until=datetime.now(timezone.utc) - timedelta(days=1)
        )
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        with pytest.raises(BusinessRuleViolation):
            q.accept()

    def test_rejected_can_only_come_from_draft_or_sent(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        q.reject(reason="too expensive")
        # Now ACCEPTED is forbidden
        with pytest.raises(InvalidStateTransition):
            q.accept()

    def test_mark_expired_only_works_on_sent(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        # DRAFT — mark_expired is no-op
        q.mark_expired()
        assert q.status == QuotationStatus.DRAFT

    def test_is_expired_property(self):
        past = self._make_quotation(
            valid_until=datetime.now(timezone.utc) - timedelta(days=1)
        )
        future = self._make_quotation(
            valid_until=datetime.now(timezone.utc) + timedelta(days=10)
        )
        assert past.is_expired is True
        assert future.is_expired is False

    def test_remove_line(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.add_line(
            QuotationLine(
                product_id=2, product_name="B", quantity=1, unit_price=Decimal("20")
            )
        )
        q.remove_line(0)
        assert len(q.lines) == 1
        assert q.lines[0].product_id == 2

    def test_remove_line_out_of_range(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        with pytest.raises(IndexError):
            q.remove_line(5)

    def test_cannot_remove_line_after_send(self):
        q = self._make_quotation()
        q.add_line(
            QuotationLine(
                product_id=1, product_name="A", quantity=1, unit_price=Decimal("10")
            )
        )
        q.send()
        with pytest.raises(InvalidStateTransition):
            q.remove_line(0)


# ============================================================================
# finance.journal (double-entry bookkeeping)
# ============================================================================


class TestJournalLine:
    def test_negative_amount_rejected(self):
        with pytest.raises(InvalidLineError):
            JournalLine(account_id=1, debit=Decimal("-1"))
        with pytest.raises(InvalidLineError):
            JournalLine(account_id=1, credit=Decimal("-1"))

    def test_both_debit_and_credit_rejected(self):
        with pytest.raises(InvalidLineError):
            JournalLine(account_id=1, debit=Decimal("10"), credit=Decimal("10"))

    def test_neither_debit_nor_credit_rejected(self):
        with pytest.raises(InvalidLineError):
            JournalLine(account_id=1)

    def test_net(self):
        # net is debit - credit
        assert JournalLine(account_id=1, debit=Decimal("10")).net == Decimal("10")
        assert JournalLine(account_id=1, credit=Decimal("7")).net == Decimal("-7")
        # A line with default 0/0 is rejected by the constructor
        # (see test_negative_debit_zero_rejected and similar), so
        # we can't construct a "truly zero" net line in isolation.
        # The JournalEntry tests cover balanced entries.

    def test_float_coercion(self):
        line = JournalLine(account_id=1, debit=10.5)  # not Decimal
        assert isinstance(line.debit, Decimal)
        assert line.debit == Decimal("10.5")


class TestJournalEntry:
    def _balanced_lines(self):
        return [
            JournalLine(account_id=1, debit=Decimal("100")),
            JournalLine(account_id=2, credit=Decimal("100")),
        ]

    def test_balanced_entry_accepted(self):
        entry = JournalEntry(
            entry_date=date.today(), description="test", lines=self._balanced_lines()
        )
        assert entry.status == JournalStatus.DRAFT
        assert entry.is_balanced is True

    def test_unbalanced_entry_rejected_on_construct(self):
        with pytest.raises(UnbalancedEntryError):
            JournalEntry(
                entry_date=date.today(),
                description="bad",
                lines=[
                    JournalLine(account_id=1, debit=Decimal("100")),
                    JournalLine(account_id=2, credit=Decimal("99")),
                ],
            )

    def test_empty_entry_rejected(self):
        with pytest.raises(UnbalancedEntryError):
            JournalEntry(entry_date=date.today(), description="empty", lines=[])

    def test_post_records_user_and_timestamp(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        assert entry.posted_at is None
        entry.post(posted_by=42)
        assert entry.status == JournalStatus.POSTED
        assert entry.posted_at is not None
        assert entry.posted_by == 42

    def test_post_unbalanced_raises(self):
        # Construct via add_line to keep balanced, then break it
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        # can_post is what it is
        # forcibly mess with internal state to simulate corruption
        entry.lines[0].debit = Decimal("200")  # Now 200 vs 100 → unbalanced
        with pytest.raises(UnbalancedEntryError):
            entry.post(posted_by=1)

    def test_cannot_post_twice(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation):
            entry.post(posted_by=1)

    def test_cannot_add_line_after_post(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation):
            entry.add_line(JournalLine(account_id=3, debit=Decimal("5")))

    def test_reverse_swaps_debit_credit(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        entry.post(posted_by=1)
        reversal = entry.reverse(posted_by=2, reason="error")
        # Original → REVERSED
        assert entry.status == JournalStatus.REVERSED
        # New entry has swapped lines
        assert reversal.status == JournalStatus.POSTED
        assert reversal.reverses_id == entry.id
        # Each line's debit and credit are swapped: original line 0
        # had (acct=1, debit=100, credit=0). Reversed line 0:
        # (acct=1, debit=0, credit=100) — what was credit becomes debit.
        # Reversed line 1: (acct=2, debit=100, credit=0) — what was credit
        # becomes debit.
        # Find lines by account_id to verify the swap unambiguously
        rline1 = next(rl for rl in reversal.lines if rl.account_id == 1)
        rline2 = next(rl for rl in reversal.lines if rl.account_id == 2)
        assert rline1.debit == Decimal("0")  # was credit=0
        assert rline1.credit == Decimal("100")  # was debit=100
        assert rline2.debit == Decimal("100")  # was credit=100
        assert rline2.credit == Decimal("0")  # was debit=0
        # And the reversal still balances
        assert reversal.is_balanced

    def test_reverse_requires_posted(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        with pytest.raises(BusinessRuleViolation):
            entry.reverse(posted_by=1, reason="too early")

    def test_reverse_requires_reason(self):
        entry = JournalEntry(
            entry_date=date.today(), description="x", lines=self._balanced_lines()
        )
        entry.post(posted_by=1)
        with pytest.raises(BusinessRuleViolation):
            entry.reverse(posted_by=1, reason="")
        with pytest.raises(BusinessRuleViolation):
            entry.reverse(posted_by=1, reason="   ")

    def test_total_debit_equals_total_credit(self):
        entry = JournalEntry(
            entry_date=date.today(),
            description="x",
            lines=[
                JournalLine(account_id=1, debit=Decimal("50")),
                JournalLine(account_id=2, debit=Decimal("50")),
                JournalLine(account_id=3, credit=Decimal("100")),
            ],
        )
        assert entry.total_debit == Decimal("100")
        assert entry.total_credit == Decimal("100")


# ============================================================================
# finance.period (accounting period close)
# ============================================================================


class TestAccountingPeriod:
    def test_invalid_month_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            AccountingPeriod(year=2026, month=0)
        with pytest.raises(BusinessRuleViolation):
            AccountingPeriod(year=2026, month=13)

    def test_invalid_year_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            AccountingPeriod(year=1999, month=1)
        with pytest.raises(BusinessRuleViolation):
            AccountingPeriod(year=2200, month=1)

    def test_period_key_format(self):
        p = AccountingPeriod(year=2026, month=3)
        assert p.period_key == "2026-03"

    def test_end_date(self):
        assert AccountingPeriod(year=2026, month=1).end_date == date(2026, 1, 31)
        assert AccountingPeriod(year=2026, month=2).end_date == date(2026, 2, 28)
        assert AccountingPeriod(year=2024, month=2).end_date == date(
            2024, 2, 29
        )  # leap year
        assert AccountingPeriod(year=2026, month=12).end_date == date(2026, 12, 31)

    def test_close_open_period(self):
        p = AccountingPeriod(year=2026, month=1)
        p.close(user_id=42)
        assert p.status == PeriodStatus.CLOSED
        assert p.closed_by == 42
        assert p.closed_at is not None
        assert p.is_closed is True
        # Event emitted
        assert len(p.collect_events()) == 1

    def test_cannot_close_twice(self):
        p = AccountingPeriod(year=2026, month=1)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation):
            p.close(user_id=1)

    def test_assert_open_rejects_closed(self):
        p = AccountingPeriod(year=2026, month=1)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation):
            p.assert_open()

    def test_reopen_requires_reason(self):
        p = AccountingPeriod(year=2026, month=1)
        p.close(user_id=1)
        with pytest.raises(BusinessRuleViolation):
            p.reopen(user_id=1, reason="")
        with pytest.raises(BusinessRuleViolation):
            p.reopen(user_id=1, reason="   ")

    def test_reopen_only_on_closed(self):
        p = AccountingPeriod(year=2026, month=1)
        with pytest.raises(BusinessRuleViolation):
            p.reopen(user_id=1, reason="too early")

    def test_reopen_emits_event(self):
        p = AccountingPeriod(year=2026, month=1)
        p.close(user_id=1)
        # collect closes the close event first
        close_events = p.collect_events()
        assert len(close_events) == 1
        assert close_events[0].event_name == "PeriodClosed"
        # Then reopen emits its own
        p.reopen(user_id=2, reason="audit correction")
        assert p.status == PeriodStatus.REOPENED
        assert p.reopen_reason == "audit correction"
        reopen_events = p.collect_events()
        assert len(reopen_events) == 1
        assert reopen_events[0].event_name == "PeriodReopened"


# ============================================================================
# inventory.batch (FEFO + FIFO allocation)
# ============================================================================


class TestInventoryBatch:
    def _make_batch(self, **kwargs):
        defaults = dict(
            product_id=1,
            warehouse_id=1,
            batch_no="B-001",
            quantity=100,
            received_date=date(2026, 1, 1),
            unit_cost=10.0,
        )
        defaults.update(kwargs)
        return InventoryBatch(**defaults)

    def test_negative_quantity_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            InventoryBatch(
                product_id=1,
                warehouse_id=1,
                batch_no="B",
                quantity=-1,
                received_date=date.today(),
                unit_cost=10.0,
            )

    def test_empty_batch_no_rejected(self):
        with pytest.raises(BusinessRuleViolation):
            InventoryBatch(
                product_id=1,
                warehouse_id=1,
                batch_no="",
                quantity=1,
                received_date=date.today(),
                unit_cost=10.0,
            )

    def test_expiry_must_be_after_manufacture(self):
        with pytest.raises(BusinessRuleViolation):
            InventoryBatch(
                product_id=1,
                warehouse_id=1,
                batch_no="B",
                quantity=1,
                received_date=date.today(),
                unit_cost=10.0,
                manufacture_date=date(2026, 6, 1),
                expiry_date=date(2026, 5, 1),
            )

    def test_available_when_status_available_and_not_expired(self):
        future = date.today() + timedelta(days=30)
        b = self._make_batch(expiry_date=future)
        assert b.is_available is True
        assert b.is_expired is False

    def test_expired_when_past_expiry(self):
        past = date.today() - timedelta(days=1)
        b = self._make_batch(expiry_date=past)
        assert b.is_expired is True
        assert b.is_available is False

    def test_not_available_when_zero_quantity(self):
        b = self._make_batch(quantity=0)
        assert b.is_available is False

    def test_not_available_when_quarantined(self):
        b = self._make_batch(status=BatchStatus.QUARANTINED)
        assert b.is_available is False

    def test_consume_reduces_quantity(self):
        b = self._make_batch(quantity=10)
        b.consume(3)
        assert b.quantity == 7
        assert b.status == BatchStatus.AVAILABLE

    def test_consume_to_zero_marks_consumed(self):
        b = self._make_batch(quantity=5)
        b.consume(5)
        assert b.quantity == 0
        assert b.status == BatchStatus.CONSUMED

    def test_consume_more_than_available_raises(self):
        b = self._make_batch(quantity=5)
        with pytest.raises(BusinessRuleViolation):
            b.consume(10)

    def test_consume_zero_or_negative_raises(self):
        b = self._make_batch(quantity=10)
        with pytest.raises(BusinessRuleViolation):
            b.consume(0)
        with pytest.raises(BusinessRuleViolation):
            b.consume(-1)

    def test_consume_quarantined_raises(self):
        b = self._make_batch(status=BatchStatus.QUARANTINED)
        with pytest.raises(BusinessRuleViolation):
            b.consume(1)

    def test_mark_expired_idempotent(self):
        past = date.today() - timedelta(days=1)
        b = self._make_batch(expiry_date=past)
        assert b.mark_expired() is True
        assert b.status == BatchStatus.EXPIRED
        # Second call is a no-op
        assert b.mark_expired() is False

    def test_mark_expired_only_on_available(self):
        past = date.today() - timedelta(days=1)
        b = self._make_batch(expiry_date=past, status=BatchStatus.QUARANTINED)
        assert b.mark_expired() is False
        assert b.status == BatchStatus.QUARANTINED


class TestFEFOAllocation:
    def test_allocates_from_earliest_expiry(self):
        # Use far-future dates to avoid the test running on/after the expiry
        today = date.today()
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B-001",
            quantity=10,
            received_date=today - timedelta(days=180),
            unit_cost=10.0,
            expiry_date=today + timedelta(days=30),
        )
        b2 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B-002",
            quantity=10,
            received_date=today - timedelta(days=170),
            unit_cost=11.0,
            expiry_date=today + timedelta(days=180),
        )
        result = allocate_fefo([b1, b2], qty=15)
        # Should pull all 10 from b1 (earlier expiry), then 5 from b2
        assert result.is_fully_allocated is True
        assert result.allocations[0].batch_no == "B-001"
        assert result.allocations[0].quantity == 10
        assert result.allocations[1].batch_no == "B-002"
        assert result.allocations[1].quantity == 5

    def test_unfilled_qty_when_insufficient(self):
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B-001",
            quantity=5,
            received_date=date(2026, 1, 1),
            unit_cost=10.0,
        )
        result = allocate_fefo([b1], qty=20)
        assert result.unfilled_qty == 15
        assert result.is_fully_allocated is False

    def test_skips_expired_batches(self):
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="OLD",
            quantity=10,
            received_date=date(2025, 1, 1),
            unit_cost=10.0,
            expiry_date=date(2025, 6, 1),
        )  # expired
        b2 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="FRESH",
            quantity=10,
            received_date=date(2026, 1, 1),
            unit_cost=12.0,
            expiry_date=date(2026, 12, 1),
        )
        result = allocate_fefo([b1, b2], qty=8)
        # Only b2 is available
        assert result.allocations[0].batch_no == "FRESH"
        assert result.allocations[0].quantity == 8

    def test_null_expiry_sorts_last(self):
        today = date.today()
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="WITH-EXP",
            quantity=5,
            received_date=today,
            unit_cost=10.0,
            expiry_date=today + timedelta(days=30),
        )
        b2 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="NO-EXP",
            quantity=5,
            received_date=today,
            unit_cost=10.0,
            expiry_date=None,
        )
        result = allocate_fefo([b1, b2], qty=3)
        # b1 has earlier expiry, should be first
        assert result.allocations[0].batch_no == "WITH-EXP"

    def test_zero_qty_raises(self):
        with pytest.raises(BusinessRuleViolation):
            allocate_fefo([], qty=0)


class TestFIFOByReceived:
    def test_allocates_oldest_received_first(self):
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B-NEW",
            quantity=10,
            received_date=date(2026, 6, 1),
            unit_cost=10.0,
        )
        b2 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B-OLD",
            quantity=10,
            received_date=date(2026, 1, 1),
            unit_cost=10.0,
        )
        result = allocate_fifo_by_received([b1, b2], qty=15)
        assert result.allocations[0].batch_no == "B-OLD"


class TestMarkExpiredBatches:
    def test_marks_only_past_expiry_available_batches(self):
        past = date.today() - timedelta(days=1)
        future = date.today() + timedelta(days=10)
        b1 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="A",
            quantity=1,
            received_date=date(2025, 1, 1),
            unit_cost=10.0,
            expiry_date=past,
        )
        b2 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="B",
            quantity=1,
            received_date=date(2026, 1, 1),
            unit_cost=10.0,
            expiry_date=future,
        )
        b3 = InventoryBatch(
            product_id=1,
            warehouse_id=1,
            batch_no="C",
            quantity=1,
            received_date=date(2025, 1, 1),
            unit_cost=10.0,
            expiry_date=past,
            status=BatchStatus.QUARANTINED,
        )
        count = mark_expired_batches([b1, b2, b3])
        assert count == 1
        assert b1.status == BatchStatus.EXPIRED
        assert b2.status == BatchStatus.AVAILABLE
        assert b3.status == BatchStatus.QUARANTINED


# ============================================================================
# inventory.cost_strategy
# ============================================================================


class TestWeightedAverageCost:
    def test_initial_receipt_uses_incoming_cost(self):
        s = WeightedAverageCost()
        result = s.compute_new_unit_cost(
            current_qty=Decimal("0"),
            current_avg_cost=Decimal("0"),
            incoming_qty=Decimal("100"),
            incoming_unit_cost=Decimal("5.00"),
        )
        assert result == Decimal("5.0000")

    def test_no_new_stock_returns_current(self):
        s = WeightedAverageCost()
        result = s.compute_new_unit_cost(
            current_qty=Decimal("100"),
            current_avg_cost=Decimal("5.00"),
            incoming_qty=Decimal("0"),
            incoming_unit_cost=Decimal("0"),
        )
        assert result == Decimal("5.0000")

    def test_blend_computes_weighted_average(self):
        s = WeightedAverageCost()
        # 100 @ 5.00 + 100 @ 7.00 = 1200 / 200 = 6.00
        result = s.compute_new_unit_cost(
            current_qty=Decimal("100"),
            current_avg_cost=Decimal("5.00"),
            incoming_qty=Decimal("100"),
            incoming_unit_cost=Decimal("7.00"),
        )
        assert result == Decimal("6.0000")

    def test_zero_zero_returns_zero(self):
        s = WeightedAverageCost()
        assert s.compute_new_unit_cost(
            current_qty=Decimal("0"),
            current_avg_cost=Decimal("0"),
            incoming_qty=Decimal("0"),
            incoming_unit_cost=Decimal("0"),
        ) == Decimal("0")

    def test_negative_qty_rejected(self):
        s = WeightedAverageCost()
        with pytest.raises(ValueError):
            s.compute_new_unit_cost(
                current_qty=Decimal("-1"),
                current_avg_cost=Decimal("5"),
                incoming_qty=Decimal("0"),
                incoming_unit_cost=Decimal("0"),
            )

    def test_negative_unit_cost_rejected(self):
        s = WeightedAverageCost()
        with pytest.raises(ValueError):
            s.compute_new_unit_cost(
                current_qty=Decimal("0"),
                current_avg_cost=Decimal("0"),
                incoming_qty=Decimal("1"),
                incoming_unit_cost=Decimal("-1"),
            )


class TestFIFOCost:
    def test_new_batch_uses_incoming_cost(self):
        s = FIFOCost()
        result = s.compute_new_unit_cost(
            current_qty=Decimal("100"),
            current_avg_cost=Decimal("5.00"),
            incoming_qty=Decimal("50"),
            incoming_unit_cost=Decimal("7.00"),
        )
        # FIFO does NOT recompute aggregate; new batch is incoming cost
        assert result == Decimal("7.0000")


class TestStandardCost:
    def test_constructor_rejects_negative(self):
        with pytest.raises(ValueError):
            StandardCost(standard_unit_cost=Decimal("-1"))

    def test_returns_standard_regardless_of_actual(self):
        s = StandardCost(standard_unit_cost=Decimal("5.00"))
        # Actual is wildly different, but standard doesn't care
        result = s.compute_new_unit_cost(
            current_qty=Decimal("0"),
            current_avg_cost=Decimal("0"),
            incoming_qty=Decimal("100"),
            incoming_unit_cost=Decimal("99.99"),
        )
        assert result == Decimal("5.0000")

    def test_compute_variance(self):
        s = StandardCost(standard_unit_cost=Decimal("5.00"))
        # Actual cost was 6.00, so variance is +1.00
        assert s.compute_variance(Decimal("6.00")) == Decimal("1.0000")
        assert s.compute_variance(Decimal("4.00")) == Decimal("-1.0000")


class TestFIFOCostTracker:
    def test_deduct_walks_batches_in_order(self):
        tracker = FIFOCostTracker()
        tracker.add_batch(Decimal("10"), Decimal("5.00"))
        tracker.add_batch(Decimal("5"), Decimal("7.00"))
        total_cogs, consumed = tracker.deduct(Decimal("12"))
        # 10 from batch 1 @ 5.00 = 50.00
        # 2 from batch 2 @ 7.00 = 14.00
        assert total_cogs == Decimal("64.00")
        assert len(consumed) == 2
        assert consumed[0] == (Decimal("10"), Decimal("5.00"))
        assert consumed[1] == (Decimal("2"), Decimal("7.00"))

    def test_deduct_more_than_available_raises(self):
        tracker = FIFOCostTracker()
        tracker.add_batch(Decimal("5"), Decimal("5.00"))
        with pytest.raises(ValueError):
            tracker.deduct(Decimal("10"))

    def test_deduct_zero_or_negative_raises(self):
        tracker = FIFOCostTracker()
        tracker.add_batch(Decimal("5"), Decimal("5.00"))
        with pytest.raises(ValueError):
            tracker.deduct(Decimal("0"))
        with pytest.raises(ValueError):
            tracker.deduct(Decimal("-1"))

    def test_add_zero_batch_raises(self):
        tracker = FIFOCostTracker()
        with pytest.raises(ValueError):
            tracker.add_batch(Decimal("0"), Decimal("5"))

    def test_empty_batches_pruned(self):
        tracker = FIFOCostTracker()
        tracker.add_batch(Decimal("5"), Decimal("5.00"))
        tracker.deduct(Decimal("5"))
        # After full consumption, batch is pruned
        assert tracker._batches == []


class TestCostStrategyFactory:
    def test_weighted_average(self):
        s = make_cost_strategy("weighted_average")
        assert isinstance(s, WeightedAverageCost)

    def test_fifo(self):
        s = make_cost_strategy("fifo")
        assert isinstance(s, FIFOCost)

    def test_standard(self):
        s = make_cost_strategy("standard", standard_unit_cost=Decimal("5"))
        assert isinstance(s, StandardCost)

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            make_cost_strategy("magic")

    def test_standard_without_kwarg_raises(self):
        with pytest.raises(ValueError):
            make_cost_strategy("standard")
