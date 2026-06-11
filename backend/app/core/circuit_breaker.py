"""Circuit breaker — protect the system from cascading failures.

When an external service (AI, SMS gateway, OCR, payment processor)
starts failing, repeated retries can take down our request threads.
A circuit breaker monitors failure rates and "opens" the circuit
to short-circuit calls to the failing service, returning a fast
fallback while the service recovers.

States:
- CLOSED:    normal operation, calls pass through
- OPEN:      service is failing, calls fail fast
- HALF_OPEN: testing recovery, one trial call allowed

This is a self-contained async-safe implementation (no tornado
dependency). Uses a sliding failure counter with a reset window.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Awaitable, Callable, Deque, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Self-contained async-safe circuit breaker.

    Args:
        name: Identifier for logging/metrics
        fail_max: Consecutive failures before opening the circuit
        reset_timeout: Seconds before transitioning OPEN → HALF_OPEN
        success_threshold: Successful trials in HALF_OPEN to close
    """

    name: str
    fail_max: int = 5
    reset_timeout: float = 60.0
    success_threshold: int = 2
    _failures: Deque[float] = field(default_factory=deque, init=False, repr=False)
    _consecutive_failures: int = field(default=0, init=False, repr=False)
    _consecutive_successes: int = field(default=0, init=False, repr=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _opened_at: Optional[float] = field(default=None, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        """Current state — transitions OPEN→HALF_OPEN after reset_timeout."""
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.reset_timeout:
                # Side-effect: persist the transition so subsequent
                # record_failure() knows we're in HALF_OPEN.
                self._state = CircuitState.HALF_OPEN
                self._consecutive_successes = 0
                logger.info("Circuit breaker '%s' → HALF_OPEN (trial)", self.name)
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        return len(self._failures)

    def is_call_permitted(self) -> bool:
        """Check if a call should be allowed through."""
        s = self.state
        if s == CircuitState.CLOSED:
            return True
        if s == CircuitState.HALF_OPEN:
            return True  # Single trial call allowed
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        self._consecutive_failures = 0
        self._consecutive_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            if self._consecutive_successes >= self.success_threshold:
                logger.info("Circuit breaker '%s' CLOSED after recovery", self.name)
                self._state = CircuitState.CLOSED
                self._opened_at = None
                self._failures.clear()
        elif self._state == CircuitState.CLOSED:
            # Reset the failure window on success
            self._failures.clear()

    def record_failure(self) -> None:
        """Record a failed call."""
        self._consecutive_successes = 0
        self._consecutive_failures += 1
        self._failures.append(time.monotonic())

        if self._state == CircuitState.HALF_OPEN:
            # Trial failed → back to OPEN
            logger.warning(
                "Circuit breaker '%s' re-OPENED after trial failure", self.name
            )
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
        elif self._state == CircuitState.CLOSED:
            if self._consecutive_failures >= self.fail_max:
                logger.warning(
                    "Circuit breaker '%s' OPENED after %d consecutive failures",
                    self.name,
                    self._consecutive_failures,
                )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def force_close(self) -> None:
        """Admin: manually close the circuit (e.g. after fix deployed)."""
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._failures.clear()
        self._consecutive_failures = 0

    def force_open(self) -> None:
        """Admin: manually open the circuit for maintenance."""
        self._state = CircuitState.OPEN
        self._opened_at = time.monotonic()

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self.state.value}, "
            f"failures={self.failure_count})"
        )


class CircuitOpenError(Exception):
    """Raised when a circuit is open — service is unreachable."""

    def __init__(self, service: str, message: str = "circuit open") -> None:
        super().__init__(f"{service}: {message}")
        self.service = service


# ────────────────────────────────────────────────────────────────────────
# Pre-configured breakers for known external dependencies
# ────────────────────────────────────────────────────────────────────────

ai_breaker = CircuitBreaker(name="ai_provider", fail_max=5, reset_timeout=60)
ocr_breaker = CircuitBreaker(name="ocr_service", fail_max=10, reset_timeout=30)
notification_breaker = CircuitBreaker(
    name="notification_service", fail_max=20, reset_timeout=30
)
logistics_breaker = CircuitBreaker(
    name="logistics_service", fail_max=5, reset_timeout=120
)

_REGISTRY: dict[str, CircuitBreaker] = {
    "ai": ai_breaker,
    "ocr": ocr_breaker,
    "notification": notification_breaker,
    "logistics": logistics_breaker,
}


def get_breaker(name: str) -> CircuitBreaker:
    """Look up a pre-configured breaker by short name."""
    if name not in _REGISTRY:
        raise KeyError(f"Unknown breaker: {name!r}. Known: {list(_REGISTRY)}")
    return _REGISTRY[name]


def list_breakers() -> list[str]:
    return list(_REGISTRY.keys())


# ────────────────────────────────────────────────────────────────────────
# Async wrapper + decorator
# ────────────────────────────────────────────────────────────────────────


async def call_with_breaker(
    name: str,
    func: Callable[..., Awaitable[T]],
    *args,
    fallback: Optional[Callable[[], T]] = None,
    **kwargs,
) -> T:
    """Call an async function through a named circuit breaker.

    If the circuit is open, returns the result of `fallback()` if
    provided, otherwise raises CircuitOpenError.

    On function failure, records the failure with the breaker
    (which may trip the circuit if the failure rate is high).
    """
    breaker = get_breaker(name)
    if not breaker.is_call_permitted():
        logger.warning("Circuit breaker '%s' is OPEN — failing fast", name)
        if fallback is not None:
            return fallback()
        raise CircuitOpenError(name, "circuit open")

    try:
        result = await func(*args, **kwargs)
    except Exception:
        breaker.record_failure()
        raise
    else:
        breaker.record_success()
        return result


def protected(
    name: str,
    fallback: Optional[Callable[[], T]] = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator: protect an async function with a named circuit breaker.

    Usage:
        @protected("ai", fallback=lambda: default_response())
        async def call_ai(...):
            ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await call_with_breaker(
                name, func, *args, fallback=fallback, **kwargs
            )

        return wrapper

    return decorator
