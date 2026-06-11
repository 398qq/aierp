"""Tests for the self-contained circuit breaker (async-safe, no deps)."""

import time

import pytest

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    call_with_breaker,
    get_breaker,
    list_breakers,
    protected,
)


class TestCircuitBreakerBasics:
    def test_initial_state_is_closed(self):
        b = CircuitBreaker(name="test", fail_max=3)
        assert b.state == CircuitState.CLOSED
        assert b.is_call_permitted() is True

    def test_name_preserved(self):
        b = CircuitBreaker(name="custom_name")
        assert b.name == "custom_name"

    def test_repr_includes_state(self):
        b = CircuitBreaker(name="x")
        s = repr(b)
        assert "x" in s
        assert "closed" in s


class TestCircuitBreakerStateTransitions:
    def test_opens_after_fail_max_consecutive_failures(self):
        b = CircuitBreaker(name="t", fail_max=3)
        for _ in range(3):
            b.record_failure()
        assert b.state == CircuitState.OPEN
        assert b.is_call_permitted() is False

    def test_does_not_open_below_fail_max(self):
        b = CircuitBreaker(name="t", fail_max=5)
        for _ in range(4):
            b.record_failure()
        assert b.state == CircuitState.CLOSED

    def test_success_resets_failure_count_in_closed(self):
        b = CircuitBreaker(name="t", fail_max=3)
        b.record_failure()
        b.record_failure()
        b.record_success()
        assert b._consecutive_failures == 0
        b.record_failure()
        b.record_failure()
        # Only 2 consecutive — not yet open
        assert b.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_reset_timeout(self):
        b = CircuitBreaker(name="t", fail_max=2, reset_timeout=0.1)
        b.record_failure()
        b.record_failure()
        assert b.state == CircuitState.OPEN
        time.sleep(0.15)
        assert b.state == CircuitState.HALF_OPEN

    def test_half_open_allows_calls(self):
        b = CircuitBreaker(name="t", fail_max=1, reset_timeout=0.05)
        b.record_failure()
        time.sleep(0.1)
        assert b.state == CircuitState.HALF_OPEN
        assert b.is_call_permitted() is True

    def test_half_open_successes_close_circuit(self):
        b = CircuitBreaker(
            name="t", fail_max=1, reset_timeout=0.05, success_threshold=2
        )
        b.record_failure()
        time.sleep(0.1)
        assert b.state == CircuitState.HALF_OPEN
        b.record_success()
        assert b.state == CircuitState.HALF_OPEN  # need 2 successes
        b.record_success()
        assert b.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        b = CircuitBreaker(name="t", fail_max=1, reset_timeout=0.05)
        b.record_failure()
        time.sleep(0.1)
        assert b.state == CircuitState.HALF_OPEN
        b.record_failure()
        assert b.state == CircuitState.OPEN


class TestCircuitBreakerAdminOperations:
    def test_force_close(self):
        b = CircuitBreaker(name="t", fail_max=1)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        b.force_close()
        assert b.state == CircuitState.CLOSED
        assert b.failure_count == 0

    def test_force_open_for_maintenance(self):
        b = CircuitBreaker(name="t")
        assert b.state == CircuitState.CLOSED
        b.force_open()
        assert b.state == CircuitState.OPEN


class TestRegistry:
    def test_known_breakers(self):
        assert get_breaker("ai").name == "ai_provider"
        assert get_breaker("ocr").name == "ocr_service"
        assert get_breaker("notification").name == "notification_service"
        assert get_breaker("logistics").name == "logistics_service"

    def test_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown breaker"):
            get_breaker("nonexistent")

    def test_list_includes_all(self):
        names = list_breakers()
        assert set(names) == {"ai", "ocr", "notification", "logistics"}


class TestCallWithBreaker:
    async def test_successful_call_passes_through(self):
        async def good() -> str:
            return "ok"

        result = await call_with_breaker("ai", good)
        assert result == "ok"

    async def test_fallback_used_when_circuit_open(self):
        b = get_breaker("ai")
        b.force_open()  # Open the circuit
        try:

            async def would_fail() -> str:
                return "should_not_run"

            result = await call_with_breaker(
                "ai", would_fail, fallback=lambda: "fallback_result"
            )
            assert result == "fallback_result"
        finally:
            b.force_close()

    async def test_no_fallback_raises_circuit_open_error(self):
        b = get_breaker("ai")
        b.force_open()
        try:

            async def any_func() -> None:
                pass

            with pytest.raises(CircuitOpenError, match="circuit open"):
                await call_with_breaker("ai", any_func)
        finally:
            b.force_close()

    async def test_failures_trip_circuit(self):
        b = get_breaker("ocr")  # fail_max=10
        b.force_close()  # reset

        async def failing() -> None:
            raise ConnectionError("upstream down")

        # fail_max=10 → 10 failures needed
        for _ in range(10):
            with pytest.raises(ConnectionError):
                await call_with_breaker("ocr", failing)

        # After 10 failures circuit should be open
        assert b.state == CircuitState.OPEN

        # Restore
        b.force_close()

    async def test_success_resets_failure_count(self):
        b = get_breaker("notification")  # fail_max=20
        b.force_close()

        async def fail() -> None:
            raise ConnectionError()

        async def succeed() -> str:
            return "ok"

        # 3 failures
        for _ in range(3):
            with pytest.raises(ConnectionError):
                await call_with_breaker("notification", fail)
        assert b._consecutive_failures == 3

        # 1 success
        await call_with_breaker("notification", succeed)
        assert b._consecutive_failures == 0


class TestProtectedDecorator:
    async def test_decorator_works(self):
        @protected("ai", fallback=lambda: "fb")
        async def my_func() -> str:
            return "real"

        result = await my_func()
        assert result == "real"

    async def test_decorator_falls_back_when_open(self):
        b = get_breaker("ai")
        b.force_open()
        try:

            @protected("ai", fallback=lambda: "fallback")
            async def would_fail() -> str:
                raise ConnectionError()

            result = await would_fail()
            assert result == "fallback"
        finally:
            b.force_close()


class TestCircuitOpenError:
    def test_message_includes_service(self):
        err = CircuitOpenError("ai", "circuit open after 5 failures")
        assert "ai" in str(err)
        assert "circuit open" in str(err)
        assert err.service == "ai"

    def test_is_exception(self):
        assert issubclass(CircuitOpenError, Exception)
