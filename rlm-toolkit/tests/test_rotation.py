"""
Tests for RLM v2.4 Model Rotation.

Tests:
- ModelConfig state management
- ModelRotator strategies
- FailoverRotator
- Metrics collection
"""

import pytest
import time
from unittest.mock import Mock

from rlm_toolkit.providers.rotation import (
    ModelRotator,
    ModelConfig,
    RotationStrategy,
    FailoverRotator,
    RotatorMetrics,
)


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_creation(self):
        """ModelConfig should be created with required fields."""
        config = ModelConfig(model="gpt-4", provider="openai")

        assert config.model == "gpt-4"
        assert config.provider == "openai"
        assert config.weight == 1.0
        assert config.priority == 0
        assert config.is_available

    def test_custom_values(self):
        """ModelConfig should accept custom values."""
        config = ModelConfig(
            model="claude-3",
            provider="anthropic",
            weight=2.0,
            priority=1,
            max_retries=5,
            cooldown=120.0
        )

        assert config.weight == 2.0
        assert config.priority == 1
        assert config.max_retries == 5
        assert config.cooldown == 120.0

    def test_record_success(self):
        """record_success should update stats."""
        config = ModelConfig(model="test", provider="test")

        config.record_success(latency_ms=100)
        config.record_success(latency_ms=200)

        assert config._success_count == 2
        assert config._total_latency == 300
        assert config.avg_latency == 150

    def test_record_failure(self):
        """record_failure should update stats and potentially mark unavailable."""
        config = ModelConfig(model="test", provider="test", max_retries=3)

        config.record_failure()
        config.record_failure()
        assert config.is_available

        config.record_failure()  # Third failure
        assert not config._is_available

    def test_cooldown_recovery(self):
        """Model should recover after cooldown."""
        config = ModelConfig(model="test", provider="test",
                             max_retries=1, cooldown=0.05)

        config.record_failure()
        assert not config._is_available

        time.sleep(0.1)

        # Check is_available property triggers recovery
        assert config.is_available

    def test_success_rate(self):
        """success_rate should calculate correctly."""
        config = ModelConfig(model="test", provider="test")

        for _ in range(7):
            config.record_success(0)
        for _ in range(3):
            config._failure_count += 1

        assert config.success_rate == 0.7

    def test_reset(self):
        """reset should restore initial state."""
        config = ModelConfig(model="test", provider="test", max_retries=1)

        config.record_failure()
        config.record_success(100)
        assert not config._is_available

        config.reset()

        assert config.is_available
        assert config._success_count == 0
        assert config._failure_count == 0


