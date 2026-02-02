"""
Model Rotation for LLM Provider Failover.

Provides automatic model rotation for load balancing and failover.
Supports multiple strategies: round-robin, weighted, priority, and adaptive.

Example:
    >>> rotator = ModelRotator([
    ...     ModelConfig("gpt-4", provider="openai", priority=1),
    ...     ModelConfig("claude-3", provider="anthropic", priority=2),
    ... ], strategy="priority")
    >>> 
    >>> model = rotator.next()  # Returns highest priority available
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class RotationStrategy(Enum):
    """Model rotation strategies."""
    ROUND_ROBIN = "round_robin"  # Cycle through models
    WEIGHTED = "weighted"         # Random based on weights
    PRIORITY = "priority"         # Use highest priority available
    ADAPTIVE = "adaptive"         # Based on performance metrics
    RANDOM = "random"             # Random selection


@dataclass
class ModelConfig:
    """Configuration for a model in the rotation.

    Attributes:
        model: Model name/identifier
        provider: Provider name (openai, anthropic, etc.)
        weight: Weight for weighted selection (higher = more likely)
        priority: Priority for priority selection (lower = higher priority)
        max_retries: Max retries before rotating away
        cooldown: Seconds before model is retried after failure
        metadata: Additional model configuration
    """
    model: str
    provider: str = "default"
    weight: float = 1.0
    priority: int = 0
    max_retries: int = 3
    cooldown: float = 60.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Runtime state
    _is_available: bool = field(default=True, repr=False)
    _last_failure: Optional[float] = field(default=None, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _success_count: int = field(default=0, repr=False)
    _total_latency: float = field(default=0.0, repr=False)

    @property
    def is_available(self) -> bool:
        """Check if model is available (not in cooldown)."""
        if self._is_available:
            return True

        # Check if cooldown has expired
        if self._last_failure and (time.time() - self._last_failure) > self.cooldown:
            self._is_available = True
            self._failure_count = 0
            return True

        return False

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self._success_count + self._failure_count
        if total == 0:
            return 1.0
        return self._success_count / total

    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        if self._success_count == 0:
            return 0.0
        return self._total_latency / self._success_count

    def record_success(self, latency_ms: float = 0) -> None:
        """Record a successful call."""
        self._success_count += 1
        self._total_latency += latency_ms
        self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failure and potentially mark unavailable."""
        self._failure_count += 1
        self._last_failure = time.time()

        if self._failure_count >= self.max_retries:
            self._is_available = False
            logger.warning(
                f"Model '{self.model}' marked unavailable "
                f"after {self.max_retries} failures"
            )

    def reset(self) -> None:
        """Reset model state."""
        self._is_available = True
        self._last_failure = None
        self._failure_count = 0
        self._success_count = 0
        self._total_latency = 0.0


@dataclass
class RotatorMetrics:
    """Metrics for model rotator."""
    total_selections: int = 0
    selections_by_model: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int))
    failures_by_model: Dict[str, int] = field(
        default_factory=lambda: defaultdict(int))
    rotations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_selections": self.total_selections,
            "selections_by_model": dict(self.selections_by_model),
            "failures_by_model": dict(self.failures_by_model),
            "rotations": self.rotations,
        }


