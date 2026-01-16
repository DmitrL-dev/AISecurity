"""Tests for OpenAI-compatible providers."""

import pytest
from unittest.mock import MagicMock, patch

from rlm_toolkit.providers.compatible import (
    OpenAICompatibleProvider,
    GroqProvider,
    TogetherProvider,
    MistralProvider,
    DeepSeekProvider,
    FireworksProvider,
    PerplexityProvider,
    CerebrasProvider,
    AzureOpenAIProvider,
)
from rlm_toolkit.providers.base import LLMResponse


class TestOpenAICompatibleProvider:
    """Tests for base OpenAI-compatible provider."""
    
    def test_provider_initialization(self):
        """Test provider initializes correctly."""
        provider = GroqProvider("llama-3.3-70b-versatile")
        assert provider._model == "llama-3.3-70b-versatile"
        assert provider.BASE_URL == "https://api.groq.com/openai/v1"
        assert provider.PROVIDER_NAME == "groq"
    
    def test_pricing_from_model(self):
        """Test pricing is set from model."""
        provider = GroqProvider("llama-3.3-70b-versatile")
        assert provider.PRICE_PER_1M_INPUT == 0.59
        assert provider.PRICE_PER_1M_OUTPUT == 0.79
    
    def test_pricing_default_for_unknown_model(self):
        """Test default pricing for unknown model."""
        provider = GroqProvider("unknown-model")
        assert provider.PRICE_PER_1M_INPUT == 1.0
        assert provider.PRICE_PER_1M_OUTPUT == 2.0
    
    def test_max_context(self):
        """Test context window size."""
        provider = GroqProvider("llama-3.3-70b-versatile")
        assert provider.max_context == 128_000


