"""
SafeClaw Router — Base Provider Interface.

Abstract base class for all LLM provider adapters.
Per router_spec.md v1.0 (Approved 2026-02-10).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompletionResult:
    """Result of an LLM completion call."""

    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    cost_kopecks: float = 0.0
    finish_reason: str = "stop"

    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output


@dataclass(frozen=True)
class ProviderHealth:
    """Health status of a provider."""

    name: str
    available: bool
    latency_ms: float = 0.0
    models: list[str] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RoutingStrategy(str, Enum):
    """Strategy for selecting a provider."""

    COST = "cost"
    QUALITY = "quality"
    LATENCY = "latency"
    FAILOVER = "failover"


# Model aliases → ordered list of (provider, model) candidates
MODEL_ALIASES: dict[str, list[tuple[str, str]]] = {
    "fast": [
        ("deepseek", "deepseek-chat"),
        ("gigachat", "GigaChat"),
        ("qwen", "Qwen3-Coder-Next"),
        ("llama", "Llama-4-Scout"),
        ("yandexgpt", "yandexgpt-lite"),
    ],
    "smart": [
        ("deepseek", "deepseek-reasoner"),
        ("qwen", "Qwen3-Max-Thinking"),
        ("llama", "Llama-4-Maverick"),
        ("gigachat", "GigaChat-Pro"),
        ("yandexgpt", "yandexgpt"),
    ],
    "cheap": [
        ("tpro", "T-Pro-2.0"),
        ("qwen", "Qwen3-Coder-Next"),
        ("llama", "Llama-4-Scout"),
        ("deepseek", "deepseek-chat"),
        ("gigachat", "GigaChat"),
    ],
    "local": [
        ("tpro", "T-Pro-2.0"),
        ("qwen", "Qwen3-Max-Thinking"),
        ("llama", "Llama-4-Maverick"),
    ],
}


# ---------------------------------------------------------------------------
# Abstract Base Provider
# ---------------------------------------------------------------------------


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str = ""
    models: list[str] = []

    def __init__(
        self,
        api_key: str,
        base_url: str,
        models: list[str] | None = None,
        rate_limit: int = 60,
        cost_per_1k_input: float = 0,
        cost_per_1k_output: float = 0,
        **kwargs,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        if models:
            self.models = models
        self.rate_limit = rate_limit
        self.cost_per_1k_input = cost_per_1k_input
        self.cost_per_1k_output = cost_per_1k_output
        self._extra = kwargs

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        """Send completion request and return result."""
        ...

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Check if the provider is available."""
        ...

    def count_tokens_approx(self, text: str) -> int:
        """Approximate token count (≈ 4 chars per token for English/Russian)."""
        return max(1, len(text) // 4)

    def estimate_cost(self, tokens_in: int, tokens_out: int) -> float:
        """Estimate cost in kopecks."""
        cost_in = (tokens_in / 1000) * self.cost_per_1k_input
        cost_out = (tokens_out / 1000) * self.cost_per_1k_output
        return round(cost_in + cost_out, 2)

    def has_model(self, model: str) -> bool:
        """Check if provider supports the given model."""
        return model in self.models

    def _measure_latency(self):
        """Context-manager-like helper for measuring latency."""
        return _LatencyTimer()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name!r} " f"models={self.models}>"
        )


class _LatencyTimer:
    """Simple latency measurement helper."""

    def __init__(self):
        self.start = 0.0
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start) * 1000
