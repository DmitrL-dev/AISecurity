"""Unit tests for callbacks module."""

import pytest
from unittest.mock import MagicMock
import logging

from rlm_toolkit.core.callbacks import (
    RLMCallback,
    CallbackManager,
    LoggingCallback,
    CostTrackingCallback,
    StreamingCallback,
)


class MockCallback(RLMCallback):
    """Mock callback for testing."""
    
    def __init__(self):
        self.events = []
    
    def on_run_start(self, context, query, config):
        self.events.append(("run_start", context, query))
    
    def on_iteration_start(self, iteration, history):
        self.events.append(("iteration_start", iteration))
    
    def on_iteration_end(self, iteration, output):
        self.events.append(("iteration_end", iteration, output))
    
    def on_code_executed(self, code, output):
        self.events.append(("code_executed", code, output))
    
    def on_final(self, result):
        self.events.append(("final", result))
    
    def on_error(self, error, context):
        self.events.append(("error", str(error)))


class TestRLMCallback:
    """Tests for RLMCallback base class."""
    
    def test_default_methods_dont_raise(self):
        """Test default methods are no-ops."""
        callback = MockCallback()
        
        # These should not raise
        callback.on_llm_response(MagicMock(), is_subcall=False)
        callback.on_code_extracted(code="print(1)")
        callback.on_subcall_start(prompt="test", depth=1)
        callback.on_subcall_end(response="resp", depth=1, cost=0.01)
        callback.on_security_violation(violation="test", code="code")


class TestCallbackManager:
    """Tests for CallbackManager."""
    
    def test_create_empty(self):
        """Test creating empty manager."""
        manager = CallbackManager()
        
        assert len(manager.callbacks) == 0
    
    def test_create_with_callbacks(self):
        """Test creating with callbacks list."""
        cb1 = MockCallback()
        cb2 = MockCallback()
        manager = CallbackManager(callbacks=[cb1, cb2])
        
        assert len(manager.callbacks) == 2
    
    def test_add_callback(self):
        """Test adding callback."""
        manager = CallbackManager()
        cb = MockCallback()
        
        manager.add(cb)
        
        assert cb in manager.callbacks
    
    def test_remove_callback(self):
        """Test removing callback."""
        cb = MockCallback()
        manager = CallbackManager(callbacks=[cb])
        
        manager.remove(cb)
        
        assert cb not in manager.callbacks
    
    def test_clear(self):
        """Test clearing all callbacks."""
        manager = CallbackManager(callbacks=[MockCallback(), MockCallback()])
        
        manager.clear()
        
        assert len(manager.callbacks) == 0
    
    def test_fire_event(self):
        """Test firing event to all callbacks."""
        cb1 = MockCallback()
        cb2 = MockCallback()
        manager = CallbackManager(callbacks=[cb1, cb2])
        
        manager.fire("on_iteration_start", iteration=5, history=[])
        
        assert ("iteration_start", 5) in cb1.events
        assert ("iteration_start", 5) in cb2.events
    
    def test_fire_continues_on_error(self):
        """Test fire continues if callback raises."""
        cb1 = MockCallback()
        cb1.on_iteration_start = MagicMock(side_effect=Exception("Test error"))
        cb2 = MockCallback()
        
        manager = CallbackManager(callbacks=[cb1, cb2])
        
        # Should not raise
        manager.fire("on_iteration_start", iteration=1, history=[])
        
        # cb2 should still receive event
        assert ("iteration_start", 1) in cb2.events
    
    def test_fire_unknown_event(self):
        """Test firing unknown event is no-op."""
        cb = MockCallback()
        manager = CallbackManager(callbacks=[cb])
        
        # Should not raise
        manager.fire("on_unknown_event", data="test")
        
        # No events recorded
        assert len(cb.events) == 0


class TestLoggingCallback:
    """Tests for LoggingCallback."""
    
    def test_creation_default_logger(self):
        """Test creation with default logger."""
        callback = LoggingCallback()
        
        assert callback.logger is not None
    
    def test_creation_custom_logger(self):
        """Test creation with custom logger."""
        logger = logging.getLogger("test")
        callback = LoggingCallback(logger=logger)
        
        assert callback.logger is logger
    
    def test_on_run_start(self):
        """Test run start logging."""
        logger = MagicMock()
        callback = LoggingCallback(logger=logger)
        
        callback.on_run_start(context="ctx", query="query", config=MagicMock())
        
        assert logger.info.called
    
    def test_on_final(self):
        """Test final logging."""
        logger = MagicMock()
        callback = LoggingCallback(logger=logger)
        
        callback.on_final(result="The answer is 42")
        
        assert logger.info.called


class TestCostTrackingCallback:
    """Tests for CostTrackingCallback."""
    
    def test_initial_cost_zero(self):
        """Test initial cost is zero."""
        callback = CostTrackingCallback()
        
        assert callback.total_cost == 0.0
        assert callback.get_total_cost() == 0.0
    
    def test_tracks_cost(self):
        """Test cost tracking."""
        callback = CostTrackingCallback()
        
        callback.on_subcall_end(response="r1", depth=1, cost=0.01)
        callback.on_subcall_end(response="r2", depth=1, cost=0.02)
        
        assert callback.get_total_cost() == 0.03
    
    def test_reset(self):
        """Test cost reset."""
        callback = CostTrackingCallback()
        
        callback.on_subcall_end(response="r", depth=1, cost=1.0)
        callback.reset()
        
        assert callback.get_total_cost() == 0.0
        assert len(callback.subcall_costs) == 0


class TestStreamingCallback:
    """Tests for StreamingCallback."""
    
    def test_default_output(self):
        """Test default output function."""
        callback = StreamingCallback()
        
        assert callback.output_func is print
    
    def test_custom_output(self):
        """Test custom output function."""
        output = []
        callback = StreamingCallback(output_func=output.append)
        
        callback.on_final(result="Answer")
        
        assert len(output) > 0
        assert "Answer" in output[0]
    
    def test_iteration_output(self):
        """Test iteration output."""
        output = []
        callback = StreamingCallback(output_func=output.append)
        
        callback.on_iteration_start(iteration=3, history=[])
        
        assert any("3" in s for s in output)
