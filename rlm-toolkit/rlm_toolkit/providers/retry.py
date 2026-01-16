"""
Retry Configuration
===================

Retry and backoff configuration for provider resilience.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Set, Type, Union


@dataclass
class RetryConfig:
    """Configuration for retry behavior.
    
    Implements exponential backoff with jitter for resilient API calls.
    
    Example:
        >>> config = RetryConfig(max_retries=3, initial_delay=1.0)
        >>> # Uses exponential backoff: 1s, 2s, 4s
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay cap (seconds)
        exponential_base: Base for exponential backoff
        jitter: Random jitter factor (0-1)
        retry_on: Exception types to retry
        retry_status_codes: HTTP status codes to retry
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.1
    retry_on: Set[Type[Exception]] = field(default_factory=lambda: {
        ConnectionError,
        TimeoutError,
        OSError,
    })
    retry_status_codes: Set[int] = field(default_factory=lambda: {
        429,  # Too Many Requests
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    })
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter
        if self.jitter > 0:
            jitter_range = delay * self.jitter
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def should_retry(self, exception: Exception, status_code: Optional[int] = None) -> bool:
        """Check if exception/status code should trigger retry.
        
        Args:
            exception: The exception that occurred
            status_code: HTTP status code if available
        
        Returns:
            True if should retry
        """
        # Check status code
        if status_code is not None and status_code in self.retry_status_codes:
            return True
        
        # Check exception type
        for exc_type in self.retry_on:
            if isinstance(exception, exc_type):
                return True
        
        return False


class Retrier:
    """Executes functions with retry logic.
    
    Example:
        >>> retrier = Retrier(RetryConfig(max_retries=3))
        >>> result = retrier.execute(my_api_call)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs
    ):
        """Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            on_retry: Callback called before each retry (attempt, exception, delay)
            **kwargs: Keyword arguments for func
        
        Returns:
            Function result
        
        Raises:
            Last exception if all retries exhausted
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Check if we should retry
                status_code = getattr(e, 'status_code', None)
                if not self.config.should_retry(e, status_code):
                    raise
                
                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    raise
                
                # Calculate delay
                delay = self.config.get_delay(attempt)
                
                # Callback
                if on_retry:
                    on_retry(attempt + 1, e, delay)
                
                # Wait
                time.sleep(delay)
        
        # Should not reach here
        raise last_exception  # type: ignore
    
    async def aexecute(
        self,
        func: Callable,
        *args,
        on_retry: Optional[Callable[[int, Exception, float], None]] = None,
        **kwargs
    ):
        """Async version of execute."""
        import asyncio
        
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                status_code = getattr(e, 'status_code', None)
                if not self.config.should_retry(e, status_code):
                    raise
                
                if attempt >= self.config.max_retries:
                    raise
                
                delay = self.config.get_delay(attempt)
                
                if on_retry:
                    on_retry(attempt + 1, e, delay)
                
                await asyncio.sleep(delay)
        
        raise last_exception  # type: ignore


# Default configurations for common providers
OPENAI_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    retry_status_codes={429, 500, 502, 503, 504, 520, 524},
)

ANTHROPIC_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    retry_status_codes={429, 500, 502, 503, 529},  # 529 = overloaded
)

OLLAMA_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    initial_delay=0.5,
    max_delay=10.0,
)
