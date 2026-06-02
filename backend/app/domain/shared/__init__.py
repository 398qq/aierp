"""Shared domain — money, exchange rates, common errors."""

from app.domain.shared.errors import (
    BusinessRuleViolation,
    ConcurrentModificationError,
    DomainError,
    InsufficientStockError,
    InvalidStateTransition,
    NotFoundError,
)
from app.domain.shared.events import DomainEvent
from app.domain.shared.money import (
    CurrencyConversionError,
    ExchangeRate,
    ExchangeRateProvider,
    Money,
    SUPPORTED_CURRENCIES,
    build_triangulation,
    convert,
)

__all__ = [
    "DomainError",
    "BusinessRuleViolation",
    "InvalidStateTransition",
    "NotFoundError",
    "InsufficientStockError",
    "ConcurrentModificationError",
    "DomainEvent",
    "Money",
    "ExchangeRate",
    "ExchangeRateProvider",
    "CurrencyConversionError",
    "SUPPORTED_CURRENCIES",
    "convert",
    "build_triangulation",
]
