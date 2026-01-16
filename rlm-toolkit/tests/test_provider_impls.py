"""Unit tests for provider implementations."""

import pytest
from rlm_toolkit.providers.base import LLMProvider, LLMResponse, ResilientProvider
from rlm_toolkit.providers.openai import OpenAIProvider
from rlm_toolkit.providers.anthropic import AnthropicProvider
from rlm_toolkit.providers.google import GeminiProvider
from rlm_toolkit.providers.ollama import OllamaProvider
from rlm_toolkit.testing.mocks import MockProvider


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""
    
    def test_provider_creation(self):
        """Test provider creation without API key (should not fail on init)."""
        # Creation should work, API call would fail
        provider = OpenAIProvider(model="gpt-4o")
        
        assert provider.model_name == "gpt-4o"
        assert provider.max_context > 0
    
    def test_pricing(self):
        """Test pricing is set."""
        provider = OpenAIProvider(model="gpt-4o")
        
        assert provider.PRICE_PER_1M_INPUT >= 0
        assert provider.PRICE_PER_1M_OUTPUT >= 0
    
    def test_cost_calculation(self):
        """Test cost calculation."""
        provider = OpenAIProvider(model="gpt-4o")
        
        response = LLMResponse(
            content="test",
            model="gpt-4o",
            tokens_in=1000,
            tokens_out=500,
        )
        
        cost = provider.get_cost(response)
        assert cost >= 0


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""
    
    def test_provider_creation(self):
        """Test provider creation."""
        provider = AnthropicProvider(model="claude-3-opus")
        
        assert "claude" in provider.model_name.lower()
        assert provider.max_context > 0
    
    def test_pricing(self):
        """Test pricing is set."""
        provider = AnthropicProvider()
        
        assert provider.PRICE_PER_1M_INPUT >= 0
        assert provider.PRICE_PER_1M_OUTPUT >= 0


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def test_provider_creation(self):
        """Test provider creation."""
        provider = GeminiProvider(model="gemini-pro")
        
        assert "gemini" in provider.model_name.lower()
        assert provider.max_context > 0
    
    def test_pricing(self):
        """Test pricing is set."""
        provider = GeminiProvider()
        
        assert provider.PRICE_PER_1M_INPUT >= 0


class TestOllamaProvider:
    """Tests for OllamaProvider."""
    
    def test_provider_creation(self):
        """Test provider creation."""
        provider = OllamaProvider(model="llama3")
        
        assert provider.model_name == "llama3"
        assert provider.max_context > 0
    
    def test_local_pricing(self):
        """Test local provider has zero pricing."""
        provider = OllamaProvider()
        
        # Local models should be free
        assert provider.PRICE_PER_1M_INPUT == 0
        assert provider.PRICE_PER_1M_OUTPUT == 0


class TestResilientProviderDetailed:
    """Additional tests for ResilientProvider."""
    
    def test_wraps_openai(self):
        """Test wrapping OpenAI provider."""
        inner = OpenAIProvider(model="gpt-4o")
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "openai"
        assert resilient.model_name == "gpt-4o"
    
    def test_wraps_anthropic(self):
        """Test wrapping Anthropic provider."""
        inner = AnthropicProvider()
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "anthropic"
    
    def test_wraps_google(self):
        """Test wrapping Google provider."""
        inner = GeminiProvider()
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "google"
    
    def test_wraps_ollama(self):
        """Test wrapping Ollama provider."""
        inner = OllamaProvider()
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "ollama"
    
    def test_custom_provider_name(self):
        """Test custom provider name override."""
        inner = MockProvider()
        resilient = ResilientProvider(inner, provider_name="custom")
        
        assert resilient._provider_name == "custom"


class TestLLMResponse:
    """Tests for LLMResponse."""
    
    def test_response_creation(self):
        """Test response creation."""
        response = LLMResponse(
            content="Hello",
            model="test",
            tokens_in=10,
            tokens_out=5,
        )
        
        assert response.content == "Hello"
        assert response.total_tokens == 15
    
    def test_empty_tokens(self):
        """Test response with no tokens."""
        response = LLMResponse(
            content="test",
            model="test",
        )
        
        assert response.total_tokens == 0
