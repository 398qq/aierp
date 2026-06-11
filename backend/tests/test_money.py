"""Tests for Money value object and ExchangeRate conversion."""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.shared import (
    CurrencyConversionError,
    ExchangeRate,
    ExchangeRateProvider,
    Money,
    build_triangulation,
    convert,
)
from app.domain.shared.money import SUPPORTED_CURRENCIES
from app.domain.shared.errors import BusinessRuleViolation


class TestMoneyConstruction:
    def test_basic_construction(self):
        m = Money(amount=Decimal("100.50"), currency="CNY")
        assert m.amount == Decimal("100.50")
        assert m.currency == "CNY"

    def test_normalizes_to_uppercase(self):
        m = Money(amount=Decimal("10"), currency="usd")
        assert m.currency == "USD"

    def test_rejects_negative_amount(self):
        with pytest.raises(BusinessRuleViolation, match="金额不能为负"):
            Money(amount=Decimal("-1"), currency="CNY")

    def test_rejects_empty_currency(self):
        with pytest.raises(BusinessRuleViolation, match="无效的货币代码"):
            Money(amount=Decimal("1"), currency="")

    def test_rejects_short_currency(self):
        with pytest.raises(BusinessRuleViolation, match="无效的货币代码"):
            Money(amount=Decimal("1"), currency="YU")

    def test_rejects_long_currency(self):
        with pytest.raises(BusinessRuleViolation, match="无效的货币代码"):
            Money(amount=Decimal("1"), currency="YUAN")

    def test_rejects_unsupported_currency(self):
        with pytest.raises(BusinessRuleViolation, match="不支持的货币"):
            Money(amount=Decimal("1"), currency="ZZZ")

    def test_coerces_float_to_decimal(self):
        m = Money(amount=0.1, currency="USD")
        # No float drift: 0.1 should be exactly 0.1
        assert m.amount == Decimal("0.1")