class TestGroqProvider:
    """Tests for Groq provider."""
    
    def test_has_correct_models(self):
        """Test Groq has expected models."""
        assert "llama-3.3-70b-versatile" in GroqProvider.MODEL_PRICING
        assert "mixtral-8x7b-32768" in GroqProvider.MODEL_PRICING
        assert "deepseek-r1-distill-llama-70b" in GroqProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert GroqProvider.BASE_URL == "https://api.groq.com/openai/v1"
    
    def test_api_key_env(self):
        """Test correct env var."""
        assert GroqProvider.API_KEY_ENV == "GROQ_API_KEY"
    
    @patch.object(GroqProvider, "_get_client")
    def test_generate(self, mock_client):
        """Test generate method."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        
        mock_client.return_value.chat.completions.create.return_value = mock_response
        
        provider = GroqProvider("llama-3.3-70b-versatile")
        response = provider.generate("Hello")
        
        assert response.content == "Test response"
        assert response.tokens_in == 10
        assert response.tokens_out == 5


class TestTogetherProvider:
    """Tests for Together AI provider."""
    
    def test_has_correct_models(self):
        """Test Together has expected models."""
        assert "meta-llama/Llama-3.3-70B-Instruct-Turbo" in TogetherProvider.MODEL_PRICING
        assert "deepseek-ai/DeepSeek-R1" in TogetherProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert TogetherProvider.BASE_URL == "https://api.together.xyz/v1"


class TestMistralProvider:
    """Tests for Mistral AI provider."""
    
    def test_has_correct_models(self):
        """Test Mistral has expected models."""
        assert "mistral-large-latest" in MistralProvider.MODEL_PRICING
        assert "codestral-latest" in MistralProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert MistralProvider.BASE_URL == "https://api.mistral.ai/v1"


class TestDeepSeekProvider:
    """Tests for DeepSeek provider."""
    
    def test_has_correct_models(self):
        """Test DeepSeek has expected models."""
        assert "deepseek-chat" in DeepSeekProvider.MODEL_PRICING
        assert "deepseek-reasoner" in DeepSeekProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert DeepSeekProvider.BASE_URL == "https://api.deepseek.com/v1"


class TestFireworksProvider:
    """Tests for Fireworks AI provider."""
    
    def test_has_correct_models(self):
        """Test Fireworks has expected models."""
        assert "accounts/fireworks/models/llama-v3p3-70b-instruct" in FireworksProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert FireworksProvider.BASE_URL == "https://api.fireworks.ai/inference/v1"


class TestPerplexityProvider:
    """Tests for Perplexity AI provider."""
    
    def test_has_correct_models(self):
        """Test Perplexity has expected models."""
        assert "llama-3.1-sonar-large-128k-online" in PerplexityProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert PerplexityProvider.BASE_URL == "https://api.perplexity.ai"


class TestCerebrasProvider:
    """Tests for Cerebras provider."""
    
    def test_has_correct_models(self):
        """Test Cerebras has expected models."""
        assert "llama3.1-70b" in CerebrasProvider.MODEL_PRICING
    
    def test_base_url(self):
        """Test correct base URL."""
        assert CerebrasProvider.BASE_URL == "https://api.cerebras.ai/v1"


class TestAzureOpenAIProvider:
    """Tests for Azure OpenAI provider."""
    
    def test_initialization(self):
        """Test provider initializes correctly."""
        provider = AzureOpenAIProvider(
            deployment_name="gpt-4-deployment",
            azure_endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        assert provider._deployment_name == "gpt-4-deployment"
        assert provider._azure_endpoint == "https://test.openai.azure.com/"
        assert provider.model_name == "gpt-4-deployment"
    
    def test_max_context(self):
        """Test context window."""
        provider = AzureOpenAIProvider("test")
        assert provider.max_context == 128_000


class TestProviderImports:
    """Test providers can be imported from main module."""
    
    def test_import_groq(self):
        """Test Groq can be imported."""
        from rlm_toolkit.providers import GroqProvider
        assert GroqProvider is not None
    
    def test_import_together(self):
        """Test Together can be imported."""
        from rlm_toolkit.providers import TogetherProvider
        assert TogetherProvider is not None
    
    def test_import_mistral(self):
        """Test Mistral can be imported."""
        from rlm_toolkit.providers import MistralProvider
        assert MistralProvider is not None
    
    def test_import_deepseek(self):
        """Test DeepSeek can be imported."""
        from rlm_toolkit.providers import DeepSeekProvider
        assert DeepSeekProvider is not None
    
    def test_import_azure(self):
        """Test Azure can be imported."""
        from rlm_toolkit.providers import AzureOpenAIProvider
        assert AzureOpenAIProvider is not None
    
    def test_import_vllm(self):
        """Test vLLM can be imported."""
        from rlm_toolkit.providers import VLLMProvider
        assert VLLMProvider is not None
    
    def test_import_huggingface_tgi(self):
        """Test HuggingFace TGI can be imported."""
        from rlm_toolkit.providers import HuggingFaceTGIProvider
        assert HuggingFaceTGIProvider is not None
    
    def test_import_openrouter(self):
        """Test OpenRouter can be imported."""
        from rlm_toolkit.providers import OpenRouterProvider
        assert OpenRouterProvider is not None
    
    def test_import_localai(self):
        """Test LocalAI can be imported."""
        from rlm_toolkit.providers import LocalAIProvider
        assert LocalAIProvider is not None
    
    def test_import_lmstudio(self):
        """Test LM Studio can be imported."""
        from rlm_toolkit.providers import LMStudioProvider
        assert LMStudioProvider is not None
    
    def test_import_anyscale(self):
        """Test Anyscale can be imported."""
        from rlm_toolkit.providers import AnyscaleProvider
        assert AnyscaleProvider is not None
    
    def test_import_lepton(self):
        """Test Lepton can be imported."""
        from rlm_toolkit.providers import LeptonProvider
        assert LeptonProvider is not None
    
    def test_import_sambanova(self):
        """Test SambaNova can be imported."""
        from rlm_toolkit.providers import SambaNovaProvider
        assert SambaNovaProvider is not None
    
    def test_import_ai21(self):
        """Test AI21 can be imported."""
        from rlm_toolkit.providers import AI21Provider
        assert AI21Provider is not None
    
    def test_import_cohere(self):
        """Test Cohere can be imported."""
        from rlm_toolkit.providers import CohereProvider
        assert CohereProvider is not None
    
    def test_import_replicate(self):
        """Test Replicate can be imported."""
        from rlm_toolkit.providers import ReplicateProvider
        assert ReplicateProvider is not None


class TestNewProviderConfigs:
    """Test configurations for new providers."""
    
    def test_vllm_defaults(self):
        from rlm_toolkit.providers.compatible import VLLMProvider
        assert VLLMProvider.BASE_URL == "http://localhost:8000/v1"
        assert VLLMProvider.PROVIDER_NAME == "vllm"
    
    def test_huggingface_defaults(self):
        from rlm_toolkit.providers.compatible import HuggingFaceTGIProvider
        assert HuggingFaceTGIProvider.API_KEY_ENV == "HF_TOKEN"
    
    def test_openrouter_models(self):
        from rlm_toolkit.providers.compatible import OpenRouterProvider
        assert "anthropic/claude-3.5-sonnet" in OpenRouterProvider.MODEL_PRICING
        assert "deepseek/deepseek-r1" in OpenRouterProvider.MODEL_PRICING
    
    def test_localai_defaults(self):
        from rlm_toolkit.providers.compatible import LocalAIProvider
        assert LocalAIProvider.BASE_URL == "http://localhost:8080/v1"
    
    def test_lmstudio_defaults(self):
        from rlm_toolkit.providers.compatible import LMStudioProvider
        assert LMStudioProvider.BASE_URL == "http://localhost:1234/v1"
    
    def test_sambanova_models(self):
        from rlm_toolkit.providers.compatible import SambaNovaProvider
        assert "Meta-Llama-3.1-70B-Instruct" in SambaNovaProvider.MODEL_PRICING
    
    def test_ai21_context(self):
        from rlm_toolkit.providers.compatible import AI21Provider
        assert AI21Provider.MODEL_CONTEXT.get("jamba-1.5-large") == 256_000
    
    def test_cohere_initialization(self):
        from rlm_toolkit.providers.compatible import CohereProvider
        provider = CohereProvider("command-r-plus")
        assert provider._model == "command-r-plus"
        assert provider.PRICE_PER_1M_INPUT == 2.5
    
    def test_replicate_initialization(self):
        from rlm_toolkit.providers.compatible import ReplicateProvider
        provider = ReplicateProvider("meta/llama-3.1-70b-instruct")
        assert provider._model == "meta/llama-3.1-70b-instruct"

