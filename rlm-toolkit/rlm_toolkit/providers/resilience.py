"""
Circuit Breaker Pattern for LLM Provider Resilience.

Implements the circuit breaker pattern to protect against cascade failures
when LLM providers become unavailable or unreliable.

States:
    CLOSED: Normal operation, requests pass through
    OPEN: Circuit has tripped, requests fail immediately
    HALF_OPEN: Testing if provider has recovered

Usage:
    >>> breaker = CircuitBreaker(failure_threshold=5, reset_timeout=60)
    >>> result = breaker.call(llm.generate, prompt)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""

    def __init__(self, breaker_name: str, remaining_seconds: float):
        self.breaker_name = breaker_name
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit '{breaker_name}' is OPEN. "
            f"Retry after {remaining_seconds:.1f}s"
        )


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "state_changes": self.state_changes,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
        }


T = TypeVar('T')


class CircuitBreaker:
    """Circuit breaker for LLM provider resilience.

    Protects against cascade failures by tracking errors and temporarily
    blocking requests when a provider becomes unreliable.

    Args:
        name: Identifier for this circuit breaker
        failure_threshold: Number of failures before opening circuit
        success_threshold: Number of successes in half-open to close
        reset_timeout: Seconds to wait before trying half-open
        excluded_exceptions: Exception types that don't count as failures

    Example:
        >>> breaker = CircuitBreaker("openai", failure_threshold=5)
        >>> 
        >>> # Sync usage
        >>> result = breaker.call(openai.complete, prompt)
        >>> 
        >>> # Async usage
        >>> result = await breaker.call_async(openai.acomplete, prompt)
        >>> 
        >>> # Decorator usage
        >>> @breaker.protect
        >>> def my_llm_call(prompt):
        ...     return provider.generate(prompt)
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        success_threshold: int = 2,
        reset_timeout: float = 60.0,
        excluded_exceptions: tuple = (),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.reset_timeout = reset_timeout
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing)."""
        return self._state == CircuitState.HALF_OPEN

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics."""
        return self._metrics

    def _should_try_half_open(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self._last_failure_time is None:
            return True
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self.reset_timeout

    def _remaining_timeout(self) -> float:
        """Get remaining seconds until half-open attempt."""
        if self._last_failure_time is None:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.reset_timeout - elapsed)

    def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit state and record metrics."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._metrics.state_changes += 1
            self._metrics.last_state_change_time = time.time()
            logger.info(
                f"CircuitBreaker '{self.name}': {old_state.value} → {new_state.value}"
            )

    def _on_success(self) -> None:
        """Record successful call."""
        self._metrics.total_calls += 1
        self._metrics.successful_calls += 1
        self._metrics.last_success_time = time.time()
        self._metrics.consecutive_failures = 0
        self._metrics.consecutive_successes += 1

        if self._state == CircuitState.HALF_OPEN:
            if self._metrics.consecutive_successes >= self.success_threshold:
                self._change_state(CircuitState.CLOSED)

    def _on_failure(self) -> None:
        """Record failed call."""
        self._metrics.total_calls += 1
        self._metrics.failed_calls += 1
        self._metrics.last_failure_time = time.time()
        self._last_failure_time = time.time()
        self._metrics.consecutive_failures += 1
        self._metrics.consecutive_successes = 0

        if self._state == CircuitState.HALF_OPEN:
            # Failure in half-open → back to open
            self._change_state(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._metrics.consecutive_failures >= self.failure_threshold:
                self._change_state(CircuitState.OPEN)

    def _on_rejected(self) -> None:
        """Record rejected call (circuit open)."""
        self._metrics.rejected_calls += 1

    def _pre_call(self) -> None:
        """Pre-call check - raise if circuit is open."""
        if self._state == CircuitState.OPEN:
            if self._should_try_half_open():
                self._change_state(CircuitState.HALF_OPEN)
            else:
                self._on_rejected()
                raise CircuitOpenError(self.name, self._remaining_timeout())

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function through circuit breaker (sync).

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception from function
        """
        self._pre_call()

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.excluded_exceptions:
            # Don't count excluded exceptions as failures
            self._on_success()
            raise
        except Exception:
            self._on_failure()
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception from function
        """
        async with self._lock:
            self._pre_call()

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                self._on_success()
            return result
        except self.excluded_exceptions:
            async with self._lock:
                self._on_success()
            raise
        except Exception:
            async with self._lock:
                self._on_failure()
            raise

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with circuit breaker.

        Example:
            >>> @breaker.protect
            >>> def my_llm_call(prompt):
            ...     return provider.generate(prompt)
        """
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._last_failure_time = None
        self._metrics = CircuitBreakerMetrics()
        logger.info(f"CircuitBreaker '{self.name}': Reset to CLOSED")

    def force_open(self) -> None:
        """Force circuit to open state (for testing/maintenance)."""
        self._change_state(CircuitState.OPEN)
        self._last_failure_time = time.time()

    def force_closed(self) -> None:
        """Force circuit to closed state."""
        self._change_state(CircuitState.CLOSED)


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Provides a centralized way to manage circuit breakers for
    different providers or operations.

    Example:
        >>> registry = CircuitBreakerRegistry()
        >>> openai_breaker = registry.get_or_create("openai")
        >>> anthropic_breaker = registry.get_or_create("anthropic")
    """

    def __init__(self, default_config: Optional[Dict[str, Any]] = None):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = default_config or {}

    def get_or_create(
        self,
        name: str,
        **kwargs
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one.

        Args:
            name: Circuit breaker name
            **kwargs: CircuitBreaker constructor arguments

        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            config = {**self._default_config, **kwargs}
            self._breakers[name] = CircuitBreaker(name=name, **config)
        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def all(self) -> Dict[str, CircuitBreaker]:
        """Get all circuit breakers."""
        return dict(self._breakers)

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {
            name: breaker.metrics.to_dict()
            for name, breaker in self._breakers.items()
        }


# Global registry for convenience
_default_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker from the default registry.

    Args:
        name: Circuit breaker name (usually provider name)
        **kwargs: CircuitBreaker configuration

    Returns:
        CircuitBreaker instance

    Example:
        >>> breaker = get_circuit_breaker("openai", failure_threshold=3)
        >>> result = breaker.call(openai.complete, prompt)
    """
    return _default_registry.get_or_create(name, **kwargs)


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all circuit breakers from default registry."""
    return _default_registry.all()


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers in default registry."""
    _default_registry.reset_all()
