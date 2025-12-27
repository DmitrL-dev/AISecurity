"""
Unit tests for Activation Steering Safety Layer.
"""

import pytest
import numpy as np
from activation_steering import (
    ActivationSteeringEngine,
    SteeringVector,
    SteeringVectorFactory,
    SteeringProfile,
    SafetyProfileLibrary,
    SafetyBehavior,
    SteeringDirection,
)


class TestSteeringVector:
    """Tests for SteeringVector."""

    def test_scaled_vector_amplify(self):
        """Test vector scaling with amplify direction."""
        vector = SteeringVector(
            id="test",
            behavior=SafetyBehavior.REFUSAL,
            direction=SteeringDirection.AMPLIFY,
            layer_id=15,
            vector=np.array([1.0, 0.0, 0.0]),
            strength=0.5
        )

        scaled = vector.scaled_vector(multiplier=2.0)

        # Amplify: positive sign
        assert np.allclose(scaled, [1.0, 0.0, 0.0])  # 1.0 * 0.5 * 2.0 * 1.0

    def test_scaled_vector_suppress(self):
        """Test vector scaling with suppress direction."""
        vector = SteeringVector(
            id="test",
            behavior=SafetyBehavior.COMPLIANCE,
            direction=SteeringDirection.SUPPRESS,
            layer_id=15,
            vector=np.array([1.0, 0.0, 0.0]),
            strength=0.5
        )

        scaled = vector.scaled_vector(multiplier=2.0)

        # Suppress: negative sign
        assert np.allclose(scaled, [-1.0, 0.0, 0.0])

    def test_to_dict(self):
        """Test serialization."""
        vector = SteeringVector(
            id="test",
            behavior=SafetyBehavior.HONESTY,
            direction=SteeringDirection.AMPLIFY,
            layer_id=10,
            vector=np.array([1.0, 2.0, 3.0]),
            strength=0.8
        )

        d = vector.to_dict()

        assert d["id"] == "test"
        assert d["behavior"] == "honesty"
        assert d["direction"] == "amplify"
        assert d["strength"] == 0.8


class TestSteeringVectorFactory:
    """Tests for SteeringVectorFactory."""

    def test_create_synthetic_vector(self):
        """Test synthetic vector creation."""
        vector = SteeringVectorFactory.create_synthetic_vector(
            behavior=SafetyBehavior.REFUSAL,
            layer_id=15,
            hidden_size=768
        )

        assert vector.behavior == SafetyBehavior.REFUSAL
        assert vector.layer_id == 15
        assert len(vector.vector) == 768
        assert vector.metadata.get("synthetic") == True

    def test_from_contrastive_pairs(self):
        """Test vector creation from contrastive pairs."""
        positive = [np.ones(10) for _ in range(5)]
        negative = [np.zeros(10) for _ in range(5)]

        vector = SteeringVectorFactory.from_contrastive_pairs(
            positive_activations=positive,
            negative_activations=negative,
            behavior=SafetyBehavior.HARMLESSNESS,
            layer_id=20
        )

        assert vector.behavior == SafetyBehavior.HARMLESSNESS
        assert vector.layer_id == 20
        assert len(vector.vector) == 10
        # Positive - Negative = all ones, normalized
        assert np.allclose(np.linalg.norm(vector.vector), 1.0)


class TestSafetyProfileLibrary:
    """Tests for pre-defined safety profiles."""

    def test_maximum_safety_profile(self):
        """Test maximum safety profile creation."""
        profile = SafetyProfileLibrary.create_maximum_safety_profile(
            hidden_size=512,
            model_size="default"
        )

        assert profile.id == "max_safety"
        assert len(profile.vectors) > 0
        assert profile.enabled

    def test_balanced_profile(self):
        """Test balanced profile creation."""
        profile = SafetyProfileLibrary.create_balanced_profile(
            hidden_size=512
        )

        assert profile.id == "balanced"
        # Should have multiple behavior types
        behaviors = set(v.behavior for v in profile.vectors)
        assert SafetyBehavior.HELPFULNESS in behaviors or SafetyBehavior.HONESTY in behaviors

    def test_anti_jailbreak_profile(self):
        """Test anti-jailbreak profile creation."""
        profile = SafetyProfileLibrary.create_anti_jailbreak_profile(
            hidden_size=512
        )

        assert profile.id == "anti_jailbreak"
        # Should have refusal vectors
        refusal_vectors = [
            v for v in profile.vectors if v.behavior == SafetyBehavior.REFUSAL]
        assert len(refusal_vectors) > 0


