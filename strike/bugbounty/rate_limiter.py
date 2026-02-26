#!/usr/bin/env python3
"""
SENTINEL Strike — Rate Limiter

Token bucket rate limiter for bug bounty compliance.
"""

import asyncio
import time
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Ensures requests don't exceed specified rate.

    Example:
        limiter = RateLimiter(requests_per_second=10)
        await limiter.acquire()  # Wait if needed
        # Make request
    """

    def __init__(self, requests_per_second: float = 10.0):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.rps = requests_per_second
        self.tokens = requests_per_second
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        """
        Acquire permission to make a request.

        Returns:
            Time waited in seconds
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Replenish tokens
            self.tokens = min(self.rps, self.tokens + elapsed * self.rps)
            self.last_update = now

            wait_time = 0.0

            if self.tokens < 1:
                # Need to wait
                wait_time = (1 - self.tokens) / self.rps
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1

            return wait_time

    def acquire_sync(self) -> float:
        """
        Synchronous version of acquire.

        Returns:
            Time waited in seconds
        """
        now = time.time()
        elapsed = now - self.last_update

        self.tokens = min(self.rps, self.tokens + elapsed * self.rps)
        self.last_update = now

        wait_time = 0.0

        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.rps
            time.sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1

        return wait_time

    def can_acquire(self) -> bool:
        """Check if can acquire immediately."""
        now = time.time()
        elapsed = now - self.last_update
        current_tokens = min(self.rps, self.tokens + elapsed * self.rps)
        return current_tokens >= 1


class DomainRateLimiter:
    """
    Per-domain rate limiting.

    Maintains separate rate limiters for each domain.

    Example:
        limiter = DomainRateLimiter(default_rps=10)
        await limiter.acquire("example.com")
        await limiter.acquire("another.com", rps=5)  # Custom rate
    """

    def __init__(self, default_rps: float = 10.0):
        """
        Initialize domain rate limiter.

        Args:
            default_rps: Default requests per second for new domains
        """
        self.default_rps = default_rps
        self.limiters: Dict[str, RateLimiter] = {}
        self._stats: Dict[str, int] = defaultdict(int)

    async def acquire(self, domain: str, rps: float = None) -> float:
        """
        Acquire permission for domain.

        Args:
            domain: Domain to rate limit
            rps: Optional custom rate for this domain

        Returns:
            Time waited
        """
        if domain not in self.limiters:
            self.limiters[domain] = RateLimiter(rps or self.default_rps)

        wait_time = await self.limiters[domain].acquire()
        self._stats[domain] += 1

        if wait_time > 0:
            logger.debug("Rate limited on %s: waited %.2fs", domain, wait_time)

        return wait_time

    def acquire_sync(self, domain: str, rps: float = None) -> float:
        """Synchronous version of acquire."""
        if domain not in self.limiters:
            self.limiters[domain] = RateLimiter(rps or self.default_rps)

        wait_time = self.limiters[domain].acquire_sync()
        self._stats[domain] += 1

        return wait_time

    def set_rate(self, domain: str, rps: float):
        """Set custom rate for domain."""
        self.limiters[domain] = RateLimiter(rps)

    def get_stats(self) -> Dict[str, int]:
        """Get request counts per domain."""
        return dict(self._stats)

    def reset_stats(self):
        """Reset request statistics."""
        self._stats.clear()


