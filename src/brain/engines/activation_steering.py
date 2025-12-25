"""
Activation Steering Safety Layer - Controlling LLM Behavior via Steering Vectors

Based on 2025 research:
  "Activation steering leverages contrastive activation pairs to create
   'steering vectors' that can amplify or suppress specific behaviors"

Capabilities:
  - Amplify safety/refusal behaviors
  - Suppress harmful/jailbreak tendencies
  - Apply task-specific behavioral modifiers
  - Real-time intervention during generation

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import OrderedDict
import hashlib
import json

logger = logging.getLogger("ActivationSteering")


# ============================================================================
# Enums and Data Classes
# ============================================================================


class SteeringDirection(str, Enum):
    """Direction to steer the model behavior."""

    AMPLIFY = "amplify"  # Enhance target behavior
    SUPPRESS = "suppress"  # Reduce target behavior
    NEUTRAL = "neutral"  # No steering


class SafetyBehavior(str, Enum):
    """Target safety behaviors for steering."""

    REFUSAL = "refusal"  # Refuse harmful requests
    HONESTY = "honesty"  # Truthful responses
    HELPFULNESS = "helpfulness"  # Helpful assistance
    HARMLESSNESS = "harmlessness"  # Avoid harmful content
    COMPLIANCE = "compliance"  # Follow instructions
    CREATIVITY = "creativity"  # Creative responses
    FORMALITY = "formality"  # Formal tone


class SteeringStrength(str, Enum):
    """Strength of steering intervention."""

    SUBTLE = "subtle"  # 0.1-0.3 multiplier
    MODERATE = "moderate"  # 0.3-0.6 multiplier
    STRONG = "strong"  # 0.6-0.9 multiplier
    MAXIMUM = "maximum"  # 0.9-1.0 multiplier


@dataclass
class SteeringVector:
    """
    A steering vector that can modify model activations.

    Created from contrastive pairs (positive, negative examples).
    """

    id: str
    behavior: SafetyBehavior
    direction: SteeringDirection
    layer_id: int
    vector: np.ndarray
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def scaled_vector(self, multiplier: float = 1.0) -> np.ndarray:
        """Get vector scaled by strength and multiplier."""
        sign = 1.0 if self.direction == SteeringDirection.AMPLIFY else -1.0
        return self.vector * self.strength * multiplier * sign

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "behavior": self.behavior.value,
            "direction": self.direction.value,
            "layer_id": self.layer_id,
            "strength": self.strength,
            "vector_norm": float(np.linalg.norm(self.vector)),
            "metadata": self.metadata,
        }


@dataclass
class SteeringProfile:
    """Collection of steering vectors for a safety objective."""

    id: str
    name: str
    description: str
    vectors: List[SteeringVector]
    target_layers: List[int]
    enabled: bool = True

    def get_vectors_for_layer(self, layer_id: int) -> List[SteeringVector]:
        """Get all vectors targeting a specific layer."""
        return [v for v in self.vectors if v.layer_id == layer_id]


@dataclass
class SteeringResult:
    """Result from applying steering."""

    profile_id: str
    layers_modified: List[int]
    vectors_applied: int
    total_strength: float
    intervention_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "layers_modified": self.layers_modified,
            "vectors_applied": self.vectors_applied,
            "total_strength": self.total_strength,
            "intervention_type": self.intervention_type,
        }


# ============================================================================
# Steering Vector Factory
# ============================================================================


class SteeringVectorFactory:
    """
    Creates steering vectors from contrastive activation pairs.

    The key insight is that behavioral differences manifest as
    consistent activation differences that can be extracted and reapplied.
    """

    @staticmethod
    def from_contrastive_pairs(
        positive_activations: List[np.ndarray],
        negative_activations: List[np.ndarray],
        behavior: SafetyBehavior,
        layer_id: int,
        direction: SteeringDirection = SteeringDirection.AMPLIFY,
    ) -> SteeringVector:
        """
        Create steering vector from contrastive activation pairs.

        Args:
            positive_activations: Activations from positive examples (desired behavior)
            negative_activations: Activations from negative examples (undesired behavior)
            behavior: Target safety behavior
            layer_id: Which layer this vector targets
            direction: Whether to amplify or suppress

        Returns:
            SteeringVector that can modify activations
        """
        # Compute mean activations
        pos_mean = np.mean([a.flatten() for a in positive_activations], axis=0)
        neg_mean = np.mean([a.flatten() for a in negative_activations], axis=0)

        # Steering vector is the difference
        vector = pos_mean - neg_mean

        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        vector_id = hashlib.sha256(
            f"{behavior.value}_{layer_id}_{direction.value}".encode()
        ).hexdigest()[:12]

        return SteeringVector(
            id=vector_id,
            behavior=behavior,
            direction=direction,
            layer_id=layer_id,
            vector=vector,
            strength=1.0,
            metadata={
                "positive_count": len(positive_activations),
                "negative_count": len(negative_activations),
                "norm": float(norm),
            },
        )

    @staticmethod
    def create_synthetic_vector(
        behavior: SafetyBehavior,
        layer_id: int,
        hidden_size: int = 768,
        direction: SteeringDirection = SteeringDirection.AMPLIFY,
    ) -> SteeringVector:
        """
        Create a synthetic steering vector (for testing/demonstration).

        In production, vectors should be computed from real contrastive pairs.
        """
        # Create a random but deterministic vector based on behavior/layer
        seed = hash(f"{behavior.value}_{layer_id}") % (2**32)
        rng = np.random.RandomState(seed)

        vector = rng.randn(hidden_size)
        vector = vector / np.linalg.norm(vector)

        vector_id = f"synthetic_{behavior.value}_{layer_id}"

        return SteeringVector(
            id=vector_id,
            behavior=behavior,
            direction=direction,
            layer_id=layer_id,
            vector=vector,
            strength=0.5,  # Lower strength for synthetic
            metadata={"synthetic": True},
        )


# ============================================================================
# Safety Profiles
# ============================================================================


class SafetyProfileLibrary:
    """
    Pre-defined safety profiles for common use cases.
    """

    # Target layers for different model sizes
    LAYER_CONFIGS = {
        "small": [6, 7, 8],  # ~125M params
        "medium": [12, 13, 14, 15],  # ~350M-1B params
        "large": [20, 21, 22, 23],  # ~7B+ params
        "default": [15, 16, 17],  # Generic mid-layers
    }

    @classmethod
    def create_maximum_safety_profile(
        cls, hidden_size: int = 768, model_size: str = "default"
    ) -> SteeringProfile:
        """Create profile for maximum safety (refusal + harmlessness)."""
        target_layers = cls.LAYER_CONFIGS.get(model_size, cls.LAYER_CONFIGS["default"])

        vectors = []
        for layer_id in target_layers:
            # Amplify refusal
            vectors.append(
                SteeringVectorFactory.create_synthetic_vector(
                    SafetyBehavior.REFUSAL,
                    layer_id,
                    hidden_size,
                    SteeringDirection.AMPLIFY,
                )
            )
            # Amplify harmlessness
            vectors.append(
                SteeringVectorFactory.create_synthetic_vector(
                    SafetyBehavior.HARMLESSNESS,
                    layer_id,
                    hidden_size,
                    SteeringDirection.AMPLIFY,
                )
            )

        return SteeringProfile(
            id="max_safety",
            name="Maximum Safety",
            description="Maximizes refusal and harmlessness behaviors",
            vectors=vectors,
            target_layers=target_layers,
        )

    @classmethod
    def create_balanced_profile(
        cls, hidden_size: int = 768, model_size: str = "default"
    ) -> SteeringProfile:
        """Create balanced profile (safety + helpfulness)."""
        target_layers = cls.LAYER_CONFIGS.get(model_size, cls.LAYER_CONFIGS["default"])

        vectors = []
        for layer_id in target_layers:
            # Moderate refusal
            v = SteeringVectorFactory.create_synthetic_vector(
                SafetyBehavior.REFUSAL, layer_id, hidden_size, SteeringDirection.AMPLIFY
            )
            v.strength = 0.5
            vectors.append(v)

            # Amplify helpfulness
            vectors.append(
                SteeringVectorFactory.create_synthetic_vector(
                    SafetyBehavior.HELPFULNESS,
                    layer_id,
                    hidden_size,
                    SteeringDirection.AMPLIFY,
                )
            )

            # Amplify honesty
            vectors.append(
                SteeringVectorFactory.create_synthetic_vector(
                    SafetyBehavior.HONESTY,
                    layer_id,
                    hidden_size,
                    SteeringDirection.AMPLIFY,
                )
            )

        return SteeringProfile(
            id="balanced",
            name="Balanced Safety",
            description="Balances safety with helpfulness and honesty",
            vectors=vectors,
            target_layers=target_layers,
        )

    @classmethod
    def create_anti_jailbreak_profile(
        cls, hidden_size: int = 768, model_size: str = "default"
    ) -> SteeringProfile:
        """Create profile specifically targeting jailbreak resistance."""
        target_layers = cls.LAYER_CONFIGS.get(model_size, cls.LAYER_CONFIGS["default"])

        vectors = []
        for layer_id in target_layers:
            # Strong refusal
            v = SteeringVectorFactory.create_synthetic_vector(
                SafetyBehavior.REFUSAL, layer_id, hidden_size, SteeringDirection.AMPLIFY
            )
            v.strength = 0.9
            vectors.append(v)

            # Suppress compliance (with jailbreak attempts)
            v = SteeringVectorFactory.create_synthetic_vector(
                SafetyBehavior.COMPLIANCE,
                layer_id,
                hidden_size,
                SteeringDirection.SUPPRESS,
            )
            v.strength = 0.7
            vectors.append(v)

        return SteeringProfile(
            id="anti_jailbreak",
            name="Anti-Jailbreak",
            description="Maximum resistance to jailbreak attempts",
            vectors=vectors,
            target_layers=target_layers,
        )


# ============================================================================
# Main Activation Steering Engine
# ============================================================================


class ActivationSteeringEngine:
    """
    Main engine for applying activation steering to LLM generation.

    Usage:
        engine = ActivationSteeringEngine()

        # Load a safety profile
        engine.load_profile(SafetyProfileLibrary.create_maximum_safety_profile())

        # Apply steering to activations during generation
        modified_activations = engine.steer(original_activations, layer_id=15)
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.profiles: Dict[str, SteeringProfile] = {}
        self.active_profile_id: Optional[str] = None
        self.steering_history: List[SteeringResult] = []
        self.global_strength: float = 1.0

        logger.info("ActivationSteeringEngine initialized")

    def load_profile(self, profile: SteeringProfile) -> None:
        """Load a steering profile."""
        self.profiles[profile.id] = profile
        logger.info(f"Loaded profile: {profile.name} ({len(profile.vectors)} vectors)")

    def activate_profile(self, profile_id: str) -> bool:
        """Activate a profile for steering."""
        if profile_id not in self.profiles:
            logger.warning(f"Profile not found: {profile_id}")
            return False

        self.active_profile_id = profile_id
        logger.info(f"Activated profile: {profile_id}")
        return True

    def deactivate(self) -> None:
        """Deactivate steering."""
        self.active_profile_id = None
        logger.info("Steering deactivated")

    def set_global_strength(self, strength: float) -> None:
        """Set global strength multiplier (0-1)."""
        self.global_strength = max(0.0, min(1.0, strength))

    def steer(
        self, activations: np.ndarray, layer_id: int, context: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Optional[SteeringResult]]:
        """
        Apply steering to layer activations.

        Args:
            activations: Original activations from the layer
            layer_id: Which layer these activations are from
            context: Optional context for adaptive steering

        Returns:
            (modified_activations, steering_result)
        """
        if self.active_profile_id is None:
            return activations, None

        profile = self.profiles.get(self.active_profile_id)
        if profile is None or not profile.enabled:
            return activations, None

        if layer_id not in profile.target_layers:
            return activations, None

        # Get vectors for this layer
        vectors = profile.get_vectors_for_layer(layer_id)
        if not vectors:
            return activations, None

        # Apply steering
        modified = activations.copy()
        total_strength = 0.0

        for vector in vectors:
            # Ensure vector matches activation shape
            if len(vector.vector) != modified.shape[-1]:
                continue

            scaled = vector.scaled_vector(self.global_strength)

            # Add steering vector to activations
            if len(modified.shape) == 3:
                # (batch, seq, hidden)
                modified = modified + scaled.reshape(1, 1, -1)
            elif len(modified.shape) == 2:
                # (seq, hidden) or (batch, hidden)
                modified = modified + scaled.reshape(1, -1)
            else:
                modified = modified + scaled

            total_strength += vector.strength * self.global_strength

        result = SteeringResult(
            profile_id=self.active_profile_id,
            layers_modified=[layer_id],
            vectors_applied=len(vectors),
            total_strength=total_strength,
            intervention_type="additive",
        )

        self.steering_history.append(result)

        return modified, result

    def steer_all_layers(
        self, hidden_states: Dict[int, np.ndarray], context: Optional[Dict] = None
    ) -> Tuple[Dict[int, np.ndarray], List[SteeringResult]]:
        """
        Apply steering across all layers.

        Args:
            hidden_states: Dict of layer_id -> activations
            context: Optional context

        Returns:
            (modified_hidden_states, results)
        """
        modified = {}
        results = []

        for layer_id, activations in hidden_states.items():
            modified_act, result = self.steer(activations, layer_id, context)
            modified[layer_id] = modified_act
            if result:
                results.append(result)

        return modified, results

    def get_active_profile(self) -> Optional[SteeringProfile]:
        """Get currently active profile."""
        if self.active_profile_id:
            return self.profiles.get(self.active_profile_id)
        return None

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all loaded profiles."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "vectors": len(p.vectors),
                "enabled": p.enabled,
                "active": p.id == self.active_profile_id,
            }
            for p in self.profiles.values()
        ]

    def analyze(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Analyze text and determine appropriate steering configuration.

        Standard API method for engine consistency.

        Args:
            text: Input text to analyze
            context: Optional context with risk_score, threat type

        Returns:
            Dict with recommended steering profile
        """
        ctx = context or {}
        risk_score = ctx.get("risk_score", 0.5)

        # Determine recommended profile based on risk
        if risk_score >= 0.8:
            recommended_profile = "anti_jailbreak"
            if "anti_jailbreak" not in self.profiles:
                self.load_profile(SafetyProfileLibrary.create_anti_jailbreak_profile())
        elif risk_score >= 0.5:
            recommended_profile = "max_safety"
            if "max_safety" not in self.profiles:
                self.load_profile(SafetyProfileLibrary.create_maximum_safety_profile())
        else:
            recommended_profile = "balanced"
            if "balanced" not in self.profiles:
                self.load_profile(SafetyProfileLibrary.create_balanced_profile())

        return {
            "risk_score": risk_score,
            "recommended_profile": recommended_profile,
            "available_profiles": list(self.profiles.keys()),
            "active_profile": self.active_profile_id,
            "global_strength": self.global_strength,
            "stats": self.get_stats(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "profiles_loaded": len(self.profiles),
            "active_profile": self.active_profile_id,
            "global_strength": self.global_strength,
            "total_interventions": len(self.steering_history),
            "recent_interventions": [r.to_dict() for r in self.steering_history[-10:]],
        }
