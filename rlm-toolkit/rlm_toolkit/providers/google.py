"""
Google Provider
===============

Google AI provider (Gemini).
"""

from typing import Optional

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider.
    
    Example:
        >>> provider = GeminiProvider("gemini-3-pro")
        >>> response = provider.generate("Hello!")
    """
    
    # Pricing per 1M tokens (January 2026)
    MODEL_PRICING = {
        "gemini-3-pro": (1.25, 5.0),
        "gemini-2-ultra": (10.0, 30.0),
        "gemini-2.0-flash": (0.075, 0.30),
    }
    
    # Context windows
    MODEL_CONTEXT = {
        "gemini-3-pro": 10_000_000,  # 10M tokens!
        "gemini-2-ultra": 2_000_000,
        "gemini-2.0-flash": 1_000_000,
    }
    
    def __init__(
        self,
        model: str = "gemini-3-pro",
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._api_key = api_key
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (1.25, 5.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(self._model)
            except ImportError:
                raise ImportError(
                    "google-generativeai required. Install with: pip install google-generativeai"
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
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        generation_config = {
            "temperature": temperature,
        }
        if max_tokens:
            generation_config["max_output_tokens"] = max_tokens
        
        response = client.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        
        content = response.text if response.text else ""
        
        # Estimate tokens
        tokens_in = len(full_prompt.split()) * 1.3
        tokens_out = len(content.split()) * 1.3
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=int(tokens_in),
            tokens_out=int(tokens_out),
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return self.MODEL_CONTEXT.get(self._model, 1_000_000)
    
    @property
    def model_name(self) -> str:
        return self._model