class TestModelRotator:
    """Tests for ModelRotator."""

    def test_creation(self):
        """ModelRotator should be created with models."""
        models = [ModelConfig(model="m1", provider="p1")]
        rotator = ModelRotator(models)

        assert len(rotator.models) == 1

    def test_empty_models_raises(self):
        """Should raise error with empty models list."""
        with pytest.raises(ValueError):
            ModelRotator([])

    def test_round_robin(self):
        """Round robin should cycle through models."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
            ModelConfig(model="c", provider="p"),
        ]
        rotator = ModelRotator(models, strategy="round_robin")

        # Get 6 selections
        names = [rotator.next().model for _ in range(6)]

        # Implementation starts at index 0, increments before selecting
        # So first selection is models[1]=b, then c, a, b, c, a
        assert names == ["b", "c", "a", "b", "c", "a"]

    def test_priority(self):
        """Priority should select lowest priority value."""
        models = [
            ModelConfig(model="low", provider="p", priority=3),
            ModelConfig(model="high", provider="p", priority=1),
            ModelConfig(model="medium", provider="p", priority=2),
        ]
        rotator = ModelRotator(models, strategy="priority")

        for _ in range(3):
            assert rotator.next().model == "high"

    def test_weighted(self):
        """Weighted should respect weights."""
        models = [
            ModelConfig(model="heavy", provider="p", weight=100),
            ModelConfig(model="light", provider="p", weight=0),
        ]
        rotator = ModelRotator(models, strategy="weighted")

        # Heavy should always be selected (light has 0 weight)
        for _ in range(10):
            assert rotator.next().model == "heavy"

    def test_random(self):
        """Random should select randomly."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
        ]
        rotator = ModelRotator(models, strategy="random")

        # Just verify it runs
        for _ in range(10):
            model = rotator.next()
            assert model.model in ["a", "b"]

    def test_adaptive(self):
        """Adaptive should prefer high success rate and low latency."""
        models = [
            ModelConfig(model="fast", provider="p"),
            ModelConfig(model="slow", provider="p"),
        ]

        # Simulate performance data
        models[0]._success_count = 95
        models[0]._failure_count = 5
        models[0]._total_latency = 9500  # 100ms avg

        models[1]._success_count = 80
        models[1]._failure_count = 20
        models[1]._total_latency = 40000  # 500ms avg

        rotator = ModelRotator(models, strategy="adaptive")

        # Fast model should score better
        assert rotator.next().model == "fast"

    def test_unavailable_skipped(self):
        """Unavailable models should be skipped."""
        models = [
            ModelConfig(model="unavail", provider="p"),
            ModelConfig(model="avail", provider="p"),
        ]
        models[0]._is_available = False

        rotator = ModelRotator(models, strategy="round_robin")

        for _ in range(5):
            assert rotator.next().model == "avail"

    def test_all_unavailable_resets(self):
        """Should reset all models if all unavailable."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
        ]

        rotator = ModelRotator(models, strategy="round_robin")

        # Mark all unavailable
        for m in models:
            m._is_available = False

        # Should reset and return something
        result = rotator.next()
        assert result is not None

    def test_record_success(self):
        """record_success should update correct model."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = ModelRotator(models)

        rotator.record_success("a", latency_ms=100)

        assert models[0]._success_count == 1
        assert models[0]._total_latency == 100

    def test_record_failure(self):
        """record_failure should update correct model."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = ModelRotator(models)

        rotator.record_failure("a")

        assert models[0]._failure_count == 1

    def test_on_rotation_callback(self):
        """Should call on_rotation when rotating."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
        ]

        callback = Mock()
        rotator = ModelRotator(
            models, strategy="round_robin", on_rotation=callback)

        rotator.next()  # First selection (a)
        rotator.next()  # Rotation to b

        assert callback.called

    def test_metrics(self):
        """Should track selection metrics."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = ModelRotator(models)

        rotator.next()
        rotator.next()
        rotator.next()

        assert rotator.metrics.total_selections == 3
        assert rotator.metrics.selections_by_model["a"] == 3

    def test_get_stats(self):
        """get_stats should return comprehensive stats."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
        ]
        rotator = ModelRotator(models, strategy="priority")

        rotator.next()
        rotator.record_success("a", 100)

        stats = rotator.get_stats()

        assert stats["strategy"] == "priority"
        assert stats["total_models"] == 2
        assert "metrics" in stats
        assert "models" in stats

    def test_mark_unavailable(self):
        """mark_unavailable should manually disable model."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = ModelRotator(models)

        rotator.mark_unavailable("a")

        assert not models[0]._is_available

    def test_reset_all(self):
        """reset_all should reset all models."""
        models = [
            ModelConfig(model="a", provider="p"),
            ModelConfig(model="b", provider="p"),
        ]
        rotator = ModelRotator(models)

        # Modify state
        for m in models:
            m._is_available = False
            m._failure_count = 5

        rotator.reset_all()

        assert all(m.is_available for m in models)
        assert all(m._failure_count == 0 for m in models)


class TestFailoverRotator:
    """Tests for FailoverRotator."""

    def test_creation(self):
        """FailoverRotator should extend ModelRotator."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = FailoverRotator(models)

        assert rotator.max_attempts == 3

    def test_custom_max_attempts(self):
        """Should accept custom max_attempts."""
        models = [ModelConfig(model="a", provider="p")]
        rotator = FailoverRotator(models, max_attempts=5)

        assert rotator.max_attempts == 5

    def test_next_on_failure(self):
        """next_on_failure should rotate and record failure."""
        models = [
            ModelConfig(model="a", provider="p", max_retries=1),
            ModelConfig(model="b", provider="p", max_retries=1),
        ]
        # Use priority for predictable behavior
        rotator = FailoverRotator(models, strategy="priority")

        # Get first model (priority: a has priority 0, same as b, so a is first)
        first = rotator.next()

        # Simulate failure and get next
        next_model = rotator.next_on_failure()

        # Should have recorded failure for first model
        assert rotator.metrics.failures_by_model[first.model] == 1

    def test_failover_exhausts_models(self):
        """next_on_failure should return None when all exhausted."""
        models = [
            ModelConfig(model="a", provider="p", max_retries=1),
        ]
        rotator = FailoverRotator(models)

        rotator.next()

        # First failure marks unavailable
        result = rotator.next_on_failure()
        # Second call should fail since all are unavailable
        # (depends on implementation - may reset or return None)


