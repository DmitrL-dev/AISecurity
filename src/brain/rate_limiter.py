"""
SENTINEL Rate Limiter — Production-Grade Request Throttling

Implements token bucket algorithm with:
- Per-user rate limits
- Per-IP rate limits
- Burst allowance
- Automatic cleanup

Usage:
    limiter = RateLimiter(requests_per_minute=60)
    
    if limiter.allow("user_123"):
        process_request()
    else:
        return 429  # Too Many Requests

Author: SENTINEL Team
Date: 2025-12-13
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("RateLimiter")


# ============================================================================
# Token Bucket Algorithm
# ============================================================================


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Allows burst traffic while enforcing average rate.
    """
    capacity: float  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(default=0.0)
    last_update: float = field(default_factory=time.time)

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns True if allowed, False if rate limited.
        """
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens
        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_rate
        )
        self.last_update = now

        # Try to consume
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def time_until_available(self) -> float:
        """Seconds until a token is available."""
        if self.tokens >= 1:
            return 0.0
        needed = 1 - self.tokens
        return needed / self.refill_rate


# ============================================================================
# Rate Limiter
# ============================================================================


class RateLimiter:
    """
    Production-grade rate limiter with multiple strategies.

    Features:
    - Token bucket algorithm
    - Per-key rate limiting
    - Automatic bucket cleanup
    - Thread-safe
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        cleanup_interval: int = 300,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Average allowed rate
            burst_size: Maximum burst capacity
            cleanup_interval: Seconds between bucket cleanups
        """
        self.rate = requests_per_minute / 60.0  # Convert to per-second
        self.burst_size = burst_size
        self.cleanup_interval = cleanup_interval

        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.time()

        logger.info(
            f"RateLimiter initialized: {requests_per_minute} req/min, "
            f"burst={burst_size}"
        )

    def allow(self, key: str, tokens: int = 1) -> bool:
        """
        Check if request is allowed.

        Args:
            key: Identifier (user_id, IP, etc.)
            tokens: Number of tokens to consume

        Returns:
            True if allowed, False if rate limited
        """
        with self._lock:
            self._maybe_cleanup()

            if key not in self._buckets:
                self._buckets[key] = TokenBucket(
                    capacity=self.burst_size,
                    refill_rate=self.rate,
                    tokens=self.burst_size,  # Start full
                )

            allowed = self._buckets[key].consume(tokens)

            if not allowed:
                logger.warning(f"Rate limited: {key}")

            return allowed

    def get_wait_time(self, key: str) -> float:
        """Get seconds to wait before next request is allowed."""
        with self._lock:
            if key not in self._buckets:
                return 0.0
            return self._buckets[key].time_until_available()

    def reset(self, key: str):
        """Reset rate limit for a key."""
        with self._lock:
            if key in self._buckets:
                del self._buckets[key]

    def get_stats(self) -> Dict[str, any]:
        """Get rate limiter statistics."""
        with self._lock:
            return {
                "active_buckets": len(self._buckets),
                "rate_per_second": self.rate,
                "burst_size": self.burst_size,
            }

    def _maybe_cleanup(self):
        """Remove stale buckets."""
        now = time.time()
        if now - self._last_cleanup < self.cleanup_interval:
            return

        self._last_cleanup = now
        stale_keys = []

        for key, bucket in self._buckets.items():
            # Remove if bucket is full and hasn't been used recently
            if bucket.tokens >= bucket.capacity:
                if now - bucket.last_update > self.cleanup_interval:
                    stale_keys.append(key)

        for key in stale_keys:
            del self._buckets[key]

        if stale_keys:
            logger.debug(f"Cleaned up {len(stale_keys)} stale buckets")


# ============================================================================
# Adaptive Rate Limiter
# ============================================================================


class AdaptiveRateLimiter(RateLimiter):
    """
    Rate limiter that adapts based on system load.

    Features:
    - Reduces limits under high load
    - Increases limits when system is idle
    - Priority queue for important users
    """

    def __init__(
        self,
        base_rpm: int = 60,
        min_rpm: int = 10,
        max_rpm: int = 200,
        **kwargs
    ):
        super().__init__(requests_per_minute=base_rpm, **kwargs)
        self.base_rpm = base_rpm
        self.min_rpm = min_rpm
        self.max_rpm = max_rpm
        self._priority_users: set = set()
        self._current_load: float = 0.0

    def set_load(self, load: float):
        """
        Update current system load (0.0 - 1.0).

        Adjusts rate limits accordingly.
        """
        self._current_load = max(0.0, min(1.0, load))

        # Adjust rate based on load
        if self._current_load > 0.8:
            # High load: reduce to minimum
            new_rpm = self.min_rpm
        elif self._current_load > 0.5:
            # Medium load: linear reduction
            factor = 1.0 - (self._current_load - 0.5) * 2
            new_rpm = self.min_rpm + (self.base_rpm - self.min_rpm) * factor
        else:
            # Low load: allow up to max
            factor = 1.0 + (0.5 - self._current_load)
            new_rpm = min(self.max_rpm, self.base_rpm * factor)

        self.rate = new_rpm / 60.0
        logger.debug(
            f"Adjusted rate to {new_rpm:.0f} RPM (load={self._current_load:.0%})")

    def add_priority_user(self, user_id: str):
        """Mark user as priority (higher limits)."""
        self._priority_users.add(user_id)

    def allow(self, key: str, tokens: int = 1) -> bool:
        """Allow with priority consideration."""
        if key in self._priority_users:
            tokens = max(1, tokens // 2)  # Priority users consume fewer tokens
        return super().allow(key, tokens)


# ============================================================================
# Sliding Window Rate Limiter
# ============================================================================


class SlidingWindowLimiter:
    """
    Sliding window rate limiter for more accurate limiting.

    Uses sliding log algorithm for precise rate calculation.
    """

    def __init__(self, requests: int = 60, window_seconds: int = 60):
        self.max_requests = requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Remove old requests
            self._requests[key] = [
                t for t in self._requests[key] if t > cutoff
            ]

            if len(self._requests[key]) < self.max_requests:
                self._requests[key].append(now)
                return True
            return False

    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            current = len([t for t in self._requests[key] if t > cutoff])
            return max(0, self.max_requests - current)


# ============================================================================
# Global Instance
# ============================================================================


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


if __name__ == "__main__":
    # Quick test
    limiter = RateLimiter(requests_per_minute=10, burst_size=3)

    user = "test_user"

    # Burst test
    for i in range(5):
        allowed = limiter.allow(user)
        print(f"Request {i+1}: {'allowed' if allowed else 'BLOCKED'}")

    # Wait and try again
    print(f"Wait time: {limiter.get_wait_time(user):.2f}s")
    print(f"Stats: {limiter.get_stats()}")
