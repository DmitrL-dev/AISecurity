"""Providers module - LLM provider implementations."""

from rlm_toolkit.providers.base import LLMProvider, LLMResponse
from rlm_toolkit.providers.retry import RetryConfig, Retrier
from rlm_toolkit.providers.rate_limit import RateLimiter, RateLimitConfig, get_rate_limiter
from rlm_toolkit.providers.resilience import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    get_circuit_breaker,
    get_all_circuit_breakers,
    reset_all_circuit_breakers,
)
from rlm_toolkit.providers.pool import (
    ConnectionPool,
    PoolConfig,
    PooledConnection,
    get_connection_pool,
    close_connection_pool,
)
from rlm_toolkit.providers.rotation import (
    ModelRotator,
    ModelConfig,
    RotationStrategy,
    FailoverRotator,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "RetryConfig",
    "Retrier",
    "RateLimiter",
    "RateLimitConfig",
    "get_rate_limiter",
    # Circuit Breaker (v2.4)
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "CircuitState",
    "get_circuit_breaker",
    "get_all_circuit_breakers",
    "reset_all_circuit_breakers",
    # Connection Pool (v2.4)
    "ConnectionPool",
    "PoolConfig",
    "PooledConnection",
    "get_connection_pool",
    "close_connection_pool",
    # Model Rotation (v2.4)
    "ModelRotator",
    "ModelConfig",
    "RotationStrategy",
    "FailoverRotator",
    # Core Providers (4)
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    # OpenAI-compatible Cloud (17)
    "GroqProvider",
    "TogetherProvider",
    "MistralProvider",
    "DeepSeekProvider",
    "FireworksProvider",
    "PerplexityProvider",
    "CerebrasProvider",
    "AzureOpenAIProvider",
    "OpenRouterProvider",
    "AnyscaleProvider",
    "LeptonProvider",
    "SambaNovaProvider",
    "AI21Provider",
    # Self-hosted (4)
    "VLLMProvider",
    "HuggingFaceTGIProvider",
    "LocalAIProvider",
    "LMStudioProvider",
    # Native SDK (2)
    "CohereProvider",
    "ReplicateProvider",
    # Extended: International (8)
    "NVIDIAProvider",
    "QwenProvider",
    "ErnieProvider",
    "MoonshotProvider",
    "YiProvider",
    "ZhipuProvider",
    "MinimaxProvider",
    "BaichuanProvider",
    # Extended: Western (7)
    "XAIProvider",
    "RekaProvider",
    "WriterProvider",
    "VoyageProvider",
    "CloudflareProvider",
    "OctoAIProvider",
    "MonsterAPIProvider",
    # Extended: Cloud (5)
    "BedrockProvider",
    "VertexAIProvider",
    "SagemakerProvider",
    "ModalProvider",
    "RunPodProvider",
    "BasetenProvider",
]

# Compatible providers from compatible.py
_COMPATIBLE_PROVIDERS = {
    "GroqProvider", "TogetherProvider", "MistralProvider", "DeepSeekProvider",
    "FireworksProvider", "PerplexityProvider", "CerebrasProvider", "AzureOpenAIProvider",
    "VLLMProvider", "HuggingFaceTGIProvider", "OpenRouterProvider", "LocalAIProvider",
    "LMStudioProvider", "AnyscaleProvider", "LeptonProvider", "SambaNovaProvider",
    "AI21Provider", "CohereProvider", "ReplicateProvider",
}

# Extended providers from extended.py
_EXTENDED_PROVIDERS = {
    "NVIDIAProvider", "QwenProvider", "ErnieProvider", "MoonshotProvider",
    "YiProvider", "ZhipuProvider", "MinimaxProvider", "BaichuanProvider",
    "XAIProvider", "RekaProvider", "WriterProvider", "VoyageProvider",
    "CloudflareProvider", "OctoAIProvider", "MonsterAPIProvider",
    "BedrockProvider", "VertexAIProvider", "SagemakerProvider",
    "ModalProvider", "RunPodProvider", "BasetenProvider",
}

# Lazy imports


def __getattr__(name):
    # Core providers
    if name == "OllamaProvider":
        from rlm_toolkit.providers.ollama import OllamaProvider
        return OllamaProvider
    elif name == "OpenAIProvider":
        from rlm_toolkit.providers.openai import OpenAIProvider
        return OpenAIProvider
    elif name == "AnthropicProvider":
        from rlm_toolkit.providers.anthropic import AnthropicProvider
        return AnthropicProvider
    elif name == "GeminiProvider":
        from rlm_toolkit.providers.google import GeminiProvider
        return GeminiProvider

    # Compatible providers
    elif name in _COMPATIBLE_PROVIDERS:
        from rlm_toolkit.providers import compatible
        return getattr(compatible, name)

    # Extended providers
    elif name in _EXTENDED_PROVIDERS:
        from rlm_toolkit.providers import extended
        return getattr(extended, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