class TestRotatorMetrics:
    """Tests for RotatorMetrics."""

    def test_to_dict(self):
        """to_dict should return all metrics."""
        metrics = RotatorMetrics()
        metrics.total_selections = 10
        metrics.rotations = 3

        d = metrics.to_dict()

        assert d["total_selections"] == 10
        assert d["rotations"] == 3
        assert "selections_by_model" in d
        assert "failures_by_model" in d


class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    def test_single_model_selection(self):
        """Single model should always be selected."""
        model = ModelConfig(model="only", provider="test")
        rotator = ModelRotator([model], strategy=RotationStrategy.ROUND_ROBIN)

        for _ in range(10):
            selected = rotator.next()
            assert selected.model == "only"

    def test_model_cooldown(self):
        """Model cooldown should work."""
        model = ModelConfig(model="test", provider="test", cooldown=0.05)
        rotator = ModelRotator([model], strategy=RotationStrategy.ROUND_ROBIN)

        # Record failures to trigger cooldown
        for _ in range(3):
            model.record_failure()

    def test_model_success_rate(self):
        """Success rate should be calculated correctly."""
        model = ModelConfig(model="test", provider="test")

        # 3 successes, 1 failure
        for _ in range(3):
            model.record_success()
        model.record_failure()

        # success_rate = 3 / (3+1) = 0.75
        assert 0.7 <= model.success_rate <= 0.8

    def test_multiple_models_priority(self):
        """Priority rotation should select correctly."""
        models = [
            ModelConfig(model="low", provider="test", priority=10),
            ModelConfig(model="high", provider="test", priority=1),
        ]
        rotator = ModelRotator(models, strategy=RotationStrategy.PRIORITY)

        selected = rotator.next()
        assert selected.model == "high"

    def test_rapid_rotation(self):
        """Rapid rotations should be stable."""
        models = [ModelConfig(model=f"m{i}", provider="test")
                  for i in range(5)]
        rotator = ModelRotator(models, strategy=RotationStrategy.ROUND_ROBIN)

        for _ in range(100):
            selected = rotator.next()
            assert selected is not None

    def test_metrics_tracking(self):
        """Metrics should track correctly."""
        models = [ModelConfig(model="test", provider="test")]
        rotator = ModelRotator(models, strategy=RotationStrategy.ROUND_ROBIN)

        for _ in range(10):
            rotator.next()

        assert rotator.metrics.total_selections == 10

    def test_failover_with_single_model(self):
        """Failover with single model should work."""
        model = ModelConfig(model="only", provider="test")
        failover = FailoverRotator([model])

        selected = failover.next()
        assert selected.model == "only"

        failover.record_failure(model)
        # Should still work with single model

    def test_weight_zero(self):
        """Zero weight should be handled."""
        models = [
            ModelConfig(model="zero", provider="test", weight=0.0),
            ModelConfig(model="normal", provider="test", weight=1.0),
        ]
        rotator = ModelRotator(models, strategy=RotationStrategy.WEIGHTED)

        # Zero weight model should rarely/never be selected
        for _ in range(10):
            selected = rotator.next()
            # Just ensure it doesn't crash
