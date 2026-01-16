"""Integration tests for RLM-Toolkit."""

import pytest
from rlm_toolkit.testing.mocks import MockProvider, SequenceProvider
from rlm_toolkit.providers.base import ResilientProvider
from rlm_toolkit.providers.retry import RetryConfig


class TestResilientProvider:
    """Tests for ResilientProvider with retry and rate limiting."""
    
    def test_basic_generate(self):
        """Test basic generation through resilient wrapper."""
        mock = MockProvider(responses="FINAL(test)")
        resilient = ResilientProvider(mock)
        
        result = resilient.generate("test prompt")
        assert result.content == "FINAL(test)"
    
    def test_retry_on_failure(self):
        """Test retry behavior on failures."""
        # Provider that fails twice then succeeds
        attempts = [0]
        
        class FailingProvider(MockProvider):
            def generate(self, prompt, **kwargs):
                attempts[0] += 1
                if attempts[0] < 3:
                    raise ConnectionError("Simulated failure")
                return super().generate(prompt, **kwargs)
        
        mock = FailingProvider(responses="FINAL(success)")
        retry_config = RetryConfig(max_retries=5, initial_delay=0.001)
        resilient = ResilientProvider(mock, retry_config=retry_config)
        
        result = resilient.generate("test")
        assert result.content == "FINAL(success)"
        assert attempts[0] == 3
    
    def test_rate_limiting_passthrough(self):
        """Test rate limiting doesn't block normal requests."""
        mock = MockProvider(responses="response")
        resilient = ResilientProvider(mock)
        
        # Should not raise
        for _ in range(5):
            resilient.generate("test")
        
        assert mock.call_count == 5
    
    def test_provider_name_detection(self):
        """Test automatic provider name detection."""
        mock = MockProvider()
        resilient = ResilientProvider(mock)
        
        # MockProvider should detect as unknown
        assert resilient._provider_name in ("unknown", "mock")
    
    def test_cost_delegation(self):
        """Test cost calculation is delegated to inner provider."""
        mock = MockProvider()
        resilient = ResilientProvider(mock)
        
        result = resilient.generate("test")
        cost = resilient.get_cost(result)
        
        # MockProvider has 0 pricing
        assert cost >= 0
    
    def test_properties_forwarded(self):
        """Test max_context and model_name are forwarded."""
        mock = MockProvider()
        resilient = ResilientProvider(mock)
        
        assert resilient.max_context == mock.max_context
        assert resilient.model_name == mock.model_name


class TestEndToEndFlow:
    """End-to-end integration tests."""
    
    def test_simple_query_flow(self):
        """Test simple query returning FINAL immediately."""
        from rlm_toolkit.testing.fixtures import create_test_rlm
        
        rlm = create_test_rlm(responses="FINAL(The answer is 42)")
        result = rlm.run(
            context="Life, the universe, and everything.",
            query="What is the answer?"
        )
        
        assert "42" in result.answer
        assert result.iterations >= 1
    
    def test_multi_iteration_flow(self):
        """Test multi-iteration processing."""
        from rlm_toolkit.testing.fixtures import create_test_rlm
        
        responses = [
            "```python\nx = 1 + 1\nprint(x)\n```",
            "```python\ny = x * 2\nprint(y)\n```", 
            "FINAL(The result is 4)",
        ]
        
        rlm = create_test_rlm(responses=responses)
        result = rlm.run(
            context="Test context",
            query="Calculate something"
        )
        
        assert "4" in result.answer or result.iterations >= 2
    
    def test_cost_tracking(self):
        """Test cost is tracked across iterations."""
        from rlm_toolkit.testing.fixtures import create_test_rlm
        
        rlm = create_test_rlm(responses="FINAL(done)")
        result = rlm.run(context="ctx", query="q")
        
        # Cost should be tracked (even if 0 for mock)
        assert hasattr(result, 'total_cost')
        assert result.total_cost >= 0