class TestActivationSteeringEngine:
    """Tests for main engine."""

    def setup_method(self):
        self.engine = ActivationSteeringEngine()

    def test_load_profile(self):
        """Test profile loading."""
        profile = SafetyProfileLibrary.create_maximum_safety_profile()
        self.engine.load_profile(profile)

        assert "max_safety" in self.engine.profiles

    def test_activate_profile(self):
        """Test profile activation."""
        profile = SafetyProfileLibrary.create_balanced_profile()
        self.engine.load_profile(profile)

        success = self.engine.activate_profile("balanced")

        assert success
        assert self.engine.active_profile_id == "balanced"

    def test_activate_nonexistent_profile(self):
        """Test activating non-existent profile."""
        success = self.engine.activate_profile("nonexistent")

        assert not success
        assert self.engine.active_profile_id is None

    def test_steer_without_active_profile(self):
        """Test steering without active profile."""
        activations = np.random.randn(1, 10, 512)

        modified, result = self.engine.steer(activations, layer_id=15)

        assert np.array_equal(modified, activations)
        assert result is None

    def test_steer_with_active_profile(self):
        """Test steering with active profile."""
        profile = SafetyProfileLibrary.create_maximum_safety_profile(
            hidden_size=512
        )
        self.engine.load_profile(profile)
        self.engine.activate_profile("max_safety")

        activations = np.zeros((1, 10, 512))
        target_layer = profile.target_layers[0]

        modified, result = self.engine.steer(
            activations, layer_id=target_layer)

        # Should be modified
        assert not np.array_equal(modified, activations)
        assert result is not None
        assert result.vectors_applied > 0

    def test_steer_non_target_layer(self):
        """Test steering on non-target layer."""
        profile = SafetyProfileLibrary.create_maximum_safety_profile()
        self.engine.load_profile(profile)
        self.engine.activate_profile("max_safety")

        activations = np.random.randn(1, 10, 768)

        # Use layer not in target_layers
        modified, result = self.engine.steer(activations, layer_id=0)

        assert np.array_equal(modified, activations)
        assert result is None

    def test_global_strength(self):
        """Test global strength setting."""
        self.engine.set_global_strength(0.5)
        assert self.engine.global_strength == 0.5

        self.engine.set_global_strength(1.5)  # Should clamp
        assert self.engine.global_strength == 1.0

        self.engine.set_global_strength(-0.5)  # Should clamp
        assert self.engine.global_strength == 0.0

    def test_list_profiles(self):
        """Test listing profiles."""
        self.engine.load_profile(
            SafetyProfileLibrary.create_maximum_safety_profile())
        self.engine.load_profile(
            SafetyProfileLibrary.create_balanced_profile())

        profiles = self.engine.list_profiles()

        assert len(profiles) == 2
        assert any(p["id"] == "max_safety" for p in profiles)

    def test_get_stats(self):
        """Test statistics retrieval."""
        profile = SafetyProfileLibrary.create_anti_jailbreak_profile(
            hidden_size=256)
        self.engine.load_profile(profile)
        self.engine.activate_profile("anti_jailbreak")

        # Do some steering
        activations = np.zeros((1, 5, 256))
        for layer_id in profile.target_layers:
            self.engine.steer(activations, layer_id)

        stats = self.engine.get_stats()

        assert stats["profiles_loaded"] == 1
        assert stats["active_profile"] == "anti_jailbreak"
        assert stats["total_interventions"] > 0


class TestIntegration:
    """Integration tests."""

    def test_full_steering_pipeline(self):
        """Test complete steering pipeline."""
        engine = ActivationSteeringEngine()

        # Load and activate profile
        profile = SafetyProfileLibrary.create_maximum_safety_profile(
            hidden_size=256)
        engine.load_profile(profile)
        engine.activate_profile("max_safety")
        engine.set_global_strength(0.8)

        # Simulate hidden states
        hidden_states = {
            i: np.random.randn(1, 20, 256) for i in range(24)
        }

        # Steer all layers
        modified, results = engine.steer_all_layers(hidden_states)

        assert len(modified) == len(hidden_states)
        assert len(results) > 0

        # Check that target layers were modified
        for result in results:
            assert result.profile_id == "max_safety"

    def test_deactivation(self):
        """Test profile deactivation."""
        engine = ActivationSteeringEngine()
        profile = SafetyProfileLibrary.create_balanced_profile(hidden_size=128)
        engine.load_profile(profile)
        engine.activate_profile("balanced")

        assert engine.active_profile_id == "balanced"

        engine.deactivate()

        assert engine.active_profile_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
