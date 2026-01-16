"""
OpenAI-Compatible Providers
===========================

Providers for APIs that are OpenAI-compatible (Groq, Together, Mistral, etc.).
"""

from typing import Dict, Optional, Tuple
import os

from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    """Base class for OpenAI-compatible API providers.
    
    Many providers (Groq, Together, Mistral, etc.) use OpenAI's API format
    but with different base URLs and API keys.
    
    Example:
        >>> provider = GroqProvider("llama-3.3-70b-versatile")
        >>> response = provider.generate("Hello!")
    """
    
    # Override in subclasses
    BASE_URL: str = ""
    API_KEY_ENV: str = ""
    PROVIDER_NAME: str = "openai-compatible"
    
    # Pricing per 1M tokens (input, output)
    MODEL_PRICING: Dict[str, Tuple[float, float]] = {}
    MODEL_CONTEXT: Dict[str, int] = {}
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize provider.
        
        Args:
            model: Model name
            api_key: API key (or use env var)
            base_url: Override base URL
        """
        self._model = model
        self._api_key = api_key or os.getenv(self.API_KEY_ENV)
        self._base_url = base_url or self.BASE_URL
        self._client = None
        
        # Set pricing
        pricing = self.MODEL_PRICING.get(model, (1.0, 2.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        """Lazy load OpenAI-compatible client."""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._base_url,
                )
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
        """Generate completion using OpenAI-compatible API."""
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


# =============================================================================
# Groq Provider
# =============================================================================

class GroqProvider(OpenAICompatibleProvider):
    """Groq LPU provider for ultra-fast inference.
    
    Example:
        >>> provider = GroqProvider("llama-3.3-70b-versatile")
        >>> response = provider.generate("Explain quantum computing")
    """
    
    BASE_URL = "https://api.groq.com/openai/v1"
    API_KEY_ENV = "GROQ_API_KEY"
    PROVIDER_NAME = "groq"
    
    MODEL_PRICING = {
        "llama-3.3-70b-versatile": (0.59, 0.79),
        "llama-3.1-70b-versatile": (0.59, 0.79),
        "llama-3.1-8b-instant": (0.05, 0.08),
        "llama-guard-3-8b": (0.20, 0.20),
        "mixtral-8x7b-32768": (0.24, 0.24),
        "gemma2-9b-it": (0.20, 0.20),
        "deepseek-r1-distill-llama-70b": (0.75, 0.99),
    }
    
    MODEL_CONTEXT = {
        "llama-3.3-70b-versatile": 128_000,
        "llama-3.1-70b-versatile": 128_000,
        "llama-3.1-8b-instant": 128_000,
        "mixtral-8x7b-32768": 32_768,
        "gemma2-9b-it": 8_192,
        "deepseek-r1-distill-llama-70b": 128_000,
    }


# =============================================================================
# Together AI Provider
# =============================================================================

class TogetherProvider(OpenAICompatibleProvider):
    """Together AI provider for open-source models.
    
    Example:
        >>> provider = TogetherProvider("meta-llama/Llama-3.3-70B-Instruct-Turbo")
        >>> response = provider.generate("Write a haiku")
    """
    
    BASE_URL = "https://api.together.xyz/v1"
    API_KEY_ENV = "TOGETHER_API_KEY"
    PROVIDER_NAME = "together"
    
    MODEL_PRICING = {
        "meta-llama/Llama-3.3-70B-Instruct-Turbo": (0.88, 0.88),
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": (3.50, 3.50),
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": (0.88, 0.88),
        "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": (0.18, 0.18),
        "mistralai/Mixtral-8x22B-Instruct-v0.1": (1.20, 1.20),
        "mistralai/Mistral-7B-Instruct-v0.3": (0.20, 0.20),
        "Qwen/Qwen2.5-72B-Instruct-Turbo": (1.20, 1.20),
        "deepseek-ai/DeepSeek-R1": (3.00, 7.00),
        "deepseek-ai/DeepSeek-V3": (0.50, 0.90),
    }
    
    MODEL_CONTEXT = {
        "meta-llama/Llama-3.3-70B-Instruct-Turbo": 128_000,
        "meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo": 128_000,
        "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo": 128_000,
        "deepseek-ai/DeepSeek-R1": 64_000,
        "deepseek-ai/DeepSeek-V3": 64_000,
    }


# =============================================================================
# Mistral AI Provider
# =============================================================================

class MistralProvider(OpenAICompatibleProvider):
    """Mistral AI provider.
    
    Example:
        >>> provider = MistralProvider("mistral-large-latest")
        >>> response = provider.generate("Explain transformers")
    """
    
    BASE_URL = "https://api.mistral.ai/v1"
    API_KEY_ENV = "MISTRAL_API_KEY"
    PROVIDER_NAME = "mistral"
    
    MODEL_PRICING = {
        "mistral-large-latest": (2.0, 6.0),
        "mistral-medium-latest": (2.7, 8.1),
        "mistral-small-latest": (0.2, 0.6),
        "codestral-latest": (0.3, 0.9),
        "open-mistral-nemo": (0.15, 0.15),
        "ministral-8b-latest": (0.1, 0.1),
    }
    
    MODEL_CONTEXT = {
        "mistral-large-latest": 128_000,
        "mistral-medium-latest": 32_000,
        "mistral-small-latest": 32_000,
        "codestral-latest": 32_000,
        "open-mistral-nemo": 128_000,
    }


# =============================================================================
# DeepSeek Provider
# =============================================================================

class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider (R1, V3).
    
    Example:
        >>> provider = DeepSeekProvider("deepseek-chat")
        >>> response = provider.generate("Solve this math problem: 2+2")
    """
    
    BASE_URL = "https://api.deepseek.com/v1"
    API_KEY_ENV = "DEEPSEEK_API_KEY"
    PROVIDER_NAME = "deepseek"
    
    MODEL_PRICING = {
        "deepseek-chat": (0.14, 0.28),        # DeepSeek-V3
        "deepseek-reasoner": (0.55, 2.19),    # DeepSeek-R1
    }
    
    MODEL_CONTEXT = {
        "deepseek-chat": 64_000,
        "deepseek-reasoner": 64_000,
    }


