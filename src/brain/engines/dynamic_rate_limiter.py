"""
Dynamic Rate Limiter Engine - Adaptive Rate Limiting

Provides intelligent rate limiting:
- Adaptive thresholds
- User behavior analysis
- Burst detection
- Fair queuing

Addresses: OWASP ASI-04 (Resource Exhaustion)
Research: rate_limiting_deep_dive.md
Invention: Dynamic Rate Limiter (#40)
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("DynamicRateLimiter")


# ============================================================================
# Data Classes
# ============================================================================


class LimitAction(Enum):
    """Rate limit actions."""

    ALLOW = "allow"
    THROTTLE = "throttle"
    BLOCK = "block"
    QUEUE = "queue"


@dataclass
class UserBehavior:
    """Tracks user behavior."""

    user_id: str
    request_times: List[float] = field(default_factory=list)
    total_requests: int = 0
    violations: int = 0
    trust_score: float = 1.0


@dataclass
class RateLimitResult:
    """Result from rate limiting."""

    action: LimitAction
    requests_remaining: int
    reset_time: float
    wait_time: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "action": self.action.value,
            "requests_remaining": self.requests_remaining,
            "reset_time": self.reset_time,
            "wait_time": self.wait_time,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Token Bucket
# ============================================================================


class TokenBucket:
    """
    Token bucket rate limiter.
    """

    def __init__(self, capacity: int = 100, refill_rate: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate  # tokens per second
        self._tokens = capacity
        self._last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens."""
        self._refill()

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on time."""
        now = time.time()
        elapsed = now - self._last_refill
        refill = elapsed * self.refill_rate

        self._tokens = min(self.capacity, self._tokens + refill)
        self._last_refill = now

    def remaining(self) -> int:
        """Get remaining tokens."""
        self._refill()
        return int(self._tokens)


# ============================================================================
# Burst Detector
# ============================================================================


class BurstDetector:
    """
    Detects request bursts.
    """

    def __init__(self, window: float = 1.0, threshold: int = 10):
        self.window = window
        self.threshold = threshold

    def is_burst(self, request_times: List[float]) -> bool:
        """Check if requests indicate a burst."""
        if len(request_times) < self.threshold:
            return False

        now = time.time()
        recent = [t for t in request_times if now - t < self.window]

        return len(recent) >= self.threshold


# ============================================================================
# Adaptive Threshold
# ============================================================================


class AdaptiveThreshold:
    """
    Adapts rate limits based on behavior.
    """

    def __init__(self, base_limit: int = 100):
        self.base_limit = base_limit

    def calculate(self, behavior: UserBehavior) -> int:
        """Calculate adaptive limit for user."""
        # Good behavior gets higher limits
        multiplier = behavior.trust_score

        # Violations reduce limit
        if behavior.violations > 0:
            multiplier *= max(0.1, 1.0 - behavior.violations * 0.1)

        return int(self.base_limit * multiplier)


# ============================================================================
# Main Engine
# ============================================================================


class DynamicRateLimiter:
    """
    Dynamic Rate Limiter - Adaptive Rate Limiting

    Intelligent limiting:
    - Token bucket
    - Burst detection
    - Adaptive thresholds

    Invention #40 from research.
    Addresses OWASP ASI-04.
    """

    def __init__(self, base_limit: int = 100, window: float = 60.0):
        self._buckets: Dict[str, TokenBucket] = {}
        self._behaviors: Dict[str, UserBehavior] = {}
        self.burst_detector = BurstDetector()
        self.adaptive = AdaptiveThreshold(base_limit)
        self.window = window

        logger.info("DynamicRateLimiter initialized")

    def _get_bucket(self, user_id: str) -> TokenBucket:
        """Get or create bucket for user."""
        if user_id not in self._buckets:
            behavior = self._get_behavior(user_id)
            limit = self.adaptive.calculate(behavior)
            self._buckets[user_id] = TokenBucket(
                capacity=limit,
                refill_rate=limit / self.window,
            )
        return self._buckets[user_id]

    def _get_behavior(self, user_id: str) -> UserBehavior:
        """Get or create behavior for user."""
        if user_id not in self._behaviors:
            self._behaviors[user_id] = UserBehavior(user_id=user_id)
        return self._behaviors[user_id]

    def check(self, user_id: str) -> RateLimitResult:
        """
        Check rate limit for user.

        Args:
            user_id: User identifier

        Returns:
            RateLimitResult
        """
        start = time.time()

        behavior = self._get_behavior(user_id)
        bucket = self._get_bucket(user_id)

        # Record request time
        behavior.request_times.append(time.time())
        behavior.total_requests += 1

        # Keep only recent times
        cutoff = time.time() - self.window
        behavior.request_times = [
            t for t in behavior.request_times if t > cutoff]

        # Check burst
        is_burst = self.burst_detector.is_burst(behavior.request_times)
        if is_burst:
            behavior.violations += 1
            behavior.trust_score = max(0.1, behavior.trust_score - 0.1)

            logger.warning(f"Burst detected for {user_id}")

            return RateLimitResult(
                action=LimitAction.BLOCK,
                requests_remaining=0,
                reset_time=time.time() + 60,
                wait_time=60.0,
                explanation="Burst detected",
                latency_ms=(time.time() - start) * 1000,
            )

        # Check bucket
        if bucket.consume():
            return RateLimitResult(
                action=LimitAction.ALLOW,
                requests_remaining=bucket.remaining(),
                reset_time=time.time() + self.window,
                explanation="Allowed",
                latency_ms=(time.time() - start) * 1000,
            )
        else:
            return RateLimitResult(
                action=LimitAction.THROTTLE,
                requests_remaining=0,
                reset_time=time.time() + 10,
                wait_time=10.0,
                explanation="Rate limit exceeded",
                latency_ms=(time.time() - start) * 1000,
            )


# ============================================================================
# Convenience
# ============================================================================

_default_limiter: Optional[DynamicRateLimiter] = None


def get_limiter() -> DynamicRateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = DynamicRateLimiter()
    return _default_limiter
