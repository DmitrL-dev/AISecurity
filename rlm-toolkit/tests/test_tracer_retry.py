"""Final tests for tracer, exporters, and retry modules."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
import time

from rlm_toolkit.observability.tracer import Tracer, Span, create_tracer
from rlm_toolkit.observability.exporters import ConsoleExporter, LangfuseExporter, LangSmithExporter
from rlm_toolkit.providers.retry import (
    RetryConfig,
    Retrier,
    OPENAI_RETRY_CONFIG,
    ANTHROPIC_RETRY_CONFIG,
    OLLAMA_RETRY_CONFIG,
)


# =============================================================================
# Span Tests
# =============================================================================

class TestSpan:
    """Tests for Span class."""
    
    def test_span_creation(self):
        """Test span creation."""
        span = Span(
            trace_id="trace-123",
            span_id="span-456",
            parent_id=None,
            name="test-span",
            start_time=time.time(),
        )
        
        assert span.trace_id == "trace-123"
        assert span.name == "test-span"
    
    def test_span_with_parent(self):
        """Test span with parent."""
        span = Span(
            trace_id="trace-1",
            span_id="span-2",
            parent_id="span-1",
            name="child",
            start_time=time.time(),
        )
        
        assert span.parent_id == "span-1"
    
    def test_duration_ms(self):
        """Test duration calculation."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=1000.0,
            end_time=1001.5,
        )
        
        assert span.duration_ms == 1500.0
    
    def test_duration_ms_not_ended(self):
        """Test duration when not ended."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=1000.0,
        )
        
        assert span.duration_ms is None
    
    def test_set_attribute(self):
        """Test setting attribute."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        
        span.set_attribute("key", "value")
        
        assert span.attributes["key"] == "value"
    
    def test_add_event(self):
        """Test adding event."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        
        span.add_event("my_event", {"data": 123})
        
        assert len(span.events) == 1
        assert span.events[0]["name"] == "my_event"
    
    def test_set_status(self):
        """Test setting status."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        
        span.set_status("error", "Something went wrong")
        
        assert span.status == "error"
        assert span.attributes["status_message"] == "Something went wrong"
    
    def test_end(self):
        """Test ending span."""
        span = Span(
            trace_id="t",
            span_id="s",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        
        span.end()
        
        assert span.end_time is not None
    
    def test_to_dict(self):
        """Test span serialization."""
        span = Span(
            trace_id="trace-1",
            span_id="span-1",
            parent_id=None,
            name="test",
            start_time=1000.0,
            end_time=1001.0,
        )
        
        data = span.to_dict()
        
        assert data["trace_id"] == "trace-1"
        assert data["duration_ms"] == 1000.0


# =============================================================================
# Tracer Tests
# =============================================================================

class TestTracerExtended:
    """Extended Tracer tests."""
    
    def test_tracer_creation(self):
        """Test tracer creation."""
        tracer = Tracer(name="test-service")
        
        assert tracer.name == "test-service"
    
    def test_start_span(self):
        """Test starting span."""
        tracer = Tracer()
        
        with tracer.start_span("my-operation") as span:
            span.set_attribute("key", "value")
        
        assert len(tracer.spans) == 1
        assert tracer.spans[0].name == "my-operation"
    
    def test_nested_spans(self):
        """Test nested spans."""
        tracer = Tracer()
        
        with tracer.start_span("parent") as parent_span:
            with tracer.start_span("child") as child_span:
                pass
        
        assert len(tracer.spans) == 2
        # Child span has parent
        child = [s for s in tracer.spans if s.name == "child"][0]
        assert child.parent_id is not None
    
    def test_span_exception(self):
        """Test span captures exception."""
        tracer = Tracer()
        
        with pytest.raises(ValueError):
            with tracer.start_span("failing") as span:
                raise ValueError("test error")
        
        assert tracer.spans[0].status == "error"
    
    def test_current_span(self):
        """Test current_span property."""
        tracer = Tracer()
        
        assert tracer.current_span is None
        
        with tracer.start_span("test") as span:
            assert tracer.current_span is span
        
        assert tracer.current_span is None
    
    def test_current_trace_id(self):
        """Test current_trace_id property."""
        tracer = Tracer()
        
        assert tracer.current_trace_id is None
        
        with tracer.start_span("test"):
            assert tracer.current_trace_id is not None
        
        assert tracer.current_trace_id is None
    
    def test_export(self):
        """Test export method."""
        tracer = Tracer()
        
        with tracer.start_span("op1"):
            pass
        with tracer.start_span("op2"):
            pass
        
        exported = tracer.export()
        
        assert len(exported) == 2
    
    def test_clear(self):
        """Test clear method."""
        tracer = Tracer()
        
        with tracer.start_span("test"):
            pass
        
        tracer.clear()
        
        assert len(tracer.spans) == 0
    
    def test_add_exporter(self):
        """Test add_exporter method."""
        tracer = Tracer()
        exporter = MagicMock()
        
        tracer.add_exporter(exporter)
        
        assert exporter in tracer.exporters
    
    def test_start_as_current_span_decorator(self):
        """Test decorator usage."""
        tracer = Tracer()
        
        @tracer.start_as_current_span("decorated")
        def my_function():
            return 42
        
        result = my_function()
        
        assert result == 42
        assert len(tracer.spans) == 1


class TestCreateTracer:
    """Tests for create_tracer factory."""
    
    def test_create_basic(self):
        """Test basic creation."""
        tracer = create_tracer(name="my-service")
        
        assert tracer.name == "my-service"
    
    def test_create_with_console(self):
        """Test with console exporter."""
        tracer = create_tracer(console=True)
        
        assert len(tracer.exporters) == 1


# =============================================================================
# Retry Config Tests
# =============================================================================

class TestRetryConfigExtended:
    """Extended RetryConfig tests."""
    
    def test_default_values(self):
        """Test default config values."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
    
    def test_get_delay_first_attempt(self):
        """Test delay for first attempt."""
        config = RetryConfig(initial_delay=1.0, jitter=0)
        
        delay = config.get_delay(0)
        
        assert delay == pytest.approx(1.0, abs=0.01)
    
    def test_get_delay_exponential(self):
        """Test exponential backoff."""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, jitter=0)
        
        delay_0 = config.get_delay(0)  # 1
        delay_1 = config.get_delay(1)  # 2
        delay_2 = config.get_delay(2)  # 4
        
        assert delay_1 == pytest.approx(2 * delay_0, abs=0.01)
        assert delay_2 == pytest.approx(2 * delay_1, abs=0.01)
    
    def test_get_delay_max_cap(self):
        """Test delay is capped at max."""
        config = RetryConfig(initial_delay=1.0, max_delay=5.0, jitter=0)
        
        delay = config.get_delay(10)  # Would be 1024 without cap
        
        assert delay <= 5.0
    
    def test_get_delay_with_jitter(self):
        """Test delay with jitter."""
        config = RetryConfig(initial_delay=1.0, jitter=0.5)
        
        delays = [config.get_delay(0) for _ in range(10)]
        
        # Delays should vary due to jitter
        assert len(set(delays)) > 1
    
    def test_should_retry_connection_error(self):
        """Test retry on ConnectionError."""
        config = RetryConfig()
        
        assert config.should_retry(ConnectionError()) is True
    
    def test_should_retry_timeout(self):
        """Test retry on TimeoutError."""
        config = RetryConfig()
        
        assert config.should_retry(TimeoutError()) is True
    
    def test_should_retry_429(self):
        """Test retry on 429 status."""
        config = RetryConfig()
        
        assert config.should_retry(Exception(), status_code=429) is True
    
    def test_should_not_retry_404(self):
        """Test no retry on 404."""
        config = RetryConfig()
        
        assert config.should_retry(Exception(), status_code=404) is False
    
    def test_should_not_retry_value_error(self):
        """Test no retry on ValueError."""
        config = RetryConfig()
        
        assert config.should_retry(ValueError()) is False


class TestRetrier:
    """Tests for Retrier class."""
    
    def test_execute_success(self):
        """Test successful execution."""
        retrier = Retrier()
        
        def success():
            return 42
        
        result = retrier.execute(success)
        
        assert result == 42
    
    def test_execute_with_retry(self):
        """Test execution with retries."""
        retrier = Retrier(RetryConfig(max_retries=3, initial_delay=0.01))
        
        attempts = [0]
        
        def failing_then_success():
            attempts[0] += 1
            if attempts[0] < 3:
                raise ConnectionError("Failed")
            return "success"
        
        result = retrier.execute(failing_then_success)
        
        assert result == "success"
        assert attempts[0] == 3
    
    def test_execute_exhausted_retries(self):
        """Test all retries exhausted."""
        retrier = Retrier(RetryConfig(max_retries=2, initial_delay=0.01))
        
        def always_fail():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            retrier.execute(always_fail)
    
    def test_execute_non_retryable(self):
        """Test non-retryable exception."""
        retrier = Retrier()
        
        def value_error():
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            retrier.execute(value_error)
    
    def test_execute_with_callback(self):
        """Test on_retry callback."""
        retrier = Retrier(RetryConfig(max_retries=2, initial_delay=0.01))
        
        callbacks = []
        
        def on_retry(attempt, exc, delay):
            callbacks.append((attempt, str(exc)))
        
        attempts = [0]
        
        def failing_once():
            attempts[0] += 1
            if attempts[0] == 1:
                raise ConnectionError("First fail")
            return "ok"
        
        result = retrier.execute(failing_once, on_retry=on_retry)
        
        assert result == "ok"
        assert len(callbacks) == 1
    
    def test_async_execute(self):
        """Test async execution."""
        retrier = Retrier()
        
        async def async_success():
            return 42
        
        result = asyncio.run(retrier.aexecute(async_success))
        
        assert result == 42


class TestProviderRetryConfigs:
    """Tests for provider retry config presets."""
    
    def test_openai_config(self):
        """Test OpenAI retry config."""
        assert OPENAI_RETRY_CONFIG.max_retries == 3
        assert 429 in OPENAI_RETRY_CONFIG.retry_status_codes
        assert 520 in OPENAI_RETRY_CONFIG.retry_status_codes
    
    def test_anthropic_config(self):
        """Test Anthropic retry config."""
        assert ANTHROPIC_RETRY_CONFIG.max_retries == 3
        assert 529 in ANTHROPIC_RETRY_CONFIG.retry_status_codes
    
    def test_ollama_config(self):
        """Test Ollama retry config."""
        assert OLLAMA_RETRY_CONFIG.max_retries == 2
        assert OLLAMA_RETRY_CONFIG.max_delay == 10.0
