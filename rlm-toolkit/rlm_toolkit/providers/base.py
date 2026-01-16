"""
LLM Provider Base
=================

Abstract base class for LLM providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.providers.retry import RetryConfig, Retrier
    from rlm_toolkit.providers.rate_limit import RateLimiter


@dataclass
class LLMResponse:
    """Response from LLM provider.
    
    Attributes:
        content: Generated text content
        model: Model used for generation
        tokens_in: Input tokens
        tokens_out: Output tokens
        raw: Raw response from provider
    """
    content: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    raw: Optional[Any] = None
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.tokens_in + self.tokens_out


class LLMProvider(ABC):
    """Abstract base class for LLM providers.
    
    Implement this to add new LLM providers.
    
    Example:
        >>> class MyProvider(LLMProvider):
        ...     def generate(self, prompt, **kwargs):
        ...         # Call your LLM API
        ...         return LLMResponse(content="...", model="...")
    """
    
    # Default pricing per 1M tokens (override in subclasses)
    PRICE_PER_1M_INPUT: float = 0.0
    PRICE_PER_1M_OUTPUT: float = 0.0
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate completion from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Provider-specific arguments
        
        Returns:
            LLMResponse with generated content
        """
        pass
    
    async def agenerate(
        self,
        prompt: str,
        **kwargs
    ) -> LLMResponse:
        """Async version of generate."""
        # Default: delegate to sync
        return self.generate(prompt, **kwargs)
    
    def get_cost(self, response: LLMResponse) -> float:
        """Calculate cost of response in USD.
        
        Args:
            response: LLM response with token counts
        
        Returns:
            Cost in USD
        """
        input_cost = (response.tokens_in / 1_000_000) * self.PRICE_PER_1M_INPUT
        output_cost = (response.tokens_out / 1_000_000) * self.PRICE_PER_1M_OUTPUT
        return input_cost + output_cost
    
    @property
    @abstractmethod
    def max_context(self) -> int:
        """Maximum context window size in tokens."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass


class ResilientProvider(LLMProvider):
    """Provider wrapper with retry and rate limiting.
    
    Wraps any LLMProvider with production-ready resilience.
    
    Example:
        >>> base = OpenAIProvider(model="gpt-4o")
        >>> provider = ResilientProvider(base)
        >>> result = provider.generate("Hello")  # With retry + rate limit
    """
    
    def __init__(
        self,
        inner: LLMProvider,
        retry_config: Optional["RetryConfig"] = None,
        rate_limiter: Optional["RateLimiter"] = None,
        provider_name: Optional[str] = None,
    ):
        """Initialize resilient provider.
        
        Args:
            inner: The underlying provider
            retry_config: Retry configuration (uses defaults if None)
            rate_limiter: Rate limiter (uses global if None)
            provider_name: Name for rate limiting (auto-detect if None)
        """
        self._inner = inner
        self._provider_name = provider_name or self._detect_provider_name()
        
        # Lazy import to avoid circular deps
        from rlm_toolkit.providers.retry import RetryConfig, Retrier
        from rlm_toolkit.providers.rate_limit import get_rate_limiter
        
        self._retry_config = retry_config or RetryConfig()
        self._retrier = Retrier(self._retry_config)
        self._rate_limiter = rate_limiter or get_rate_limiter()
    
    def _detect_provider_name(self) -> str:
        """Detect provider name from inner class."""
        name = self._inner.__class__.__name__.lower()
        if "openai" in name:
            return "openai"
        if "anthropic" in name:
            return "anthropic"
        if "google" in name or "gemini" in name:
            return "google"
        if "ollama" in name:
            return "ollama"
        return "unknown"
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate with retry and rate limiting."""
        # Rate limit
        self._rate_limiter.acquire(self._provider_name)
        
        # Execute with retry
        def _call():
            return self._inner.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
        
        return self._retrier.execute(_call)
    
    async def agenerate(self, prompt: str, **kwargs) -> LLMResponse:
        """Async generate with retry and rate limiting."""
        self._rate_limiter.acquire(self._provider_name)
        
        async def _call():
            return await self._inner.agenerate(prompt, **kwargs)
        
        return await self._retrier.aexecute(_call)
    
    def get_cost(self, response: LLMResponse) -> float:
        """Delegate to inner provider."""
        return self._inner.get_cost(response)
    
    @property
    def max_context(self) -> int:
        return self._inner.max_context
    
    @property
    def model_name(self) -> str:
        return self._inner.model_name
    
    # Forward pricing
    @property
    def PRICE_PER_1M_INPUT(self) -> float:
        return self._inner.PRICE_PER_1M_INPUT
    
    @property
    def PRICE_PER_1M_OUTPUT(self) -> float:
        return self._inner.PRICE_PER_1M_OUTPUT

