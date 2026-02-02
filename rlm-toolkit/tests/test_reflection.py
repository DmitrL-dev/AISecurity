"""
Tests for RLM v2.4 Reflection Callback.

Tests:
- ActionResult tracking
- Reflector implementations
- ReflectionCallback integration
- Quality scoring
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

from rlm_toolkit.callbacks.reflection import (
    ReflectionCallback,
    Reflection,
    ActionResult,
    ReflectorBase,
    LLMReflector,
    SimpleReflector,
    create_hmem_store_func,
)


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_creation(self):
        """ActionResult should be created with fields."""
        result = ActionResult(
            action_id="action-123",
            action_type="llm_call",
            input="Hello",
            output="Hi there!",
            success=True,
            latency_ms=150.0
        )

        assert result.action_id == "action-123"
        assert result.action_type == "llm_call"
        assert result.input == "Hello"
        assert result.output == "Hi there!"
        assert result.success is True
        assert result.latency_ms == 150.0

    def test_with_error(self):
        """ActionResult should support failed actions."""
        result = ActionResult(
            action_id="action-456",
            action_type="llm_call",
            input="Bad prompt",
            output="Rate limit exceeded",
            success=False
        )

        assert result.success is False
        assert result.output == "Rate limit exceeded"


class TestReflection:
    """Tests for Reflection dataclass."""

    def test_creation(self):
        """Reflection should be created with fields."""
        reflection = Reflection(
            action_id="action-123",
            analysis="Good response, on topic",
            quality_score=0.85,
            improvements=["Could be more detailed"],
            learnings=["Fast response achieved"]
        )

        assert reflection.action_id == "action-123"
        assert reflection.analysis == "Good response, on topic"
        assert reflection.quality_score == 0.85
        assert len(reflection.improvements) == 1
        assert len(reflection.learnings) == 1

    def test_timestamp(self):
        """Reflection should have timestamp."""
        reflection = Reflection(
            action_id="action-123",
            analysis="Test",
            quality_score=0.5
        )

        assert reflection.timestamp is not None
        assert isinstance(reflection.timestamp, datetime)

    def test_to_dict(self):
        """to_dict should return all fields."""
        reflection = Reflection(
            action_id="action-123",
            analysis="Test",
            quality_score=0.75
        )

        d = reflection.to_dict()

        assert d["action_id"] == "action-123"
        assert d["analysis"] == "Test"
        assert d["quality_score"] == 0.75
        assert "timestamp" in d


class TestSimpleReflector:
    """Tests for SimpleReflector."""

    def test_creation(self):
        """SimpleReflector should be created."""
        reflector = SimpleReflector()
        assert reflector is not None

    def test_reflect_success(self):
        """Should reflect on successful action."""
        reflector = SimpleReflector()

        action_result = ActionResult(
            action_id="test-1",
            action_type="llm_call",
            input="What is 2+2?",
            output="2+2 equals 4",
            success=True,
            latency_ms=100
        )

        reflection = reflector.reflect(action_result)

        assert reflection is not None
        assert 0.0 <= reflection.quality_score <= 1.0
        assert reflection.action_id == "test-1"

    def test_reflect_failure(self):
        """Should reflect on failed action with lower score."""
        reflector = SimpleReflector()

        action_result = ActionResult(
            action_id="test-2",
            action_type="llm_call",
            input="test",
            output="Timeout error",
            success=False
        )

        reflection = reflector.reflect(action_result)

        assert reflection.quality_score < 0.5

    def test_latency_affects_score(self):
        """High latency should lower score."""
        reflector = SimpleReflector()

        fast_result = ActionResult(
            action_id="fast",
            action_type="llm_call",
            input="p",
            output="r",
            success=True,
            latency_ms=50
        )

        slow_result = ActionResult(
            action_id="slow",
            action_type="llm_call",
            input="p",
            output="r",
            success=True,
            latency_ms=10000
        )

        fast_reflection = reflector.reflect(fast_result)
        slow_reflection = reflector.reflect(slow_result)

        assert fast_reflection.quality_score >= slow_reflection.quality_score


class TestLLMReflector:
    """Tests for LLMReflector."""

    def test_creation(self):
        """LLMReflector should be created with LLM function."""
        def mock_llm(prompt):
            return '{"quality_score": 0.8, "analysis": "Good"}'

        reflector = LLMReflector(llm_func=mock_llm)
        assert reflector is not None

    def test_reflect_uses_llm(self):
        """Should use LLM for reflection."""
        llm_calls = []

        def mock_llm(prompt):
            llm_calls.append(prompt)
            return '{"quality_score": 0.9, "analysis": "Excellent response"}'

        reflector = LLMReflector(llm_func=mock_llm)

        action_result = ActionResult(
            action_id="test",
            action_type="llm_call",
            input="test",
            output="response",
            success=True
        )

        reflection = reflector.reflect(action_result)

        assert len(llm_calls) == 1
        assert reflection is not None
        assert reflection.quality_score == 0.9


class TestReflectionCallback:
    """Tests for ReflectionCallback."""

    def test_creation(self):
        """ReflectionCallback should be created."""
        callback = ReflectionCallback()
        assert callback is not None

    def test_with_custom_reflector(self):
        """Should accept custom reflector."""
        reflector = SimpleReflector()
        callback = ReflectionCallback(reflector=reflector)

        assert callback.reflector is reflector

    def test_on_llm_start(self):
        """on_llm_start should record action start."""
        callback = ReflectionCallback()

        callback.on_llm_start(prompt="Hello")

        assert callback._pending_action is not None
        assert callback._pending_action.input == "Hello"

    def test_on_llm_end(self):
        """on_llm_end should complete action and trigger reflection."""
        callback = ReflectionCallback()

        callback.on_llm_start(prompt="What is AI?")
        callback.on_llm_end(response="AI is artificial intelligence")

        assert len(callback._reflections) == 1

    def test_on_llm_error(self):
        """on_llm_error should record failure."""
        callback = ReflectionCallback()

        callback.on_llm_start(prompt="test")
        callback.on_llm_error(error=ValueError("Test error"))

        # Errors always trigger reflection
        assert len(callback._reflections) == 1
        assert callback._reflections[0].quality_score < 0.5

    def test_frequency(self):
        """Should respect reflection frequency."""
        callback = ReflectionCallback(frequency=3)

        # Only every 3rd action should trigger reflection
        for i in range(6):
            callback.on_llm_start(prompt=f"prompt {i}")
            callback.on_llm_end(response=f"response {i}")

        # Should have 2 reflections (at actions 3 and 6)
        assert len(callback._reflections) == 2

    def test_store_func(self):
        """Should call custom store function."""
        stored = []

        def store(reflection):
            stored.append(reflection)

        callback = ReflectionCallback(store_func=store)

        callback.on_llm_start(prompt="test")
        callback.on_llm_end(response="response")

        assert len(stored) == 1

    def test_reflections_property(self):
        """reflections property should return all reflections."""
        callback = ReflectionCallback()

        for i in range(3):
            callback.on_llm_start(prompt=f"p{i}")
            callback.on_llm_end(response=f"r{i}")

        reflections = callback.reflections
        assert len(reflections) == 3

    def test_get_summary(self):
        """get_summary should return statistics."""
        callback = ReflectionCallback()

        for i in range(5):
            callback.on_llm_start(prompt=f"p{i}")
            callback.on_llm_end(response=f"r{i}")

        summary = callback.get_summary()

        assert "total_reflections" in summary
        assert "average_quality" in summary
        assert summary["total_reflections"] == 5

    def test_clear(self):
        """clear should remove all reflections."""
        callback = ReflectionCallback()

        callback.on_llm_start(prompt="test")
        callback.on_llm_end(response="response")

        assert len(callback._reflections) == 1

        callback.clear()

        assert len(callback._reflections) == 0


class TestHMEMIntegration:
    """Tests for H-MEM integration."""

    def test_create_hmem_store_func(self):
        """create_hmem_store_func should create store function."""
        # Create mock memory bridge
        mock_bridge = Mock()

        store_func = create_hmem_store_func(mock_bridge)

        assert callable(store_func)

        # Test calling it
        reflection = Reflection(
            action_id="test",
            analysis="Test analysis",
            quality_score=0.8
        )
        store_func(reflection)

        mock_bridge.add_fact.assert_called_once()


class TestIntegration:
    """Integration tests for reflection system."""

    def test_full_workflow(self):
        """Test complete reflection workflow."""
        callback = ReflectionCallback(
            reflector=SimpleReflector(),
            frequency=1
        )

        # Simulate several LLM calls
        prompts_responses = [
            ("What is Python?", "Python is a programming language"),
            ("How to sort a list?", "Use the sort() method"),
            ("Explain recursion", "Recursion is when a function calls itself"),
        ]

        for prompt, response in prompts_responses:
            callback.on_llm_start(prompt=prompt)
            callback.on_llm_end(response=response)

        summary = callback.get_summary()

        assert summary["total_reflections"] == 3
        assert summary["average_quality"] > 0