class BurstLimiter:
    """
    Burst-aware rate limiter.

    Allows short bursts but enforces overall rate.
    Useful for pagination or parallel requests.
    """

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 5
    ):
        """
        Initialize burst limiter.

        Args:
            requests_per_second: Sustained rate
            burst_size: Maximum burst size
        """
        self.rps = requests_per_second
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self, count: int = 1) -> float:
        """
        Acquire multiple tokens at once.

        Args:
            count: Number of tokens to acquire

        Returns:
            Time waited
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update

            # Replenish tokens (up to burst_size)
            self.tokens = min(
                float(self.burst_size),
                self.tokens + elapsed * self.rps
            )
            self.last_update = now

            wait_time = 0.0

            if self.tokens < count:
                wait_time = (count - self.tokens) / self.rps
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= count

            return wait_time


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter with automatic slowdown.

    Detects rate limiting responses and automatically reduces request rate.
    Uses exponential backoff on consecutive rate limits.

    Example:
        limiter = AdaptiveRateLimiter(initial_rps=10)

        # Before each request
        await limiter.before_request()

        # After response
        limiter.on_response(response_code, is_blocked=False)

        # If rate limited
        limiter.on_rate_limit()  # Automatically slows down
    """

    # Rate limit indicators
    RATE_LIMIT_CODES = {429, 503, 529}
    RATE_LIMIT_PATTERNS = [
        'rate limit', 'too many requests', 'slow down',
        'throttled', 'quota exceeded', 'try again later',
        'blocked', 'banned', 'forbidden', 'access denied'
    ]

    def __init__(
        self,
        initial_rps: float = 10.0,
        min_rps: float = 0.5,
        max_rps: float = 50.0,
        backoff_factor: float = 0.5,
        recovery_factor: float = 1.1,
        consecutive_success_to_recover: int = 10
    ):
        """
        Initialize adaptive rate limiter.

        Args:
            initial_rps: Starting requests per second
            min_rps: Minimum RPS (won't go below this)
            max_rps: Maximum RPS (won't go above this)
            backoff_factor: Multiply RPS by this on rate limit (0.5 = halve speed)
            recovery_factor: Multiply RPS by this on success streak
            consecutive_success_to_recover: Successes needed before speeding up
        """
        self.initial_rps = initial_rps
        self.current_rps = initial_rps
        self.min_rps = min_rps
        self.max_rps = max_rps
        self.backoff_factor = backoff_factor
        self.recovery_factor = recovery_factor
        self.consecutive_success_to_recover = consecutive_success_to_recover

        self._limiter = RateLimiter(initial_rps)
        self._consecutive_success = 0
        self._consecutive_rate_limits = 0
        self._total_rate_limits = 0
        self._total_requests = 0
        self._lock = asyncio.Lock()

        # Callbacks for UI notification
        self._on_slowdown_callback = None
        self._on_speedup_callback = None

        logger.info(f"AdaptiveRateLimiter initialized: {initial_rps} RPS")

    def set_callbacks(self, on_slowdown=None, on_speedup=None):
        """Set callbacks for rate changes."""
        self._on_slowdown_callback = on_slowdown
        self._on_speedup_callback = on_speedup

    async def before_request(self) -> float:
        """
        Call before making a request.

        Returns:
            Time waited in seconds
        """
        self._total_requests += 1
        return await self._limiter.acquire()

    def before_request_sync(self) -> float:
        """Synchronous version of before_request."""
        self._total_requests += 1
        return self._limiter.acquire_sync()

    def on_response(self, status_code: int = 200, response_text: str = "", is_blocked: bool = False):
        """
        Call after receiving a response.

        Args:
            status_code: HTTP status code
            response_text: Response body text (for pattern matching)
            is_blocked: Whether the request was detected as blocked
        """
        # Check if rate limited
        if self._is_rate_limited(status_code, response_text, is_blocked):
            self.on_rate_limit()
        else:
            self._on_success()

    def _is_rate_limited(self, status_code: int, response_text: str, is_blocked: bool) -> bool:
        """Check if response indicates rate limiting."""
        # Check status code
        if status_code in self.RATE_LIMIT_CODES:
            return True

        # Check if marked as blocked
        if is_blocked:
            return True

        # Check response text patterns
        text_lower = response_text.lower()
        for pattern in self.RATE_LIMIT_PATTERNS:
            if pattern in text_lower:
                return True

        return False

    def on_rate_limit(self):
        """
        Call when rate limiting is detected.
        Automatically reduces request rate.
        """
        self._consecutive_success = 0
        self._consecutive_rate_limits += 1
        self._total_rate_limits += 1

        # Calculate new rate with exponential backoff
        # More consecutive rate limits = more aggressive slowdown
        backoff = self.backoff_factor ** min(self._consecutive_rate_limits, 5)
        new_rps = max(self.min_rps, self.current_rps * backoff)

        if new_rps != self.current_rps:
            old_rps = self.current_rps
            self.current_rps = new_rps
            self._limiter = RateLimiter(new_rps)

            logger.warning(
                f"Rate limit detected! Slowing down: {old_rps:.1f} → {new_rps:.1f} RPS "
                f"(consecutive: {self._consecutive_rate_limits})"
            )

            if self._on_slowdown_callback:
                try:
                    self._on_slowdown_callback(
                        old_rps, new_rps, self._consecutive_rate_limits)
                except Exception:
                    pass

    def _on_success(self):
        """Handle successful request."""
        self._consecutive_rate_limits = 0
        self._consecutive_success += 1

        # Try to speed up after success streak
        if self._consecutive_success >= self.consecutive_success_to_recover:
            self._try_speedup()

    def _try_speedup(self):
        """Attempt to increase request rate after success streak."""
        if self.current_rps >= self.max_rps:
            return

        if self.current_rps >= self.initial_rps:
            return  # Don't go above initial rate

        old_rps = self.current_rps
        new_rps = min(self.initial_rps, self.current_rps *
                      self.recovery_factor)

        self.current_rps = new_rps
        self._limiter = RateLimiter(new_rps)
        self._consecutive_success = 0

        logger.info(f"Recovery: speeding up {old_rps:.1f} → {new_rps:.1f} RPS")

        if self._on_speedup_callback:
            try:
                self._on_speedup_callback(old_rps, new_rps)
            except Exception:
                pass

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            'current_rps': self.current_rps,
            'initial_rps': self.initial_rps,
            'total_requests': self._total_requests,
            'total_rate_limits': self._total_rate_limits,
            'consecutive_rate_limits': self._consecutive_rate_limits,
            'consecutive_success': self._consecutive_success,
            'rate_limit_percentage': (
                (self._total_rate_limits / self._total_requests * 100)
                if self._total_requests > 0 else 0
            )
        }

    def reset(self):
        """Reset to initial state."""
        self.current_rps = self.initial_rps
        self._limiter = RateLimiter(self.initial_rps)
        self._consecutive_success = 0
        self._consecutive_rate_limits = 0
        self._total_rate_limits = 0
        self._total_requests = 0
        logger.info(f"AdaptiveRateLimiter reset to {self.initial_rps} RPS")
