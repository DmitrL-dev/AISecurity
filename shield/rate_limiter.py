"""
SENTINEL Shield v2.0 — Rate Limiter

In-memory rate limiter using sliding window algorithm.
Thread-safe via asyncio.Lock.

Supports per-IP and global limits.
Redis backend can be added as a future extension.
"""

import time
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger("shield.ratelimit")


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    limit: int
    reset_at: float
    retry_after: float = 0.0


class SlidingWindowLimiter:
    """
    Sliding window rate limiter.

    Tracks request timestamps per key (IP/client).
    Window = 60 seconds by default.
    """

    def __init__(
        self,
        requests_per_minute: int = 100,
        burst: int = 20,
        window_seconds: int = 60,
    ):
        self.rpm = requests_per_minute
        self.burst = burst
        self.window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._total_allowed = 0
        self._total_rejected = 0

    async def check(self, key: str = "global") -> RateLimitResult:
        """
        Check if request is allowed.

        Args:
            key: Rate limit key (IP, API key, etc.)

        Returns:
            RateLimitResult with allowed/remaining info
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window

            # Remove expired entries
            timestamps = self._requests[key]
            self._requests[key] = [t for t in timestamps if t > cutoff]
            timestamps = self._requests[key]

            current = len(timestamps)

            if current >= self.rpm:
                # Rate exceeded
                self._total_rejected += 1
                oldest = timestamps[0] if timestamps else now
                retry = oldest + self.window - now
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=self.rpm,
                    reset_at=oldest + self.window,
                    retry_after=max(0, retry),
                )

            # Allow request
            timestamps.append(now)
            self._total_allowed += 1

            return RateLimitResult(
                allowed=True,
                remaining=self.rpm - current - 1,
                limit=self.rpm,
                reset_at=now + self.window,
            )

    async def reset(self, key: str = "global"):
        """Reset rate limit for a key."""
        async with self._lock:
            self._requests.pop(key, None)

    async def reset_all(self):
        """Reset all rate limits."""
        async with self._lock:
            self._requests.clear()

    def stats(self) -> dict:
        return {
            "rpm_limit": self.rpm,
            "burst": self.burst,
            "window_seconds": self.window,
            "active_keys": len(self._requests),
            "total_allowed": self._total_allowed,
            "total_rejected": self._total_rejected,
            "rejection_rate": (
                self._total_rejected
                / max(
                    self._total_allowed + self._total_rejected,
                    1,
                )
                * 100
            ),
        }
