"""
Provider Router for RLM MCP Server.

Routes LLM requests to appropriate providers:
- Ollama (local)
- OpenAI
- Anthropic  
- Google
"""

import os
import logging
from typing import Any, Dict, Optional
from enum import Enum

logger = logging.getLogger("rlm_mcp.providers")


class Provider(Enum):
    """Available LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class ProviderRouter:
    """Routes requests to appropriate LLM provider."""
    
    def __init__(self):
        """Initialize provider router with auto-detection."""
        self.available_providers: Dict[Provider, bool] = {}
        self.default_provider: Optional[Provider] = None
        self._detect_providers()
    
    def _detect_providers(self):
        """Detect available providers."""
        # Check Ollama
        self.available_providers[Provider.OLLAMA] = self._check_ollama()
        
        # Check API keys
        self.available_providers[Provider.OPENAI] = bool(os.getenv("OPENAI_API_KEY"))
        self.available_providers[Provider.ANTHROPIC] = bool(os.getenv("ANTHROPIC_API_KEY"))
        self.available_providers[Provider.GOOGLE] = bool(os.getenv("GOOGLE_API_KEY"))
        
        # Set default provider
        self._set_default_provider()
        
        logger.info(f"Available providers: {[p.value for p, v in self.available_providers.items() if v]}")
        logger.info(f"Default provider: {self.default_provider.value if self.default_provider else 'None'}")
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def _set_default_provider(self):
        """Set default provider based on availability."""
        # Priority: Ollama > OpenAI > Anthropic > Google
        priority = [Provider.OLLAMA, Provider.OPENAI, Provider.ANTHROPIC, Provider.GOOGLE]
        
        for provider in priority:
            if self.available_providers.get(provider):
                self.default_provider = provider
                return
        
        logger.warning("No LLM providers available!")
    
    def get_provider(self, preference: Optional[str] = None) -> Optional[Provider]:
        """
        Get provider by preference or default.
        
        Args:
            preference: Preferred provider name
        
        Returns:
            Provider enum or None
        """
        if preference:
            try:
                provider = Provider(preference.lower())
                if self.available_providers.get(provider):
                    return provider
            except ValueError:
                pass
        
        return self.default_provider
    
    async def generate(
        self,
        prompt: str,
        provider: Optional[Provider] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate text using specified or default provider.
        
        Args:
            prompt: The prompt to send
            provider: Provider to use (default if not specified)
            model: Model name override
            **kwargs: Additional provider-specific arguments
        
        Returns:
            Generated text
        """
        provider = provider or self.default_provider
        
        if not provider:
            raise RuntimeError("No LLM provider available")
        
        if provider == Provider.OLLAMA:
            return await self._generate_ollama(prompt, model, **kwargs)
        elif provider == Provider.OPENAI:
            return await self._generate_openai(prompt, model, **kwargs)
        elif provider == Provider.ANTHROPIC:
            return await self._generate_anthropic(prompt, model, **kwargs)
        elif provider == Provider.GOOGLE:
            return await self._generate_google(prompt, model, **kwargs)
        
        raise ValueError(f"Unknown provider: {provider}")
    
    async def _generate_ollama(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate using Ollama."""
        import httpx
        
        model = model or "llama3:8b"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    **kwargs
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()["response"]
    
    async def _generate_openai(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate using OpenAI."""
        # TODO: Implement OpenAI generation
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    async def _generate_anthropic(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate using Anthropic."""
        # TODO: Implement Anthropic generation
        raise NotImplementedError("Anthropic provider not yet implemented")
    
    async def _generate_google(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate using Google."""
        # TODO: Implement Google generation
        raise NotImplementedError("Google provider not yet implemented")
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status."""
        return {
            "available_providers": {p.value: v for p, v in self.available_providers.items()},
            "default_provider": self.default_provider.value if self.default_provider else None,
        }
