"""Providers module - LLM provider implementations."""

from rlm_toolkit.providers.base import LLMProvider, LLMResponse
from rlm_toolkit.providers.retry import RetryConfig, Retrier
from rlm_toolkit.providers.rate_limit import RateLimiter, RateLimitConfig, get_rate_limiter

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "RetryConfig",
    "Retrier",
    "RateLimiter",
    "RateLimitConfig",
    "get_rate_limiter",
]

# Lazy imports for optional dependencies
def __getattr__(name):
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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

