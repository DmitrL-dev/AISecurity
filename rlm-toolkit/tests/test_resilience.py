"""
Tests for RLM v2.4 Resilience Components.

Tests:
- CircuitBreaker state machine
- CircuitBreakerRegistry
- Metrics collection
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch

from rlm_toolkit.providers.resilience import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_is_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed
        assert not cb.is_open

    def test_successful_calls_stay_closed(self):
        """Successful calls should keep circuit closed."""
        cb = CircuitBreaker("test", failure_threshold=3)

        def success():
            return "ok"

        for _ in range(10):
            result = cb.call(success)
            assert result == "ok"

        assert cb.is_closed
        assert cb.metrics.successful_calls == 10
        assert cb.metrics.failed_calls == 0

    def test_failures_open_circuit(self):
        """Failures exceeding threshold should open circuit."""
        cb = CircuitBreaker("test", failure_threshold=3)

        def failing():
            raise Exception("Error")

        # Fail 3 times to trip circuit
        for i in range(3):
            with pytest.raises(Exception):
                cb.call(failing)

        assert cb.is_open
        assert cb.metrics.failed_calls == 3
        assert cb.metrics.consecutive_failures == 3

    def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls immediately."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=60)

        # Trip the circuit
        for _ in range(2):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        assert cb.is_open

        # Should reject with CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            cb.call(lambda: "should not run")

        assert "test" in str(exc_info.value)
        assert cb.metrics.rejected_calls == 1

    def test_half_open_after_timeout(self):
        """Circuit should become half-open after timeout."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.1)

        # Trip circuit
        for _ in range(2):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        assert cb.is_open

        # Wait for timeout
        time.sleep(0.15)

        # Next call should transition to half-open
        result = cb.call(lambda: "recovered")
        assert result == "recovered"
        # After success it may still be half-open or closed depending on success_threshold

    def test_half_open_success_closes_circuit(self):
        """Successful calls in half-open should close circuit."""
        cb = CircuitBreaker("test", failure_threshold=2,
                            success_threshold=2, reset_timeout=0.1)

        # Trip
        for _ in range(2):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        time.sleep(0.15)

        # Two successes needed
        cb.call(lambda: "ok")
        cb.call(lambda: "ok")

        assert cb.is_closed

    def test_half_open_failure_reopens(self):
        """Failure in half-open should reopen circuit."""
        cb = CircuitBreaker("test", failure_threshold=2, reset_timeout=0.1)

        # Trip
        for _ in range(2):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        time.sleep(0.15)

        # Fail in half-open
        try:
            cb.call(lambda: 1/0)
        except ZeroDivisionError:
            pass

        assert cb.is_open

    def test_excluded_exceptions_not_counted(self):
        """Excluded exceptions should not count as failures."""
        cb = CircuitBreaker("test", failure_threshold=2,
                            excluded_exceptions=(ValueError,))

        def raise_value_error():
            raise ValueError("expected")

        # These should not trip circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                cb.call(raise_value_error)

        assert cb.is_closed
        assert cb.metrics.successful_calls == 5  # Counted as success

    def test_reset_restores_initial_state(self):
        """Reset should restore circuit to initial state."""
        cb = CircuitBreaker("test", failure_threshold=2)

        # Trip circuit
        for _ in range(2):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        assert cb.is_open

        cb.reset()

        assert cb.is_closed
        assert cb.metrics.total_calls == 0

    def test_force_open(self):
        """Force open should open circuit immediately."""
        cb = CircuitBreaker("test")
        assert cb.is_closed

        cb.force_open()
        assert cb.is_open

    def test_force_closed(self):
        """Force closed should close circuit immediately."""
        cb = CircuitBreaker("test", failure_threshold=1)

        try:
            cb.call(lambda: 1/0)
        except ZeroDivisionError:
            pass

        assert cb.is_open

        cb.force_closed()
        assert cb.is_closed

    def test_metrics_calculation(self):
        """Metrics should calculate correctly."""
        cb = CircuitBreaker("test", failure_threshold=10)

        # 7 successes, 3 failures
        for _ in range(7):
            cb.call(lambda: "ok")

        for _ in range(3):
            try:
                cb.call(lambda: 1/0)
            except ZeroDivisionError:
                pass

        metrics = cb.metrics
        assert metrics.total_calls == 10
        assert metrics.successful_calls == 7
        assert metrics.failed_calls == 3
        assert metrics.success_rate == 0.7
        assert metrics.failure_rate == 0.3

    def test_decorator_protect(self):
        """@protect decorator should work."""
        cb = CircuitBreaker("test", failure_threshold=3)

        @cb.protect
        def my_func(x):
            return x * 2

        assert my_func(5) == 10
        assert cb.metrics.successful_calls == 1


