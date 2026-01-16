"""Extended tests for providers module."""

import pytest
from rlm_toolkit import providers
from rlm_toolkit.providers.base import LLMProvider, LLMResponse


class TestProvidersInit:
    """Tests for providers __init__ lazy imports."""
    
    def test_import_ollama_provider(self):
        """Test lazy import of OllamaProvider."""
        OllamaProvider = providers.OllamaProvider
        
        assert OllamaProvider is not None
    
    def test_import_openai_provider(self):
        """Test lazy import of OpenAIProvider."""
        OpenAIProvider = providers.OpenAIProvider
        
        assert OpenAIProvider is not None
    
    def test_import_anthropic_provider(self):
        """Test lazy import of AnthropicProvider."""
        AnthropicProvider = providers.AnthropicProvider
        
        assert AnthropicProvider is not None
    
    def test_import_gemini_provider(self):
        """Test lazy import of GeminiProvider."""
        GeminiProvider = providers.GeminiProvider
        
        assert GeminiProvider is not None
    
    def test_import_unknown_raises(self):
        """Test unknown attribute raises AttributeError."""
        with pytest.raises(AttributeError):
            _ = providers.UnknownProvider
    
    def test_direct_imports(self):
        """Test direct imports work."""
        assert providers.LLMProvider is not None
        assert providers.LLMResponse is not None
        assert providers.RetryConfig is not None


class TestLLMResponse:
    """Tests for LLMResponse."""
    
    def test_creation(self):
        """Test response creation."""
        response = LLMResponse(
            content="Hello, world!",
            tokens_in=10,
            tokens_out=5,
            model="test",
        )
        
        assert response.content == "Hello, world!"
        assert response.tokens_in == 10
        assert response.tokens_out == 5
    
    def test_total_tokens(self):
        """Test total tokens calculation."""
        response = LLMResponse(
            content="test",
            tokens_in=100,
            tokens_out=50,
            model="test",
        )
        
        assert response.total_tokens == 150


class TestOllamaProvider:
    """Tests for OllamaProvider."""
    
    def test_creation(self):
        """Test provider creation."""
        from rlm_toolkit.providers.ollama import OllamaProvider
        
        provider = OllamaProvider("llama3")
        
        assert provider.model_name == "llama3"
    
    def test_max_context(self):
        """Test max context."""
        from rlm_toolkit.providers.ollama import OllamaProvider
        
        provider = OllamaProvider("llama3")
        
        assert provider.max_context > 0
    
    def test_custom_base_url(self):
        """Test custom base URL."""
        from rlm_toolkit.providers.ollama import OllamaProvider
        
        # Just verify it accepts base_url parameter
        provider = OllamaProvider("llama3", base_url="http://custom:11434")
        
        assert provider.model_name == "llama3"


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""
    
    def test_creation(self):
        """Test provider creation."""
        from rlm_toolkit.providers.openai import OpenAIProvider
        
        provider = OpenAIProvider("gpt-4o")
        
        assert provider.model_name == "gpt-4o"
    
    def test_max_context(self):
        """Test max context."""
        from rlm_toolkit.providers.openai import OpenAIProvider
        
        provider = OpenAIProvider("gpt-4o")
        
        assert provider.max_context > 0


class TestGeminiProvider:
    """Tests for GeminiProvider."""
    
    def test_creation(self):
        """Test provider creation."""
        from rlm_toolkit.providers.google import GeminiProvider
        
        provider = GeminiProvider("gemini-exp")
        
        assert provider.model_name == "gemini-exp"
    
    def test_max_context(self):
        """Test max context."""
        from rlm_toolkit.providers.google import GeminiProvider
        
        provider = GeminiProvider("gemini-exp")
        
        assert provider.max_context > 0


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""
    
    def test_creation(self):
        """Test provider creation."""
        from rlm_toolkit.providers.anthropic import AnthropicProvider
        
        provider = AnthropicProvider("claude-3-opus")
        
        assert provider.model_name == "claude-3-opus"
