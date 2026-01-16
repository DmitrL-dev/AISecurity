"""Extended provider tests for coverage."""

import pytest
from unittest.mock import MagicMock, patch

from rlm_toolkit.providers.base import LLMProvider, LLMResponse
from rlm_toolkit.providers.ollama import OllamaProvider
from rlm_toolkit.providers.openai import OpenAIProvider
from rlm_toolkit.providers.anthropic import AnthropicProvider
from rlm_toolkit.providers.google import GeminiProvider


class TestOllamaProviderExtended:
    """Extended tests for OllamaProvider."""
    
    def test_default_base_url(self):
        """Test default base URL."""
        provider = OllamaProvider("llama3")
        
        assert "localhost:11434" in provider._base_url
    
    def test_custom_context_window(self):
        """Test custom context window."""
        provider = OllamaProvider("llama3", context_window=50000)
        
        assert provider.max_context == 50000
    
    def test_default_context_window(self):
        """Test default context window."""
        provider = OllamaProvider("llama3")
        
        assert provider.max_context == OllamaProvider.DEFAULT_CONTEXT
    
    def test_free_pricing(self):
        """Test Ollama is free (local)."""
        assert OllamaProvider.PRICE_PER_1M_INPUT == 0.0
        assert OllamaProvider.PRICE_PER_1M_OUTPUT == 0.0
    
    @patch("rlm_toolkit.providers.ollama.OllamaProvider._get_client")
    def test_generate_with_system_prompt(self, mock_get_client):
        """Test generate with system prompt."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {
            "message": {"content": "Hello!"},
            "eval_count": 10,
            "prompt_eval_count": 5,
        }
        mock_get_client.return_value = mock_client
        
        provider = OllamaProvider("llama3")
        response = provider.generate("Hi", system_prompt="You are helpful")
        
        assert response.content == "Hello!"
        call_args = mock_client.chat.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert len(messages) == 2  # system + user
    
    @patch("rlm_toolkit.providers.ollama.OllamaProvider._get_client")
    def test_generate_with_max_tokens(self, mock_get_client):
        """Test generate with max_tokens."""
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "response"}}
        mock_get_client.return_value = mock_client
        
        provider = OllamaProvider("llama3")
        provider.generate("Hi", max_tokens=100)
        
        call_args = mock_client.chat.call_args
        options = call_args.kwargs.get("options") or call_args[1].get("options")
        assert options["num_predict"] == 100


class TestOpenAIProviderExtended:
    """Extended tests for OpenAIProvider."""
    
    def test_context_windows(self):
        """Test context windows for different models."""
        provider_4o = OpenAIProvider("gpt-4o")
        provider_mini = OpenAIProvider("gpt-4o-mini")
        
        assert provider_4o.max_context > 0
        assert provider_mini.max_context > 0
    
    def test_pricing(self):
        """Test pricing is defined."""
        assert hasattr(OpenAIProvider, 'PRICE_PER_1M_INPUT')
        assert hasattr(OpenAIProvider, 'PRICE_PER_1M_OUTPUT')


class TestAnthropicProviderExtended:
    """Extended tests for AnthropicProvider."""
    
    def test_context_window(self):
        """Test context window."""
        provider = AnthropicProvider("claude-3-opus")
        
        assert provider.max_context > 0
    
    def test_pricing(self):
        """Test pricing is defined."""
        assert hasattr(AnthropicProvider, 'PRICE_PER_1M_INPUT')
        assert hasattr(AnthropicProvider, 'PRICE_PER_1M_OUTPUT')


class TestGeminiProviderExtended:
    """Extended tests for GeminiProvider."""
    
    def test_context_window(self):
        """Test context window."""
        provider = GeminiProvider("gemini-exp")
        
        assert provider.max_context > 0
    
    def test_model_name(self):
        """Test model name."""
        provider = GeminiProvider("gemini-2.0-flash")
        
        assert provider.model_name == "gemini-2.0-flash"


class TestLLMResponse:
    """Extended tests for LLMResponse."""
    
    def test_total_tokens(self):
        """Test total tokens calculation."""
        response = LLMResponse(
            content="test",
            tokens_in=100,
            tokens_out=50,
            model="test",
        )
        
        assert response.total_tokens == 150
    
    def test_raw_response(self):
        """Test raw response storage."""
        raw = {"custom": "data"}
        response = LLMResponse(
            content="test",
            tokens_in=10,
            tokens_out=5,
            model="test",
            raw=raw,
        )
        
        assert response.raw == raw
    
    def test_default_raw(self):
        """Test default raw is None."""
        response = LLMResponse(
            content="test",
            tokens_in=10,
            tokens_out=5,
            model="test",
        )
        
        assert response.raw is None