class TestCircuitBreakerRegistry:
    """Tests for CircuitBreakerRegistry."""

    def test_get_or_create(self):
        """Should create new breaker or return existing."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("openai", failure_threshold=5)
        cb2 = registry.get_or_create("openai")

        assert cb1 is cb2
        assert cb1.failure_threshold == 5

    def test_get_nonexistent_returns_none(self):
        """get() should return None for nonexistent breaker."""
        registry = CircuitBreakerRegistry()
        assert registry.get("nonexistent") is None

    def test_reset_all(self):
        """reset_all should reset all breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("a", failure_threshold=1)
        cb2 = registry.get_or_create("b", failure_threshold=1)

        # Trip both
        try:
            cb1.call(lambda: 1/0)
        except ZeroDivisionError:
            pass
        try:
            cb2.call(lambda: 1/0)
        except ZeroDivisionError:
            pass

        assert cb1.is_open
        assert cb2.is_open

        registry.reset_all()

        assert cb1.is_closed
        assert cb2.is_closed

    def test_get_all_metrics(self):
        """Should return metrics for all breakers."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("a")
        cb2 = registry.get_or_create("b")

        cb1.call(lambda: "ok")
        cb2.call(lambda: "ok")
        cb2.call(lambda: "ok")

        metrics = registry.get_all_metrics()

        assert "a" in metrics
        assert "b" in metrics
        assert metrics["a"]["total_calls"] == 1
        assert metrics["b"]["total_calls"] == 2


class TestAsyncCircuitBreaker:
    """Tests for async circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_async_call(self):
        """call_async should work with async functions."""
        cb = CircuitBreaker("test")

        async def async_func():
            await asyncio.sleep(0.01)
            return "async result"

        result = await cb.call_async(async_func)
        assert result == "async result"
        assert cb.metrics.successful_calls == 1

    @pytest.mark.asyncio
    async def test_async_failure(self):
        """Async failures should trip circuit."""
        cb = CircuitBreaker("test", failure_threshold=2)

        async def async_fail():
            raise ValueError("async error")

        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call_async(async_fail)

        assert cb.is_open

    @pytest.mark.asyncio
    async def test_async_protect_decorator(self):
        """@protect should work with async functions."""
        cb = CircuitBreaker("test")

        @cb.protect
        async def async_protected(x):
            return x * 3

        result = await async_protected(4)
        assert result == 12


class TestGlobalCircuitBreaker:
    """Tests for global circuit breaker functions."""

    def test_get_circuit_breaker(self):
        """get_circuit_breaker should work."""
        reset_all_circuit_breakers()

        cb = get_circuit_breaker("test_global", failure_threshold=10)
        assert cb.failure_threshold == 10

        cb2 = get_circuit_breaker("test_global")
        assert cb is cb2


class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    def test_zero_failure_threshold(self):
        """Zero threshold should be handled."""
        cb = CircuitBreaker(name="zero", failure_threshold=0)
        # Should still allow calls
        result = cb.call(lambda: "ok")
        assert result == "ok"

    def test_very_large_threshold(self):
        """Large failure threshold should work."""
        cb = CircuitBreaker(name="large", failure_threshold=10000)

        for i in range(100):
            try:
                cb.call(lambda: (_ for _ in ()).throw(ValueError()))
            except ValueError:
                pass

        assert cb.is_closed

    def test_empty_returns(self):
        """Empty/None returns should work."""
        cb = CircuitBreaker(name="empty")

        assert cb.call(lambda: None) is None
        assert cb.call(lambda: "") == ""
        assert cb.call(lambda: 0) == 0
        assert cb.call(lambda: []) == []
        assert cb.call(lambda: {}) == {}

    def test_exception_types_preserved(self):
        """Original exception types should be preserved."""
        cb = CircuitBreaker(name="exc", failure_threshold=10)

        with pytest.raises(TypeError):
            cb.call(lambda: (_ for _ in ()).throw(TypeError("type")))

        with pytest.raises(KeyError):
            cb.call(lambda: (_ for _ in ()).throw(KeyError("key")))

    def test_rapid_transitions(self):
        """Rapid state transitions should be stable."""
        cb = CircuitBreaker(
            name="rapid", failure_threshold=1, reset_timeout=0.01)

        for i in range(10):
            try:
                if i % 2 == 0:
                    cb.call(lambda: (_ for _ in ()).throw(ValueError()))
                else:
                    time.sleep(0.02)
                    cb.call(lambda: "ok")
            except (ValueError, CircuitOpenError):
                pass

    def test_nested_calls(self):
        """Nested circuit breaker calls should work."""
        cb = CircuitBreaker(name="nested", failure_threshold=5)

        def recursive(depth):
            if depth == 0:
                return "done"
            return cb.call(lambda: recursive(depth - 1))

        result = cb.call(lambda: recursive(3))
        assert result == "done"

    def test_concurrent_call_tracking(self):
        """Metrics should track concurrent calls correctly."""
        cb = CircuitBreaker(name="concurrent")

        for _ in range(100):
            cb.call(lambda: "ok")

        assert cb.metrics.successful_calls == 100

    @pytest.mark.asyncio
    async def test_async_with_cancellation(self):
        """Async calls should handle cancellation."""
        cb = CircuitBreaker(name="cancel")

        async def slow_call():
            await asyncio.sleep(10)
            return "done"

        task = asyncio.create_task(cb.call_async(slow_call))
        await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


class TestNegativeScenarios:
    """Negative scenario tests."""

    def test_call_with_none_function(self):
        """Calling with None should raise TypeError."""
        cb = CircuitBreaker(name="none")

        with pytest.raises(TypeError):
            cb.call(None)

    def test_metrics_after_reset(self):
        """Metrics should be zeroed after reset."""
        cb = CircuitBreaker(name="reset_metrics", failure_threshold=5)

        for _ in range(5):
            cb.call(lambda: "ok")

        cb.reset()

        assert cb.metrics.total_calls == 0
        assert cb.metrics.successful_calls == 0

    def test_force_operations(self):
        """Force operations should work in any state."""
        cb = CircuitBreaker(name="force", failure_threshold=2)

        # Force open when closed
        cb.force_open()
        assert cb.is_open

        # Force closed when open
        cb.force_closed()
        assert cb.is_closed

        # Force open again
        cb.force_open()
        assert cb.is_open

    def test_registry_duplicate_names(self):
        """Registry should handle duplicate names correctly."""
        registry = CircuitBreakerRegistry()

        cb1 = registry.get_or_create("dup", failure_threshold=5)
        cb2 = registry.get_or_create("dup", failure_threshold=10)

        # Should return same instance
        assert cb1 is cb2
        # Original threshold preserved
        assert cb1.failure_threshold == 5