# =============================================================================
# Fireworks AI Provider
# =============================================================================

class FireworksProvider(OpenAICompatibleProvider):
    """Fireworks AI provider for fast inference.
    
    Example:
        >>> provider = FireworksProvider("accounts/fireworks/models/llama-v3p1-70b-instruct")
    """
    
    BASE_URL = "https://api.fireworks.ai/inference/v1"
    API_KEY_ENV = "FIREWORKS_API_KEY"
    PROVIDER_NAME = "fireworks"
    
    MODEL_PRICING = {
        "accounts/fireworks/models/llama-v3p3-70b-instruct": (0.90, 0.90),
        "accounts/fireworks/models/llama-v3p1-405b-instruct": (3.00, 3.00),
        "accounts/fireworks/models/qwen2p5-72b-instruct": (0.90, 0.90),
        "accounts/fireworks/models/deepseek-r1": (3.00, 8.00),
    }
    
    MODEL_CONTEXT = {
        "accounts/fireworks/models/llama-v3p3-70b-instruct": 128_000,
        "accounts/fireworks/models/llama-v3p1-405b-instruct": 128_000,
    }


# =============================================================================
# Perplexity Provider
# =============================================================================

class PerplexityProvider(OpenAICompatibleProvider):
    """Perplexity AI provider with online search.
    
    Example:
        >>> provider = PerplexityProvider("llama-3.1-sonar-large-128k-online")
    """
    
    BASE_URL = "https://api.perplexity.ai"
    API_KEY_ENV = "PERPLEXITY_API_KEY"
    PROVIDER_NAME = "perplexity"
    
    MODEL_PRICING = {
        "llama-3.1-sonar-small-128k-online": (0.20, 0.20),
        "llama-3.1-sonar-large-128k-online": (1.00, 1.00),
        "llama-3.1-sonar-huge-128k-online": (5.00, 5.00),
    }
    
    MODEL_CONTEXT = {
        "llama-3.1-sonar-small-128k-online": 128_000,
        "llama-3.1-sonar-large-128k-online": 128_000,
        "llama-3.1-sonar-huge-128k-online": 128_000,
    }


