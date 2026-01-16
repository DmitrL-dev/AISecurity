"""
OpenAI Provider
===============

OpenAI API provider (GPT-4, GPT-5).
"""

from typing import Optional

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider.
    
    Example:
        >>> provider = OpenAIProvider("gpt-5.2")
        >>> response = provider.generate("Hello!")
        >>> print(response.content)
    """
    
    # Pricing per 1M tokens (January 2026)
    MODEL_PRICING = {
        "gpt-5.2": (10.0, 30.0),       # $10/M in, $30/M out
        "gpt-5": (8.0, 24.0),
        "gpt-4o": (5.0, 15.0),
        "gpt-4o-mini": (0.15, 0.60),   # Cheap for sub-calls
        "gpt-4.1": (2.0, 8.0),
        "o3-mini": (1.10, 4.40),
    }
    
    # Context windows
    MODEL_CONTEXT = {
        "gpt-5.2": 4_000_000,   # 4M tokens
        "gpt-5": 2_000_000,
        "gpt-4o": 128_000,
        "gpt-4o-mini": 128_000,
        "gpt-4.1": 128_000,
        "o3-mini": 200_000,
    }
    
    def __init__(
        self,
        model: str = "gpt-5.2",
        api_key: Optional[str] = None,
    ):
        """Initialize OpenAI provider.
        
        Args:
            model: Model name
            api_key: OpenAI API key (or OPENAI_API_KEY env var)
        """
        self._model = model
        self._api_key = api_key
        self._client = None
        
        # Set pricing
        pricing = self.MODEL_PRICING.get(model, (5.0, 15.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "openai package required. Install with: pip install openai"
                )
        return self._client
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using OpenAI."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        content = response.choices[0].message.content or ""
        usage = response.usage
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return self.MODEL_CONTEXT.get(self._model, 128_000)
    
    @property
    def model_name(self) -> str:
        return self._model
