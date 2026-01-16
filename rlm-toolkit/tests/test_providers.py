"""Unit tests for providers."""

import pytest
from rlm_toolkit.providers.base import LLMProvider, LLMResponse
from rlm_toolkit.providers.retry import RetryConfig, Retrier
from rlm_toolkit.providers.rate_limit import TokenBucket, RateLimiter, RateLimitConfig
from rlm_toolkit.testing.mocks import MockProvider, SequenceProvider


class TestMockProvider:
    """Tests for MockProvider."""
    
    def test_single_response(self):
        """Test single fixed response."""
        mock = MockProvider(responses="test response")
        response = mock.generate("prompt")
        assert response.content == "test response"
    
    def test_sequence_responses(self):
        """Test sequence of responses."""
        mock = MockProvider(responses=["first", "second", "third"])
        assert mock.generate("p").content == "first"
        assert mock.generate("p").content == "second"
        assert mock.generate("p").content == "third"
        # Should repeat last
        assert mock.generate("p").content == "third"
    
    def test_call_count(self):
        """Test call counting."""
        mock = MockProvider()
        assert mock.call_count == 0
        mock.generate("p")
        assert mock.call_count == 1
        mock.generate("p")
        assert mock.call_count == 2
    
    def test_history_recording(self):
        """Test that calls are recorded."""
        mock = MockProvider()
        mock.generate("test prompt")
        assert len(mock.history) == 1
        assert mock.history[0]["prompt"] == "test prompt"
    
    def test_raise_on_call(self):
        """Test error injection."""
        mock = MockProvider(raise_on_call=2)
        mock.generate("p")  # OK
        with pytest.raises(RuntimeError):
            mock.generate("p")  # Raises


class TestSequenceProvider:
    """Tests for SequenceProvider."""
    
    def test_sequence(self):
        """Test basic sequence."""
        seq = SequenceProvider("a", "b", "c")
        assert seq.generate("").content == "a"
        assert seq.generate("").content == "b"
        assert seq.generate("").content == "c"
    
    def test_cycle(self):
        """Test cycling through responses."""
        seq = SequenceProvider("x", "y", cycle=True)
        assert seq.generate("").content == "x"
        assert seq.generate("").content == "y"
        assert seq.generate("").content == "x"  # Cycles back


class TestRetryConfig:
    """Tests for RetryConfig."""
    
    def test_exponential_delay(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, jitter=0)
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
    
    def test_max_delay_cap(self):
        """Test delay is capped at max."""
        config = RetryConfig(initial_delay=1.0, max_delay=5.0, jitter=0)
        assert config.get_delay(10) == 5.0
    
    def test_should_retry_connection_error(self):
        """Test retry on ConnectionError."""
        config = RetryConfig()
        assert config.should_retry(ConnectionError())
    
    def test_should_retry_status_429(self):
        """Test retry on rate limit status."""
        config = RetryConfig()
        assert config.should_retry(Exception(), status_code=429)
    
    def test_should_not_retry_value_error(self):
        """Test no retry on ValueError."""
        config = RetryConfig()
        assert not config.should_retry(ValueError())


class TestRetrier:
    """Tests for Retrier."""
    
    def test_success_no_retry(self):
        """Test successful call without retries."""
        retrier = Retrier(RetryConfig(max_retries=3))
        result = retrier.execute(lambda: "success")
        assert result == "success"
    
    def test_retry_then_success(self):
        """Test retry until success."""
        attempts = [0]
        
        def fail_twice():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("fail")
            return "success"
        
        retrier = Retrier(RetryConfig(max_retries=5, initial_delay=0.001))
        result = retrier.execute(fail_twice)
        assert result == "success"
        assert attempts[0] == 3
    
    def test_max_retries_exceeded(self):
        """Test failure after max retries."""
        retrier = Retrier(RetryConfig(max_retries=2, initial_delay=0.001))
        
        with pytest.raises(ConnectionError):
            retrier.execute(lambda: (_ for _ in ()).throw(ConnectionError("fail")))


class TestTokenBucket:
    """Tests for TokenBucket."""
    
    def test_initial_capacity(self):
        """Test bucket starts at capacity."""
        bucket = TokenBucket(rate=10, capacity=100)
        assert bucket.available == 100
    
    def test_acquire(self):
        """Test token acquisition."""
        bucket = TokenBucket(rate=10, capacity=100)
        assert bucket.acquire(50)
        assert bucket.available == pytest.approx(50, abs=1)
    
    def test_non_blocking_fail(self):
        """Test non-blocking acquire when empty."""
        bucket = TokenBucket(rate=1, capacity=10)
        bucket.acquire(10)  # Use all
        assert not bucket.acquire(5, block=False)


class TestRateLimiter:
    """Tests for RateLimiter."""
    
    def test_configure_and_acquire(self):
        """Test basic configuration and acquisition."""
        limiter = RateLimiter()
        limiter.configure("test", RateLimitConfig(requests_per_minute=60))
        assert limiter.acquire("test", block=False)
    
    def test_unknown_provider_passthrough(self):
        """Test unknown provider allows requests."""
        limiter = RateLimiter()
        assert limiter.acquire("unknown", block=False)