# =============================================================================
# Cerebras Provider
# =============================================================================

class CerebrasProvider(OpenAICompatibleProvider):
    """Cerebras Inference provider (fastest in the world).
    
    Example:
        >>> provider = CerebrasProvider("llama3.1-70b")
    """
    
    BASE_URL = "https://api.cerebras.ai/v1"
    API_KEY_ENV = "CEREBRAS_API_KEY"
    PROVIDER_NAME = "cerebras"
    
    MODEL_PRICING = {
        "llama3.1-8b": (0.10, 0.10),
        "llama3.1-70b": (0.60, 0.60),
        "llama-3.3-70b": (0.85, 0.85),
    }
    
    MODEL_CONTEXT = {
        "llama3.1-8b": 128_000,
        "llama3.1-70b": 128_000,
        "llama-3.3-70b": 128_000,
    }


# =============================================================================
# Azure OpenAI Provider
# =============================================================================

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider.
    
    Requires different configuration than standard OpenAI.
    
    Example:
        >>> provider = AzureOpenAIProvider(
        ...     deployment_name="gpt-4-deployment",
        ...     azure_endpoint="https://your-resource.openai.azure.com/",
        ... )
    """
    
    PRICE_PER_1M_INPUT = 5.0
    PRICE_PER_1M_OUTPUT = 15.0
    
    def __init__(
        self,
        deployment_name: str,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: str = "2024-02-01",
    ):
        self._deployment_name = deployment_name
        self._azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self._api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self._api_version = api_version
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(
                    api_key=self._api_key,
                    azure_endpoint=self._azure_endpoint,
                    api_version=self._api_version,
                )
            except ImportError:
                raise ImportError("openai package required")
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
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = client.chat.completions.create(
            model=self._deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        content = response.choices[0].message.content or ""
        usage = response.usage
        
        return LLMResponse(
            content=content,
            model=self._deployment_name,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return 128_000
    
    @property
    def model_name(self) -> str:
        return self._deployment_name


# =============================================================================
# vLLM Provider (Self-hosted)
# =============================================================================

class VLLMProvider(OpenAICompatibleProvider):
    """vLLM self-hosted provider.
    
    Example:
        >>> provider = VLLMProvider("meta-llama/Llama-3.1-70B", base_url="http://localhost:8000/v1")
    """
    
    BASE_URL = "http://localhost:8000/v1"
    API_KEY_ENV = "VLLM_API_KEY"
    PROVIDER_NAME = "vllm"
    
    MODEL_PRICING = {}  # Self-hosted, no pricing
    MODEL_CONTEXT = {}


# =============================================================================
# HuggingFace TGI Provider
# =============================================================================

class HuggingFaceTGIProvider(OpenAICompatibleProvider):
    """HuggingFace Text Generation Inference provider.
    
    Example:
        >>> provider = HuggingFaceTGIProvider("meta-llama/Llama-3.1-70B-Instruct")
    """
    
    BASE_URL = "https://api-inference.huggingface.co/v1"
    API_KEY_ENV = "HF_TOKEN"
    PROVIDER_NAME = "huggingface"
    
    MODEL_PRICING = {
        "meta-llama/Llama-3.1-70B-Instruct": (0.0, 0.0),  # Free tier
        "meta-llama/Llama-3.1-8B-Instruct": (0.0, 0.0),
        "mistralai/Mistral-7B-Instruct-v0.3": (0.0, 0.0),
    }
    
    MODEL_CONTEXT = {
        "meta-llama/Llama-3.1-70B-Instruct": 128_000,
        "meta-llama/Llama-3.1-8B-Instruct": 128_000,
    }


# =============================================================================
# OpenRouter Provider
# =============================================================================

class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter unified API for multiple providers.
    
    Example:
        >>> provider = OpenRouterProvider("anthropic/claude-3.5-sonnet")
    """
    
    BASE_URL = "https://openrouter.ai/api/v1"
    API_KEY_ENV = "OPENROUTER_API_KEY"
    PROVIDER_NAME = "openrouter"
    
    MODEL_PRICING = {
        "anthropic/claude-3.5-sonnet": (3.0, 15.0),
        "openai/gpt-4o": (5.0, 15.0),
        "google/gemini-pro-1.5": (1.25, 5.0),
        "meta-llama/llama-3.3-70b-instruct": (0.40, 0.40),
        "deepseek/deepseek-r1": (0.55, 2.19),
        "qwen/qwen-2.5-72b-instruct": (0.35, 0.40),
    }
    
    MODEL_CONTEXT = {
        "anthropic/claude-3.5-sonnet": 200_000,
        "openai/gpt-4o": 128_000,
        "google/gemini-pro-1.5": 2_000_000,
    }


