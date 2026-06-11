"""Multi-currency value object — Money + FX conversion.

A `Money` is a (amount, currency) pair. The currency is a 3-letter
ISO 4217 code (CNY, USD, EUR, JPY, HKD, etc.). Arithmetic between
Money values requires FX conversion via the `ExchangeRate` provider.

This module owns the pure conversion math. The FX rate provider
loads rates from a database table (or HTTP API) and caches them.
"""

from dataclasses import dataclass
from datetime import date as date_type
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from app.domain.shared.errors import BusinessRuleViolation


# ISO 4217 currency codes we support out of the box
SUPPORTED_CURRENCIES = frozenset(
    {
        "CNY",
        "USD",
        "EUR",
        "JPY",
        "HKD",
        "GBP",
        "KRW",
        "TWD",
        "SGD",
    }
)


class CurrencyConversionError(BusinessRuleViolation):
    code = "CURRENCY_CONVERSION_ERROR"


@dataclass(frozen=True)
class Money:
    """An amount of money in a specific currency.

    Immutable. Arithmetic operators return new Money. Cross-currency
    operations require an `ExchangeRate` argument.
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            # Coerce floats to Decimal to avoid float drift
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if self.amount < 0:
            raise BusinessRuleViolation("金额不能为负")
        if not self.currency or len(self.currency) != 3:
            raise BusinessRuleViolation(f"无效的货币代码: {self.currency!r}")
        if self.currency.upper() != self.currency:
            # Normalize to upper-case ISO 4217
            object.__setattr__(self, "currency", self.currency.upper())
        if self.currency not in SUPPORTED_CURRENCIES:
            raise BusinessRuleViolation(f"不支持的货币: {self.currency}")

    @property
    def cents(self) -> Decimal:
        """Round to 2 decimal places (or 0 for JPY)."""
        if self.currency == "JPY":
            return self.amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise CurrencyConversionError(
                f"无法直接相加不同货币: {self.currency} + {other.currency}，请先转换"
            )
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise CurrencyConversionError(
                f"无法直接相减不同货币: {self.currency} - {other.currency}"
            )
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, factor: Decimal | int | float) -> "Money":
        if not isinstance(factor, (Decimal, int, float)):
            return NotImplemented
        if factor < 0:
            raise BusinessRuleViolation("乘数不能为负")
        return Money(
            amount=(self.amount * Decimal(str(factor))),
            currency=self.currency,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.currency == other.currency and self.amount == other.amount

    def __lt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise CurrencyConversionError(
                f"无法比较不同货币: {self.currency} vs {other.currency}"
            )
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self < other or self == other

    def __gt__(self, other: "Money") -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return not (self <= other)

    def __ge__(self, other: "Money") -> bool:
        return not (self < other)

    def __hash__(self) -> int:
        return hash((self.cents, self.currency))

    def __str__(self) -> str:
        return f"{self.currency} {self.cents}"

    def __repr__(self) -> str:
        return f"Money({self.cents} {self.currency})"


@dataclass(frozen=True)
class ExchangeRate:
    """A foreign exchange rate for a specific date.

    Convention: `from_currency → to_currency` at `rate`. So if you have
    100 USD and the rate is USD→CNY = 7.20, you get 720 CNY.
    """

    from_currency: str
    to_currency: str
    rate: Decimal
    effective_date: date_type
    source: str = "manual"  # 'manual' | 'api' | 'bank_statement'

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise BusinessRuleViolation("汇率必须为正")
        if self.from_currency == self.to_currency:
            raise BusinessRuleViolation("from 与 to 货币不能相同")
        if self.from_currency not in SUPPORTED_CURRENCIES:
            raise BusinessRuleViolation(f"不支持的源货币: {self.from_currency}")
        if self.to_currency not in SUPPORTED_CURRENCIES:
            raise BusinessRuleViolation(f"不支持的目标货币: {self.to_currency}")

    def convert(self, amount: Money) -> Money:
        if amount.currency != self.from_currency:
            raise CurrencyConversionError(
                f"汇率 {self.from_currency}→{self.to_currency} 不适用于 {amount.currency}"
            )
        converted = (amount.amount * self.rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        return Money(amount=converted, currency=self.to_currency)


class ExchangeRateProvider:
    """In-memory FX rate provider with date-based lookup.

    Production version would load rates from a database table refreshed
    by a daily job, or call an external API (e.g. central bank rates).
    """

    def __init__(self) -> None:
        self._rates: dict[tuple[str, str, date_type], ExchangeRate] = {}

    def add(self, rate: ExchangeRate) -> None:
        self._rates[(rate.from_currency, rate.to_currency, rate.effective_date)] = rate

    def get(
        self,
        from_currency: str,
        to_currency: str,
        at: Optional[date_type] = None,
    ) -> Optional[ExchangeRate]:
        """Look up the most recent rate on or before `at` (default: today)."""
        if from_currency == to_currency:
            return None  # 1:1 — no need
        at = at or date_type.today()
        # Search for the most recent rate on or before `at`
        candidates = [
            (k, v)
            for k, v in self._rates.items()
            if k[0] == from_currency and k[1] == to_currency and k[2] <= at
        ]
        if not candidates:
            return None
        # Return the most recent
        return max(candidates, key=lambda kv: kv[0][2])[1]


def convert(
    amount: Money,
    to_currency: str,
    provider: ExchangeRateProvider,
    at: Optional[date_type] = None,
) -> Money:
    """Convert `amount` to `to_currency` using rates from `provider`.

    Raises CurrencyConversionError if no rate is available.
    """
    if amount.currency == to_currency:
        return amount
    rate = provider.get(amount.currency, to_currency, at)
    if rate is None:
        raise CurrencyConversionError(f"找不到 {amount.currency}→{to_currency} 的汇率")
    return rate.convert(amount)


def build_triangulation(
    provider: ExchangeRateProvider,
    base: str = "CNY",
) -> ExchangeRateProvider:
    """Build a 'triangulated' provider: any pair not directly available
    is computed via base currency (e.g. USD→EUR via USD→CNY × CNY→EUR).

    Useful when the FX feed only publishes rates against a base currency
    (typical for central banks).
    """
    out = ExchangeRateProvider()
    # First, copy direct rates
    for rate in list(provider._rates.values()):
        out.add(rate)

    # Find all rates in the "to base" direction (A → base)
    to_base = [
        v
        for v in provider._rates.values()
        if v.to_currency == base and v.from_currency != base
    ]
    # Find all rates in the "from base" direction (base → B)
    from_base = [
        v
        for v in provider._rates.values()
        if v.from_currency == base and v.to_currency != base
    ]

    # Triangulate: for each A → base and base → B, create A → B
    for r1 in to_base:
        for r2 in from_base:
            a = r1.from_currency
            b = r2.to_currency
            if a == b:
                continue
            new_rate = ExchangeRate(
                from_currency=a,
                to_currency=b,
                rate=(r1.rate * r2.rate).quantize(
                    Decimal("0.000001"), rounding=ROUND_HALF_UP
                ),
                effective_date=max(r1.effective_date, r2.effective_date),
                source="triangulated",
            )
            out.add(new_rate)
    return out
