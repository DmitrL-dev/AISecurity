"""Unit tests for core engine module."""

import pytest
from unittest.mock import MagicMock

from rlm_toolkit.core.engine import RLM, RLMConfig, RLMResult
from rlm_toolkit.testing.mocks import MockProvider


class TestRLMConfig:
    """Tests for RLMConfig."""
    
    def test_default_config(self):
        """Test default config values."""
        config = RLMConfig()
        
        assert config.max_iterations > 0
        assert config.max_cost > 0
        assert config.max_execution_time > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RLMConfig(
            max_iterations=100,
            max_cost=50.0,
            max_execution_time=60.0,
        )
        
        assert config.max_iterations == 100
        assert config.max_cost == 50.0
        assert config.max_execution_time == 60.0
    
    def test_sandbox_default_enabled(self):
        """Test sandbox is enabled by default."""
        config = RLMConfig()
        assert config.sandbox is True
    
    def test_allowed_imports_default(self):
        """Test default allowed imports."""
        config = RLMConfig()
        
        assert "re" in config.allowed_imports
        assert "json" in config.allowed_imports
        assert "math" in config.allowed_imports


class TestRLMResult:
    """Tests for RLMResult."""
    
    def test_result_creation(self):
        """Test result creation."""
        result = RLMResult(
            answer="The answer is 42",
            status="success",
            iterations=5,
            total_cost=0.05,
            execution_time=2.5,
            subcall_count=3,
        )
        
        assert result.answer == "The answer is 42"
        assert result.status == "success"
        assert result.iterations == 5
        assert result.subcall_count == 3
    
    def test_result_success_property(self):
        """Test success property."""
        success = RLMResult(
            answer="done",
            status="success",
            iterations=1,
            total_cost=0.01,
            execution_time=1.0,
            subcall_count=0,
        )
        
        assert success.success is True
        
        failed = RLMResult(
            answer="error",
            status="error",
            iterations=1,
            total_cost=0.01,
            execution_time=1.0,
            subcall_count=0,
        )
        
        assert failed.success is False


class TestRLM:
    """Tests for RLM class."""
    
    def test_creation_with_provider(self):
        """Test RLM creation with provider."""
        provider = MockProvider()
        rlm = RLM(root=provider)
        
        assert rlm is not None
    
    def test_creation_with_config(self):
        """Test RLM creation with config."""
        provider = MockProvider()
        config = RLMConfig(max_iterations=10)
        
        rlm = RLM(root=provider, config=config)
        
        assert rlm.config.max_iterations == 10
    
    def test_run_basic(self):
        """Test basic run."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="test", query="What is 6*7?")
        
        assert result.status == "success"
        assert "42" in result.answer
    
    def test_run_with_iterations(self):
        """Test run with multiple iterations."""
        provider = MockProvider(responses=[
            "Let me calculate... ```python\nprint(6*7)\n```",
            "FINAL(42)",
        ])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="What is 6*7?")
        
        assert result.iterations >= 1
    
    def test_max_iterations_limit(self):
        """Test max iterations is enforced."""
        # Provider that never gives FINAL
        provider = MockProvider(responses=["Still thinking..."])
        config = RLMConfig(max_iterations=3)
        rlm = RLM(root=provider, config=config)
        
        result = rlm.run(context="", query="?")
        
        assert result.iterations <= 3
        assert result.status in ("max_iterations", "error", "success")
    
    def test_run_tracks_cost(self):
        """Test run tracks costs."""
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert result.total_cost >= 0.0
    
    def test_run_tracks_time(self):
        """Test run tracks execution time."""
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert result.execution_time >= 0.0


class TestRLMFactories:
    """Tests for RLM factory methods."""
    
    def test_from_ollama(self):
        """Test from_ollama factory."""
        rlm = RLM.from_ollama("llama3")
        
        assert rlm is not None
        assert rlm.root.model_name == "llama3"
    
    def test_from_openai(self):
        """Test from_openai factory."""
        rlm = RLM.from_openai("gpt-4o")
        
        assert rlm is not None
        assert rlm.root.model_name == "gpt-4o"
    
    def test_from_anthropic(self):
        """Test from_anthropic factory."""
        rlm = RLM.from_anthropic("claude-3-opus")
        
        assert rlm is not None


class TestRLMCallbacks:
    """Tests for RLM with callbacks."""
    
    def test_callbacks_fired(self):
        """Test callbacks are fired during run."""
        from rlm_toolkit.core.callbacks import RLMCallback
        
        class TestCallback(RLMCallback):
            def __init__(self):
                self.events = []
            
            def on_run_start(self, context, query, config):
                self.events.append("start")
            
            def on_final(self, result):
                self.events.append("final")
        
        callback = TestCallback()
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider, callbacks=[callback])
        
        rlm.run(context="", query="test")
        
        assert "start" in callback.events or "final" in callback.events
