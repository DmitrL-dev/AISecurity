"""
Rate Limiter
============

Token bucket rate limiting for provider API calls.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RateLimitConfig:
    """Rate limit configuration.
    
    Uses token bucket algorithm.
    
    Attributes:
        requests_per_minute: Maximum requests per minute
        tokens_per_minute: Maximum tokens per minute (optional)
        burst_size: Maximum burst size
    """
    requests_per_minute: int = 60
    tokens_per_minute: Optional[int] = None
    burst_size: int = 10


class TokenBucket:
    """Token bucket rate limiter.
    
    Thread-safe implementation.
    
    Example:
        >>> bucket = TokenBucket(rate=10, capacity=20)  # 10 tokens/sec, 20 max
        >>> if bucket.acquire():
        ...     make_request()
    """
    
    def __init__(self, rate: float, capacity: float):
        """Initialize bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def acquire(self, tokens: float = 1.0, block: bool = True, timeout: float = 60.0) -> bool:
        """Acquire tokens from bucket.
        
        Args:
            tokens: Number of tokens to acquire
            block: If True, wait for tokens
            timeout: Maximum wait time (seconds)
        
        Returns:
            True if tokens acquired, False if timed out
        """
        start = time.time()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
            
            if not block:
                return False
            
            # Check timeout
            if time.time() - start > timeout:
                return False
            
            # Wait and retry
            wait_time = (tokens - self.tokens) / self.rate
            time.sleep(min(wait_time, 0.1))
    
    @property
    def available(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """Rate limiter for providers.
    
    Manages rate limits per provider with request and token quotas.
    
    Example:
        >>> limiter = RateLimiter()
        >>> limiter.configure("openai", RateLimitConfig(requests_per_minute=60))
        >>> limiter.acquire("openai")  # Blocks if rate limited
    """
    
    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
    
    def configure(self, provider: str, config: RateLimitConfig) -> None:
        """Configure rate limits for provider.
        
        Args:
            provider: Provider name
            config: Rate limit configuration
        """
        # Requests per minute -> requests per second
        rate = config.requests_per_minute / 60.0
        capacity = config.burst_size
        
        with self._lock:
            self._buckets[provider] = TokenBucket(rate=rate, capacity=capacity)
            
            # Token limit if configured
            if config.tokens_per_minute:
                token_rate = config.tokens_per_minute / 60.0
                self._token_buckets[provider] = TokenBucket(
                    rate=token_rate,
                    capacity=config.tokens_per_minute,
                )
    
    def acquire(
        self,
        provider: str,
        tokens: int = 0,
        block: bool = True,
        timeout: float = 60.0,
    ) -> bool:
        """Acquire permission for request.
        
        Args:
            provider: Provider name
            tokens: Estimated token count (for token rate limiting)
            block: If True, wait for permission
            timeout: Maximum wait time
        
        Returns:
            True if acquired, False if timed out/would block
        """
        # Request rate limit
        if provider in self._buckets:
            if not self._buckets[provider].acquire(1.0, block, timeout):
                return False
        
        # Token rate limit
        if tokens > 0 and provider in self._token_buckets:
            if not self._token_buckets[provider].acquire(float(tokens), block, timeout):
                return False
        
        return True
    
    def get_wait_time(self, provider: str) -> float:
        """Estimate wait time for next request.
        
        Args:
            provider: Provider name
        
        Returns:
            Estimated wait time in seconds
        """
        if provider not in self._buckets:
            return 0.0
        
        bucket = self._buckets[provider]
        if bucket.available >= 1.0:
            return 0.0
        
        return (1.0 - bucket.available) / bucket.rate


# Default rate limits per provider (conservative)
DEFAULT_RATE_LIMITS: Dict[str, RateLimitConfig] = {
    "openai": RateLimitConfig(requests_per_minute=60, burst_size=10),
    "anthropic": RateLimitConfig(requests_per_minute=60, burst_size=10),
    "google": RateLimitConfig(requests_per_minute=60, burst_size=10),
    "ollama": RateLimitConfig(requests_per_minute=120, burst_size=20),  # Local, more permissive
}


# Global rate limiter instance
_global_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RateLimiter()
        # Configure defaults
        for provider, config in DEFAULT_RATE_LIMITS.items():
            _global_limiter.configure(provider, config)
    return _global_limiter