# =============================================================================
# LocalAI Provider (Self-hosted)
# =============================================================================

class LocalAIProvider(OpenAICompatibleProvider):
    """LocalAI self-hosted provider.
    
    Example:
        >>> provider = LocalAIProvider("llama-3-8b", base_url="http://localhost:8080/v1")
    """
    
    BASE_URL = "http://localhost:8080/v1"
    API_KEY_ENV = ""  # No key needed for local
    PROVIDER_NAME = "localai"
    
    MODEL_PRICING = {}
    MODEL_CONTEXT = {}


# =============================================================================
# LM Studio Provider (Local)
# =============================================================================

class LMStudioProvider(OpenAICompatibleProvider):
    """LM Studio local provider.
    
    Example:
        >>> provider = LMStudioProvider("local-model", base_url="http://localhost:1234/v1")
    """
    
    BASE_URL = "http://localhost:1234/v1"
    API_KEY_ENV = ""  # No key needed
    PROVIDER_NAME = "lmstudio"
    
    MODEL_PRICING = {}
    MODEL_CONTEXT = {}


# =============================================================================
# Anyscale Provider
# =============================================================================

class AnyscaleProvider(OpenAICompatibleProvider):
    """Anyscale Endpoints provider.
    
    Example:
        >>> provider = AnyscaleProvider("meta-llama/Llama-3-70b-chat-hf")
    """
    
    BASE_URL = "https://api.endpoints.anyscale.com/v1"
    API_KEY_ENV = "ANYSCALE_API_KEY"
    PROVIDER_NAME = "anyscale"
    
    MODEL_PRICING = {
        "meta-llama/Llama-3-70b-chat-hf": (1.00, 1.00),
        "mistralai/Mixtral-8x7B-Instruct-v0.1": (0.50, 0.50),
    }
    
    MODEL_CONTEXT = {
        "meta-llama/Llama-3-70b-chat-hf": 8_192,
        "mistralai/Mixtral-8x7B-Instruct-v0.1": 32_768,
    }


# =============================================================================
# Lepton AI Provider
# =============================================================================

class LeptonProvider(OpenAICompatibleProvider):
    """Lepton AI provider.
    
    Example:
        >>> provider = LeptonProvider("llama3-70b")
    """
    
    BASE_URL = "https://llama3-70b.lepton.run/api/v1"
    API_KEY_ENV = "LEPTON_API_KEY"
    PROVIDER_NAME = "lepton"
    
    MODEL_PRICING = {
        "llama3-70b": (0.80, 0.80),
        "llama3-8b": (0.20, 0.20),
        "mixtral-8x7b": (0.50, 0.50),
    }
    
    MODEL_CONTEXT = {
        "llama3-70b": 8_192,
        "llama3-8b": 8_192,
    }


# =============================================================================
# SambaNova Provider
# =============================================================================

class SambaNovaProvider(OpenAICompatibleProvider):
    """SambaNova Cloud provider (ultra-fast).
    
    Example:
        >>> provider = SambaNovaProvider("Meta-Llama-3.1-70B-Instruct")
    """
    
    BASE_URL = "https://api.sambanova.ai/v1"
    API_KEY_ENV = "SAMBANOVA_API_KEY"
    PROVIDER_NAME = "sambanova"
    
    MODEL_PRICING = {
        "Meta-Llama-3.1-70B-Instruct": (0.60, 0.60),
        "Meta-Llama-3.1-8B-Instruct": (0.10, 0.10),
        "Meta-Llama-3.1-405B-Instruct": (5.00, 5.00),
    }
    
    MODEL_CONTEXT = {
        "Meta-Llama-3.1-70B-Instruct": 128_000,
        "Meta-Llama-3.1-8B-Instruct": 128_000,
        "Meta-Llama-3.1-405B-Instruct": 128_000,
    }


