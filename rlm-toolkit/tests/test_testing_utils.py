"""Unit tests for testing utilities module."""

import pytest
from rlm_toolkit.testing.mocks import MockProvider, RecordingProvider, SequenceProvider
from rlm_toolkit.testing.fixtures import (
    sample_contexts,
    create_test_rlm,
    create_failing_rlm,
    create_multi_iteration_rlm,
    RLMTestCase,
)


class TestMockProvider:
    """Tests for MockProvider."""
    
    def test_default_response(self):
        """Test default response."""
        provider = MockProvider()
        response = provider.generate("test prompt")
        
        assert response.content is not None
        assert len(response.content) > 0
    
    def test_custom_responses(self):
        """Test custom responses."""
        provider = MockProvider(responses=["Answer 1", "Answer 2"])
        
        r1 = provider.generate("q1")
        r2 = provider.generate("q2")
        
        assert r1.content == "Answer 1"
        assert r2.content == "Answer 2"
    
    def test_response_cycling(self):
        """Test responses cycle to last."""
        provider = MockProvider(responses=["A", "B"])
        
        provider.generate("1")  # A
        provider.generate("2")  # B
        r3 = provider.generate("3")  # B (stays at last)
        
        assert r3.content == "B"
    
    def test_model_name(self):
        """Test model name."""
        provider = MockProvider(model="test-model")
        
        assert provider.model_name == "test-model"
    
    def test_max_context(self):
        """Test max context."""
        provider = MockProvider()
        
        assert provider.max_context > 0
    
    def test_call_count(self):
        """Test call count tracking."""
        provider = MockProvider()
        
        assert provider.call_count == 0
        provider.generate("1")
        assert provider.call_count == 1
        provider.generate("2")
        assert provider.call_count == 2
    
    def test_call_history(self):
        """Test call history tracking."""
        provider = MockProvider(responses=["done"])
        
        provider.generate("prompt 1")
        provider.generate("prompt 2")
        
        assert len(provider.history) == 2
        assert provider.history[0]["prompt"] == "prompt 1"
    
    def test_reset(self):
        """Test reset clears history."""
        provider = MockProvider()
        
        provider.generate("test")
        provider.reset()
        
        assert provider.call_count == 0
        assert len(provider.history) == 0
    
    def test_raise_on_call(self):
        """Test error injection."""
        provider = MockProvider(
            responses=["ok"],
            raise_on_call=2,
        )
        
        provider.generate("1")  # OK
        
        with pytest.raises(RuntimeError):
            provider.generate("2")  # Raises
    
    def test_callable_responses(self):
        """Test dynamic response function."""
        def response_fn(prompt, call_num):
            return f"Response {call_num}: {prompt[:10]}"
        
        provider = MockProvider(responses=response_fn)
        
        r = provider.generate("Hello world")
        assert "Response 1" in r.content


class TestRecordingProvider:
    """Tests for RecordingProvider."""
    
    def test_wraps_provider(self):
        """Test wrapping a provider."""
        inner = MockProvider(responses=["test"])
        recording = RecordingProvider(inner)
        
        response = recording.generate("prompt")
        
        assert response.content == "test"
    
    def test_records_calls(self):
        """Test call recording."""
        inner = MockProvider(responses=["r1", "r2"])
        recording = RecordingProvider(inner)
        
        recording.generate("p1")
        recording.generate("p2")
        
        assert len(recording.calls) == 2
        assert recording.calls[0]["prompt"] == "p1"
    
    def test_clear(self):
        """Test clearing records."""
        inner = MockProvider()
        recording = RecordingProvider(inner)
        
        recording.generate("test")
        recording.clear()
        
        assert len(recording.calls) == 0


class TestSequenceProvider:
    """Tests for SequenceProvider."""
    
    def test_sequence(self):
        """Test response sequence."""
        provider = SequenceProvider("A", "B", "C")
        
        assert provider.generate("1").content == "A"
        assert provider.generate("2").content == "B"
        assert provider.generate("3").content == "C"
    
    def test_no_cycle(self):
        """Test without cycling stays at last."""
        provider = SequenceProvider("A", "B", cycle=False)
        
        provider.generate("1")  # A
        provider.generate("2")  # B
        r = provider.generate("3")  # B
        
        assert r.content == "B"
    
    def test_with_cycle(self):
        """Test with cycling."""
        provider = SequenceProvider("A", "B", cycle=True)
        
        provider.generate("1")  # A
        provider.generate("2")  # B
        r = provider.generate("3")  # A
        
        assert r.content == "A"


class TestSampleContexts:
    """Tests for sample_contexts fixture."""
    
    def test_returns_dict(self):
        """Test returns dictionary."""
        contexts = sample_contexts()
        
        assert isinstance(contexts, dict)
        assert len(contexts) > 0
    
    def test_has_short_context(self):
        """Test has short context."""
        contexts = sample_contexts()
        
        assert "short" in contexts
        assert len(contexts["short"]) < 100


class TestCreateTestRLM:
    """Tests for create_test_rlm fixture."""
    
    def test_creates_rlm(self):
        """Test RLM creation."""
        rlm = create_test_rlm()
        
        assert rlm is not None
    
    def test_with_responses(self):
        """Test with custom responses."""
        rlm = create_test_rlm(responses=["FINAL(test)"])
        
        result = rlm.run(context="c", query="q")
        assert "test" in result.answer


class TestCreateFailingRLM:
    """Tests for create_failing_rlm fixture."""
    
    def test_creates_rlm(self):
        """Test creates RLM."""
        rlm = create_failing_rlm()
        
        assert rlm is not None


class TestCreateMultiIterationRLM:
    """Tests for create_multi_iteration_rlm fixture."""
    
    def test_creates_rlm(self):
        """Test creates RLM."""
        rlm = create_multi_iteration_rlm(iterations=3)
        
        assert rlm is not None


class TestRLMTestCase:
    """Tests for RLMTestCase base class."""
    
    def test_setup_method(self):
        """Test setup creates RLM."""
        tc = RLMTestCase()
        tc.setup_method()
        
        assert tc.rlm is not None