class ModelRotator:
    """Model rotator with multiple selection strategies.

    Args:
        models: List of model configurations
        strategy: Selection strategy
        on_rotation: Callback when rotation occurs

    Example:
        >>> rotator = ModelRotator([
        ...     ModelConfig("gpt-4", provider="openai", priority=1),
        ...     ModelConfig("gpt-3.5-turbo", provider="openai", priority=2),
        ...     ModelConfig("claude-3-sonnet", provider="anthropic", priority=3),
        ... ], strategy="priority")
        >>> 
        >>> # Get next model
        >>> model = rotator.next()
        >>> 
        >>> # Record result
        >>> rotator.record_success("gpt-4", latency_ms=150)
        >>> # or
        >>> rotator.record_failure("gpt-4")
    """

    def __init__(
        self,
        models: List[ModelConfig],
        strategy: str = "round_robin",
        on_rotation: Optional[Callable[[
            ModelConfig, ModelConfig], None]] = None,
        auth_store: Optional["AuthProfileStore"] = None,
    ):
        if not models:
            raise ValueError("At least one model is required")

        self.models = models
        self.strategy = RotationStrategy(strategy)
        self.on_rotation = on_rotation
        self._auth_store = auth_store

        self._current_index = 0
        self._current_model: Optional[ModelConfig] = None
        self._metrics = RotatorMetrics()

    @property
    def metrics(self) -> RotatorMetrics:
        """Get rotator metrics."""
        return self._metrics

    @property
    def current(self) -> Optional[ModelConfig]:
        """Get current model."""
        return self._current_model

    @property
    def available_models(self) -> List[ModelConfig]:
        """Get list of available models."""
        return [m for m in self.models if m.is_available]

    def next(self) -> ModelConfig:
        """Get next model based on strategy.

        Returns:
            Selected ModelConfig

        Raises:
            RuntimeError: If no models are available
        """
        available = self.available_models

        # Filter by auth profile availability (OpenClaw-inspired)
        if self._auth_store:
            available = [
                m for m in available
                if not self._auth_store.all_in_cooldown(m.provider)
            ]

        if not available:
            # Reset all models and try again
            logger.warning("No models available, resetting all")
            for model in self.models:
                model.reset()
            if self._auth_store:
                self._auth_store.reset_all()
            available = self.models

        previous = self._current_model

        if self.strategy == RotationStrategy.ROUND_ROBIN:
            model = self._round_robin(available)
        elif self.strategy == RotationStrategy.WEIGHTED:
            model = self._weighted(available)
        elif self.strategy == RotationStrategy.PRIORITY:
            model = self._priority(available)
        elif self.strategy == RotationStrategy.ADAPTIVE:
            model = self._adaptive(available)
        else:  # RANDOM
            model = random.choice(available)

        self._current_model = model
        self._metrics.total_selections += 1
        self._metrics.selections_by_model[model.model] += 1

        # Check if this is a rotation
        if previous and previous != model:
            self._metrics.rotations += 1
            if self.on_rotation:
                self.on_rotation(previous, model)
            logger.info(f"Rotated from '{previous.model}' to '{model.model}'")

        return model

    def _round_robin(self, available: List[ModelConfig]) -> ModelConfig:
        """Round-robin selection."""
        # Find next available model starting from current index
        for _ in range(len(self.models)):
            self._current_index = (self._current_index + 1) % len(self.models)
            model = self.models[self._current_index]
            if model in available:
                return model
        return available[0]

    def _weighted(self, available: List[ModelConfig]) -> ModelConfig:
        """Weighted random selection."""
        total_weight = sum(m.weight for m in available)
        if total_weight <= 0:
            return random.choice(available)

        r = random.uniform(0, total_weight)
        cumulative = 0
        for model in available:
            cumulative += model.weight
            if r <= cumulative:
                return model
        return available[-1]

    def _priority(self, available: List[ModelConfig]) -> ModelConfig:
        """Priority-based selection (lowest priority value = highest priority)."""
        return min(available, key=lambda m: m.priority)

    def _adaptive(self, available: List[ModelConfig]) -> ModelConfig:
        """Adaptive selection based on performance.

        Considers success rate and latency.
        Score = success_rate * 100 - (avg_latency / 100)
        """
        def score(model: ModelConfig) -> float:
            sr = model.success_rate * 100
            latency_penalty = model.avg_latency / 100 if model.avg_latency > 0 else 0
            return sr - latency_penalty

        return max(available, key=score)

    def record_success(self, model_name: str, latency_ms: float = 0) -> None:
        """Record successful call for a model.

        Args:
            model_name: Model name
            latency_ms: Call latency in milliseconds
        """
        for model in self.models:
            if model.model == model_name:
                model.record_success(latency_ms)
                return

    def record_failure(self, model_name: str) -> None:
        """Record failed call for a model.

        Args:
            model_name: Model name
        """
        for model in self.models:
            if model.model == model_name:
                model.record_failure()
                self._metrics.failures_by_model[model_name] += 1
                return

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """Get model by name."""
        for model in self.models:
            if model.model == name:
                return model
        return None

    def reset_all(self) -> None:
        """Reset all models to available state."""
        for model in self.models:
            model.reset()
        self._current_index = 0
        self._current_model = None
        logger.info("All models reset")

    def mark_unavailable(self, model_name: str) -> None:
        """Manually mark a model as unavailable.

        Args:
            model_name: Model name to mark
        """
        for model in self.models:
            if model.model == model_name:
                model._is_available = False
                model._last_failure = time.time()
                logger.info(f"Model '{model_name}' marked unavailable")
                return

    def get_api_key(self, model: ModelConfig) -> Optional[str]:
        """Get available API key for model's provider.

        Uses AuthProfileStore to get the best available key.

        Args:
            model: Model configuration

        Returns:
            API key string, or None if no auth store configured
        """
        if not self._auth_store:
            return None
        profile = self._auth_store.get_available(model.provider)
        return profile.api_key if profile else None

    def get_stats(self) -> Dict[str, Any]:
        """Get detailed statistics."""
        return {
            "strategy": self.strategy.value,
            "total_models": len(self.models),
            "available_models": len(self.available_models),
            "current_model": self._current_model.model if self._current_model else None,
            "metrics": self._metrics.to_dict(),
            "models": [
                {
                    "model": m.model,
                    "provider": m.provider,
                    "available": m.is_available,
                    "success_rate": round(m.success_rate, 3),
                    "avg_latency_ms": round(m.avg_latency, 2),
                    "failures": m._failure_count,
                }
                for m in self.models
            ],
        }


class FailoverRotator(ModelRotator):
    """Model rotator with automatic failover.

    Extends ModelRotator to automatically rotate on failure
    and retry with the next available model.

    Example:
        >>> rotator = FailoverRotator([...])
        >>> 
        >>> async def call_with_failover(prompt):
        ...     for attempt in range(rotator.max_attempts):
        ...         model = rotator.next()
        ...         try:
        ...             result = await llm.call(model.model, prompt)
        ...             rotator.record_success(model.model)
        ...             return result
        ...         except Exception as e:
        ...             rotator.record_failure(model.model)
        ...     raise RuntimeError("All models failed")
    """

    def __init__(
        self,
        models: List[ModelConfig],
        strategy: str = "priority",
        max_attempts: int = 3,
        **kwargs
    ):
        super().__init__(models, strategy, **kwargs)
        self.max_attempts = max_attempts

    def next_on_failure(self) -> Optional[ModelConfig]:
        """Get next model after a failure.

        Automatically records failure for current model.

        Returns:
            Next available model, or None if all exhausted
        """
        if self._current_model:
            self.record_failure(self._current_model.model)

        available = self.available_models
        if not available:
            return None

        return self.next()