# =============================================================================
# AI21 Labs Provider
# =============================================================================

class AI21Provider(OpenAICompatibleProvider):
    """AI21 Labs Jamba provider.
    
    Example:
        >>> provider = AI21Provider("jamba-1.5-large")
    """
    
    BASE_URL = "https://api.ai21.com/studio/v1"
    API_KEY_ENV = "AI21_API_KEY"
    PROVIDER_NAME = "ai21"
    
    MODEL_PRICING = {
        "jamba-1.5-large": (2.0, 8.0),
        "jamba-1.5-mini": (0.2, 0.4),
    }
    
    MODEL_CONTEXT = {
        "jamba-1.5-large": 256_000,
        "jamba-1.5-mini": 256_000,
    }


# =============================================================================
# Cohere Provider
# =============================================================================

class CohereProvider(LLMProvider):
    """Cohere Command provider.
    
    Uses Cohere's native API (not OpenAI-compatible).
    
    Example:
        >>> provider = CohereProvider("command-r-plus")
    """
    
    MODEL_PRICING = {
        "command-r-plus": (2.5, 10.0),
        "command-r": (0.15, 0.60),
        "command-light": (0.30, 0.60),
    }
    
    MODEL_CONTEXT = {
        "command-r-plus": 128_000,
        "command-r": 128_000,
        "command-light": 4_096,
    }
    
    def __init__(
        self,
        model: str = "command-r-plus",
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._api_key = api_key or os.getenv("COHERE_API_KEY")
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (2.5, 10.0))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                import cohere
                self._client = cohere.Client(api_key=self._api_key)
            except ImportError:
                raise ImportError("cohere package required. pip install cohere")
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
        
        response = client.chat(
            model=self._model,
            message=prompt,
            preamble=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return LLMResponse(
            content=response.text,
            model=self._model,
            tokens_in=response.meta.tokens.input_tokens if response.meta else 0,
            tokens_out=response.meta.tokens.output_tokens if response.meta else 0,
            raw=response,
        )
    
    @property
    def max_context(self) -> int:
        return self.MODEL_CONTEXT.get(self._model, 128_000)
    
    @property
    def model_name(self) -> str:
        return self._model


# =============================================================================
# Replicate Provider
# =============================================================================

class ReplicateProvider(LLMProvider):
    """Replicate provider for open-source models.
    
    Example:
        >>> provider = ReplicateProvider("meta/llama-3.1-405b-instruct")
    """
    
    MODEL_PRICING = {
        "meta/llama-3.1-405b-instruct": (0.95, 0.95),
        "meta/llama-3.1-70b-instruct": (0.65, 0.65),
        "meta/llama-3.1-8b-instruct": (0.05, 0.05),
    }
    
    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
    ):
        self._model = model
        self._api_key = api_key or os.getenv("REPLICATE_API_TOKEN")
        self._client = None
        
        pricing = self.MODEL_PRICING.get(model, (0.5, 0.5))
        self.PRICE_PER_1M_INPUT = pricing[0]
        self.PRICE_PER_1M_OUTPUT = pricing[1]
    
    def _get_client(self):
        if self._client is None:
            try:
                import replicate
                self._client = replicate.Client(api_token=self._api_key)
            except ImportError:
                raise ImportError("replicate package required. pip install replicate")
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
        
        output = client.run(
            self._model,
            input={
                "prompt": full_prompt,
                "max_tokens": max_tokens or 1024,
                "temperature": temperature,
            }
        )
        
        content = "".join(output) if output else ""
        
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_in=len(full_prompt) // 4,  # Approximate
            tokens_out=len(content) // 4,
            raw=output,
        )
    
    @property
    def max_context(self) -> int:
        return 128_000
    
    @property
    def model_name(self) -> str:
        return self._model
