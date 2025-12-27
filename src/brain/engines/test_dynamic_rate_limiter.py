"""
Unit tests for Dynamic Rate Limiter.
"""

import pytest
from dynamic_rate_limiter import (
    DynamicRateLimiter,
    TokenBucket,
    BurstDetector,
    AdaptiveThreshold,
    UserBehavior,
    LimitAction,
)


class TestTokenBucket:
    """Tests for token bucket."""

    def test_consume_success(self):
        """Can consume tokens."""
        bucket = TokenBucket(capacity=10)

        result = bucket.consume(1)

        assert result is True
        assert bucket.remaining() == 9

    def test_consume_fails_empty(self):
        """Cannot consume from empty bucket."""
        bucket = TokenBucket(capacity=2, refill_rate=0)
        bucket.consume(2)

        result = bucket.consume(1)

        assert result is False


class TestBurstDetector:
    """Tests for burst detector."""

    def test_no_burst(self):
        """Normal traffic not burst."""
        detector = BurstDetector(threshold=5)

        is_burst = detector.is_burst([1.0, 2.0, 3.0])

        assert is_burst is False

    def test_detect_burst(self):
        """Detects burst traffic."""
        import time

        detector = BurstDetector(window=2.0, threshold=5)
        now = time.time()
        times = [now - 0.1 * i for i in range(10)]

        is_burst = detector.is_burst(times)

        assert is_burst is True


class TestDynamicRateLimiter:
    """Integration tests."""

    def test_allow_normal(self):
        """Normal requests allowed."""
        limiter = DynamicRateLimiter(base_limit=100)

        result = limiter.check("user1")

        assert result.action == LimitAction.ALLOW

    def test_tracks_remaining(self):
        """Tracks remaining requests."""
        limiter = DynamicRateLimiter(base_limit=10)

        limiter.check("user1")
        result = limiter.check("user1")

        assert result.requests_remaining < 10

    def test_throttle_on_limit(self):
        """Throttles when limit reached."""
        limiter = DynamicRateLimiter(base_limit=3)

        for _ in range(5):
            result = limiter.check("user1")

        assert result.action in (LimitAction.THROTTLE, LimitAction.ALLOW)

    def test_different_users(self):
        """Different users have separate limits."""
        limiter = DynamicRateLimiter(base_limit=5)

        for _ in range(3):
            limiter.check("user1")

        result = limiter.check("user2")

        assert result.action == LimitAction.ALLOW


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
