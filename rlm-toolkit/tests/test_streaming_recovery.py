"""Unit tests for streaming and recovery modules."""

import pytest
import time

from rlm_toolkit.core.streaming import (
    RLMStreamEvent,
    TokenEvent,
    ExecutionEvent,
    FinalEvent,
    ErrorEvent,
)
from rlm_toolkit.core.recovery import (
    RecoveryStrategy,
    RecoveryConfig,
    RecoveryHandler,
)


class TestRLMStreamEvent:
    """Tests for RLMStreamEvent."""
    
    def test_creation(self):
        """Test event creation."""
        event = RLMStreamEvent(
            type="run_start",
            iteration=0,
            timestamp=time.time(),
        )
        
        assert event.type == "run_start"
        assert event.iteration == 0
    
    def test_with_data(self):
        """Test event with data."""
        event = RLMStreamEvent(
            type="iteration_start",
            iteration=1,
            timestamp=time.time(),
            data={"context_length": 1000},
        )
        
        assert event.data["context_length"] == 1000
    
    def test_repr(self):
        """Test string representation."""
        event = RLMStreamEvent(
            type="final",
            iteration=5,
            timestamp=time.time(),
        )
        
        repr_str = repr(event)
        assert "final" in repr_str
        assert "5" in repr_str


class TestTokenEvent:
    """Tests for TokenEvent."""
    
    def test_creation(self):
        """Test token event creation."""
        event = TokenEvent(
            type="llm_token",
            iteration=1,
            timestamp=time.time(),
            token="Hello",
        )
        
        assert event.token == "Hello"
        assert event.is_subcall is False
    
    def test_subcall_flag(self):
        """Test subcall flag."""
        event = TokenEvent(
            type="llm_token",
            iteration=1,
            timestamp=time.time(),
            is_subcall=True,
        )
        
        assert event.is_subcall is True


class TestExecutionEvent:
    """Tests for ExecutionEvent."""
    
    def test_creation(self):
        """Test execution event creation."""
        event = ExecutionEvent(
            type="code_executed",
            iteration=2,
            timestamp=time.time(),
            code="print(42)",
            output="42",
        )
        
        assert event.code == "print(42)"
        assert event.output == "42"


class TestFinalEvent:
    """Tests for FinalEvent."""
    
    def test_creation(self):
        """Test final event creation."""
        event = FinalEvent(
            type="final",
            iteration=3,
            timestamp=time.time(),
            answer="The answer is 42",
        )
        
        assert event.answer == "The answer is 42"
        assert event.status == "success"
    
    def test_custom_status(self):
        """Test custom status."""
        event = FinalEvent(
            type="final",
            iteration=3,
            timestamp=time.time(),
            status="max_iterations",
        )
        
        assert event.status == "max_iterations"


class TestErrorEvent:
    """Tests for ErrorEvent."""
    
    def test_creation(self):
        """Test error event creation."""
        event = ErrorEvent(
            type="error",
            iteration=1,
            timestamp=time.time(),
            error_type="ValueError",
            error_message="Invalid input",
        )
        
        assert event.error_type == "ValueError"
        assert event.error_message == "Invalid input"


class TestRecoveryStrategy:
    """Tests for RecoveryStrategy enum."""
    
    def test_values(self):
        """Test strategy values."""
        assert RecoveryStrategy.SAME.value == "same"
        assert RecoveryStrategy.FIX.value == "fix"
        assert RecoveryStrategy.SKIP.value == "skip"
    
    def test_comparison(self):
        """Test strategy comparison."""
        assert RecoveryStrategy.FIX == RecoveryStrategy.FIX
        assert RecoveryStrategy.SAME != RecoveryStrategy.FIX


class TestRecoveryConfig:
    """Tests for RecoveryConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = RecoveryConfig()
        
        assert config.max_retries == 3
        assert config.retry_strategy == RecoveryStrategy.FIX
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RecoveryConfig(
            max_retries=5,
            retry_strategy=RecoveryStrategy.SAME,
        )
        
        assert config.max_retries == 5
        assert config.retry_strategy == RecoveryStrategy.SAME
    
    def test_prompt_template(self):
        """Test fix prompt template."""
        config = RecoveryConfig()
        
        assert "{error}" in config.fix_prompt_template
        assert "{code}" in config.fix_prompt_template


class TestRecoveryHandler:
    """Tests for RecoveryHandler."""
    
    def test_creation(self):
        """Test handler creation."""
        config = RecoveryConfig()
        handler = RecoveryHandler(config)
        
        assert handler.config == config
    
    def test_should_retry_initial(self):
        """Test should_retry for new error."""
        handler = RecoveryHandler(RecoveryConfig(max_retries=3))
        
        assert handler.should_retry("error_key") is True
    
    def test_should_retry_after_max(self):
        """Test should_retry after max retries."""
        handler = RecoveryHandler(RecoveryConfig(max_retries=2))
        
        handler.record_retry("error_key")
        handler.record_retry("error_key")
        
        assert handler.should_retry("error_key") is False
    
    def test_record_retry(self):
        """Test recording retries."""
        handler = RecoveryHandler(RecoveryConfig())
        
        handler.record_retry("key1")
        handler.record_retry("key1")
        handler.record_retry("key2")
        
        assert handler.retry_counts["key1"] == 2
        assert handler.retry_counts["key2"] == 1
    
    def test_get_recovery_prompt(self):
        """Test recovery prompt generation."""
        handler = RecoveryHandler(RecoveryConfig())
        
        prompt = handler.get_recovery_prompt(
            code="print(undefined)",
            error="NameError: name 'undefined' is not defined",
        )
        
        assert "undefined" in prompt
        assert "NameError" in prompt
    
    def test_reset(self):
        """Test reset clears retry counts."""
        handler = RecoveryHandler(RecoveryConfig())
        
        handler.record_retry("key1")
        handler.record_retry("key2")
        handler.reset()
        
        assert len(handler.retry_counts) == 0
        assert handler.should_retry("key1") is True
