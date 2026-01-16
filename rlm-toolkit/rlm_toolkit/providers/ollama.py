"""
Ollama Provider
===============

Local LLM provider using Ollama.
"""

from typing import Optional

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama (local) LLM provider.
    
    Example:
        >>> provider = OllamaProvider("llama4")
        >>> response = provider.generate("Hello!")
        >>> print(response.content)
    """
    
    # Ollama is free (local)
    PRICE_PER_1M_INPUT = 0.0
    PRICE_PER_1M_OUTPUT = 0.0
    
    # Default context window (varies by model)
    DEFAULT_CONTEXT = 128_000
    
    def __init__(
        self,
        model: str = "llama4",
        base_url: str = "http://localhost:11434",
        context_window: Optional[int] = None,
    ):
        """Initialize Ollama provider.
        
        Args:
            model: Model name (e.g., "llama4", "qwen3:7b")
            base_url: Ollama server URL
            context_window: Override context window size
        """
        self._model = model
        self._base_url = base_url.rstrip('/')
        self._context_window = context_window or self.DEFAULT_CONTEXT
        self._client = None
    
    def _get_client(self):
        """Lazy load Ollama client."""
        if self._client is None:
            try:
                import ollama
                self._client = ollama.Client(host=self._base_url)
            except ImportError:
                raise ImportError(
                    "ollama package required. Install with: pip install ollama"
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
        """Generate completion using Ollama."""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        options = {"temperature": temperature}
        if max_tokens:
            options["num_predict"] = max_tokens
        
        response = client.chat(
            model=self._model,
            messages=messages,
            options=options,
        )
        
        content = response.get("message", {}).get("content", "")
        
        # Estimate tokens (Ollama doesn't always return token counts)
        tokens_in = len(prompt.split()) * 1.3
        tokens_out = len(content.split()) * 1.3
        
        if "eval_count" in response:
            tokens_out = response["eval_count"]
        if "prompt_eval_count" in response:
            tokens_in = response["prompt_eval_count"]
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=int(tokens_in),
            tokens_out=int(tokens_out),
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return self._context_window
    
    @property
    def model_name(self) -> str:
        return self._model
