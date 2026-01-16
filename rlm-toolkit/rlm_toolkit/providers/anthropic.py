"""
Anthropic Provider
==================

Anthropic API provider (Claude).
"""

from typing import Optional

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) LLM provider.
    
    Example:
        >>> provider = AnthropicProvider("claude-opus-4.5")
        >>> response = provider.generate("Hello!")
    """
    
    # Pricing per 1M tokens (January 2026)
    MODEL_PRICING = {
        "claude-opus-4.5": (15.0, 75.0),
        "claude-4-sonnet": (3.0, 15.0),
        "claude-haiku": (0.25, 1.25),
        "claude-3.5-sonnet": (3.0, 15.0),
    }
    
    # Context windows
    MODEL_CONTEXT = {
        "claude-opus-4.5": 2_000_000,
        "claude-4-sonnet": 200_000,
        "claude-haiku": 200_000,
        "claude-3.5-sonnet": 200_000,
    }
    
    def __init__(
        self,
        model: str = "claude-opus-4.5",
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._api_key = api_key
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (3.0, 15.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "anthropic package required. Install with: pip install anthropic"
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
        client = self._get_client()
        
        response = client.messages.create(
            model=self._model,
            max_tokens=max_tokens or 4096,
            system=system_prompt or "",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        
        content = response.content[0].text if response.content else ""
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return self.MODEL_CONTEXT.get(self._model, 200_000)
    
    @property
    def model_name(self) -> str:
        return self._model
