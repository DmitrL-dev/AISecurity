"""
SENTINEL Brain - Circuit Breaker & Resilience

Implements circuit breaker pattern for fault tolerance.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject requests
    HALF_OPEN = "half_open" # Testing if recovered


@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5        # Failures before opening
    success_threshold: int = 3        # Successes to close
    timeout: float = 30.0             # Seconds before half-open
    half_open_max_calls: int = 3      # Max calls in half-open


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    failures: int = 0
    successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    total_calls: int = 0
    rejected_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit broken, requests fail fast
    - HALF_OPEN: Testing, limited requests allowed
    """
    
    def __init__(self, name: str, config: CircuitConfig = None):
        self.name = name
        self.config = config or CircuitConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
    
    def _should_try(self) -> bool:
        """Check if request should be attempted."""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.stats.last_failure_time:
                elapsed = time.time() - self.stats.last_failure_time
                if elapsed >= self.config.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"Circuit {self.name}: OPEN -> HALF_OPEN")
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def _record_success(self) -> None:
        """Record successful call."""
        self.stats.successes += 1
        self.stats.consecutive_successes += 1
        self.stats.consecutive_failures = 0
        
        if self.state == CircuitState.HALF_OPEN:
            if self.stats.consecutive_successes >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                logger.info(f"Circuit {self.name}: HALF_OPEN -> CLOSED")
    
    def _record_failure(self) -> None:
        """Record failed call."""
        self.stats.failures += 1
        self.stats.consecutive_failures += 1
        self.stats.consecutive_successes = 0
        self.stats.last_failure_time = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.stats.consecutive_failures >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name}: CLOSED -> OPEN")
        
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name}: HALF_OPEN -> OPEN")
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Raises:
            CircuitOpenError: If circuit is open
        """
        async with self._lock:
            self.stats.total_calls += 1
            
            if not self._should_try():
                self.stats.rejected_calls += 1
                raise CircuitOpenError(f"Circuit {self.name} is OPEN")
            
            if self.state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            async with self._lock:
                self._record_success()
            
            return result
            
        except Exception:
            async with self._lock:
                self._record_failure()
            raise
    
    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failures": self.stats.failures,
            "successes": self.stats.successes,
            "consecutive_failures": self.stats.consecutive_failures,
            "total_calls": self.stats.total_calls,
            "rejected_calls": self.stats.rejected_calls,
        }


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


# Retry with exponential backoff

T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    **kwargs,
) -> T:
    """
    Retry async function with exponential backoff.
    
    Args:
        func: Async function to call
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        
    Returns:
        Function result
        
    Raises:
        Exception: Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
                
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                break
            
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {e}"
            )
            await asyncio.sleep(delay)
    
    raise last_exception


def circuit_breaker(name: str, config: CircuitConfig = None):
    """
    Decorator for circuit breaker protection.
    
    Usage:
        @circuit_breaker("external_api")
        async def call_api():
            ...
    """
    breaker = CircuitBreaker(name, config)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        wrapper.circuit = breaker
        return wrapper
    
    return decorator


# Fallback strategies

async def with_fallback(
    primary: Callable,
    fallback: Callable,
    *args,
    **kwargs,
) -> Any:
    """
    Execute primary function with fallback on failure.
    
    Args:
        primary: Primary function to try
        fallback: Fallback function if primary fails
        
    Returns:
        Result from primary or fallback
    """
    try:
        if asyncio.iscoroutinefunction(primary):
            return await primary(*args, **kwargs)
        return primary(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Primary failed, using fallback: {e}")
        if asyncio.iscoroutinefunction(fallback):
            return await fallback(*args, **kwargs)
        return fallback(*args, **kwargs)
