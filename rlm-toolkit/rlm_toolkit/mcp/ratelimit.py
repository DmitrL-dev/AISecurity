"""
Rate Limiter for RLM MCP Server.

Provides token-bucket rate limiting with exponential backoff.
"""

import time
import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("rlm_mcp.ratelimit")


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 60
    burst_size: int = 10
    backoff_base: float = 1.0
    backoff_max: float = 60.0


class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens per second
            capacity: Maximum tokens (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Returns:
            True if tokens consumed, False if rate limited
        """
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def wait_time(self) -> float:
        """Time to wait before tokens available."""
        self._refill()
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.rate


class RateLimiter:
    """Rate limiter with per-tool limits and backoff."""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, TokenBucket] = {}
        self.backoff_counts: Dict[str, int] = {}
    
    def _get_bucket(self, key: str) -> TokenBucket:
        """Get or create bucket for key."""
        if key not in self.buckets:
            rate = self.config.requests_per_minute / 60.0
            self.buckets[key] = TokenBucket(rate, self.config.burst_size)
        return self.buckets[key]
    
    def check(self, tool_name: str) -> bool:
        """
        Check if request is allowed.
        
        Args:
            tool_name: Name of the tool being called
        
        Returns:
            True if allowed, False if rate limited
        """
        bucket = self._get_bucket(tool_name)
        if bucket.consume():
            self.backoff_counts[tool_name] = 0
            return True
        
        # Rate limited
        self.backoff_counts[tool_name] = self.backoff_counts.get(tool_name, 0) + 1
        logger.warning(f"Rate limited: {tool_name}")
        return False
    
    def get_backoff_time(self, tool_name: str) -> float:
        """Get exponential backoff time."""
        count = self.backoff_counts.get(tool_name, 0)
        backoff = min(
            self.config.backoff_base * (2 ** count),
            self.config.backoff_max
        )
        return backoff
    
    def wait_time(self, tool_name: str) -> float:
        """Time to wait before next request."""
        bucket = self._get_bucket(tool_name)
        return bucket.wait_time()
    
    def reset(self, tool_name: Optional[str] = None):
        """Reset rate limits."""
        if tool_name:
            self.buckets.pop(tool_name, None)
            self.backoff_counts.pop(tool_name, None)
        else:
            self.buckets.clear()
            self.backoff_counts.clear()
    
    def get_stats(self) -> Dict[str, Dict]:
        """Get rate limiter statistics."""
        stats = {}
        for key, bucket in self.buckets.items():
            bucket._refill()
            stats[key] = {
                "tokens": round(bucket.tokens, 2),
                "capacity": bucket.capacity,
                "backoff_count": self.backoff_counts.get(key, 0),
            }
        return stats