class TestMoneyArithmetic:
    def test_add_same_currency(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("50"), currency="CNY")
        result = a + b
        assert result.amount == Decimal("150")
        assert result.currency == "CNY"

    def test_sub_same_currency(self):
        a = Money(amount=Decimal("100"), currency="USD")
        b = Money(amount=Decimal("30"), currency="USD")
        result = a - b
        assert result.amount == Decimal("70")

    def test_add_different_currency_raises(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("100"), currency="USD")
        with pytest.raises(CurrencyConversionError, match="不同货币"):
            _ = a + b

    def test_sub_different_currency_raises(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("100"), currency="USD")
        with pytest.raises(CurrencyConversionError):
            _ = a - b

    def test_multiply_by_positive_factor(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        result = a * 2
        assert result.amount == Decimal("200")
        assert result.currency == "CNY"

    def test_multiply_by_decimal(self):
        a = Money(amount=Decimal("100"), currency="USD")
        result = a * Decimal("1.5")
        assert result.amount == Decimal("150.0")

    def test_multiply_by_zero(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        result = a * 0
        assert result.amount == Decimal("0")

    def test_multiply_by_negative_raises(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        with pytest.raises(BusinessRuleViolation, match="乘数不能为负"):
            _ = a * -1

    def test_equality(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("100"), currency="CNY")
        assert a == b

    def test_inequality_amount(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("200"), currency="CNY")
        assert a != b

    def test_inequality_currency(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("100"), currency="USD")
        assert a != b

    def test_comparison(self):
        a = Money(amount=Decimal("100"), currency="CNY")
        b = Money(amount=Decimal("200"), currency="CNY")
        assert a < b
        assert b > a
        assert a <= b
        assert b >= a
        assert a <= a

    def test_hashable(self):
        a = Money(amount=Decimal("100.50"), currency="CNY")
        b = Money(amount=Decimal("100.50"), currency="CNY")
        s = {a, b}
        assert len(s) == 1  # Equal Money values are deduped

    def test_str_representation(self):
        a = Money(amount=Decimal("123.45"), currency="CNY")
        s = str(a)
        assert "CNY" in s
        assert "123.45" in s


class TestMoneyCentsRounding:
    def test_cny_rounds_to_2_decimals(self):
        a = Money(amount=Decimal("100.456"), currency="CNY")
        assert a.cents == Decimal("100.46")

    def test_jpy_has_no_decimals(self):
        a = Money(amount=Decimal("100.6"), currency="JPY")
        assert a.cents == Decimal("101")  # Round half up

    def test_usd_rounds_to_2_decimals(self):
        a = Money(amount=Decimal("99.999"), currency="USD")
        assert a.cents == Decimal("100.00")


class TestExchangeRate:
    def test_basic_construction(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.20"),
            effective_date=date(2026, 6, 1),
        )
        assert r.rate == Decimal("7.20")

    def test_rejects_zero_rate(self):
        with pytest.raises(BusinessRuleViolation, match="汇率必须为正"):
            ExchangeRate(
                from_currency="USD",
                to_currency="CNY",
                rate=Decimal("0"),
                effective_date=date.today(),
            )

    def test_rejects_negative_rate(self):
        with pytest.raises(BusinessRuleViolation, match="汇率必须为正"):
            ExchangeRate(
                from_currency="USD",
                to_currency="CNY",
                rate=Decimal("-1"),
                effective_date=date.today(),
            )

    def test_rejects_same_currency(self):
        with pytest.raises(BusinessRuleViolation, match="不能相同"):
            ExchangeRate(
                from_currency="USD",
                to_currency="USD",
                rate=Decimal("1"),
                effective_date=date.today(),
            )

    def test_convert_basic(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.20"),
            effective_date=date(2026, 6, 1),
        )
        result = r.convert(Money(amount=Decimal("100"), currency="USD"))
        assert result.currency == "CNY"
        assert result.amount == Decimal("720.00")

    def test_convert_rounds_to_cents(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.2345"),
            effective_date=date(2026, 6, 1),
        )
        result = r.convert(Money(amount=Decimal("10"), currency="USD"))
        # 10 * 7.2345 = 72.345 → rounded to 72.35
        assert result.amount == Decimal("72.35")

    def test_convert_wrong_source_currency_raises(self):
        r = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7"),
            effective_date=date.today(),
        )
        with pytest.raises(CurrencyConversionError):
            r.convert(Money(amount=Decimal("100"), currency="EUR"))


class TestExchangeRateProvider:
    def test_empty_provider_returns_none(self):
        p = ExchangeRateProvider()
        assert p.get("USD", "CNY") is None

    def test_add_and_get_exact_date(self):
        p = ExchangeRateProvider()
        rate = ExchangeRate(
            from_currency="USD",
            to_currency="CNY",
            rate=Decimal("7.20"),
            effective_date=date(2026, 6, 1),
        )
        p.add(rate)
        found = p.get("USD", "CNY", at=date(2026, 6, 1))
        assert found is rate

    def test_get_uses_most_recent_rate_on_or_before(self):
        p = ExchangeRateProvider()
        p.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        p.add(ExchangeRate("USD", "CNY", Decimal("7.2"), date(2026, 3, 1)))
        p.add(ExchangeRate("USD", "CNY", Decimal("7.4"), date(2026, 6, 1)))

        # Ask on June 15 → most recent rate (7.4)
        found = p.get("USD", "CNY", at=date(2026, 6, 15))
        assert found.rate == Decimal("7.4")

        # Ask on Feb 15 → 7.0
        found = p.get("USD", "CNY", at=date(2026, 2, 15))
        assert found.rate == Decimal("7.0")

    def test_get_returns_none_when_no_rate_before_date(self):
        p = ExchangeRateProvider()
        p.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        found = p.get("USD", "CNY", at=date(2025, 12, 31))
        assert found is None

    def test_get_same_currency_returns_none(self):
        p = ExchangeRateProvider()
        # Adding USD→USD would raise (same currency), so we just test
        # the short-circuit in get(): requesting the same currency
        # returns None without consulting the rate table.
        assert p.get("USD", "USD") is None


class TestConvertFunction:
    def test_same_currency_no_op(self):
        p = ExchangeRateProvider()
        m = Money(amount=Decimal("100"), currency="CNY")
        result = convert(m, "CNY", p)
        assert result == m

    def test_uses_provider_rate(self):
        p = ExchangeRateProvider()
        p.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date.today()))
        result = convert(Money(amount=Decimal("100"), currency="USD"), "CNY", p)
        assert result == Money(amount=Decimal("700"), currency="CNY")

    def test_no_rate_raises(self):
        p = ExchangeRateProvider()
        with pytest.raises(CurrencyConversionError, match="找不到"):
            convert(Money(amount=Decimal("100"), currency="USD"), "JPY", p)


class TestBuildTriangulation:
    def test_triangulates_via_base(self):
        # Only have CNY-based rates
        p = ExchangeRateProvider()
        p.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        p.add(ExchangeRate("CNY", "EUR", Decimal("0.13"), date(2026, 1, 1)))

        # Build triangulation — should derive USD→EUR via CNY
        out = build_triangulation(p, base="CNY")
        usd_eur = out.get("USD", "EUR", at=date(2026, 1, 1))
        assert usd_eur is not None
        # 7.0 * 0.13 = 0.91
        assert usd_eur.rate == Decimal("0.910000")
        assert usd_eur.source == "triangulated"

    def test_no_op_when_target_currency_same_as_source(self):
        p = ExchangeRateProvider()
        p.add(ExchangeRate("USD", "CNY", Decimal("7.0"), date(2026, 1, 1)))
        out = build_triangulation(p, base="CNY")
        # USD→CNY is a direct rate, not a triangulation
        usd_cny = out.get("USD", "CNY", at=date(2026, 1, 1))
        assert usd_cny.source == "manual"  # Original source

    def test_empty_provider(self):
        p = ExchangeRateProvider()
        out = build_triangulation(p, base="CNY")
        assert out.get("USD", "EUR") is None


class TestSupportedCurrencies:
    def test_chinese_yuan_included(self):
        assert "CNY" in SUPPORTED_CURRENCIES

    def test_usd_included(self):
        assert "USD" in SUPPORTED_CURRENCIES

    def test_jpy_included(self):
        assert "JPY" in SUPPORTED_CURRENCIES

    def test_eur_included(self):
        assert "EUR" in SUPPORTED_CURRENCIES
