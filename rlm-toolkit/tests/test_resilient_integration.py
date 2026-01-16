"""Tests for ResilientProvider integration in RLM engine."""

import pytest
from unittest.mock import MagicMock, patch

from rlm_toolkit.core.engine import RLM, RLMConfig
from rlm_toolkit.providers.base import ResilientProvider
from rlm_toolkit.testing.mocks import MockProvider


class TestFactoryMethodsResilient:
    """Tests for factory methods with resilient parameter."""
    
    @patch("rlm_toolkit.providers.ollama.OllamaProvider")
    def test_from_ollama_resilient_default(self, mock_ollama):
        """Test from_ollama wraps with ResilientProvider by default."""
        mock_provider = MagicMock()
        mock_ollama.return_value = mock_provider
        
        rlm = RLM.from_ollama("llama4")
        
        # Root should be wrapped in ResilientProvider
        assert isinstance(rlm.root, ResilientProvider)
    
    @patch("rlm_toolkit.providers.ollama.OllamaProvider")
    def test_from_ollama_resilient_false(self, mock_ollama):
        """Test from_ollama without resilient wrapper."""
        mock_provider = MagicMock()
        mock_ollama.return_value = mock_provider
        
        rlm = RLM.from_ollama("llama4", resilient=False)
        
        # Root should NOT be wrapped
        assert not isinstance(rlm.root, ResilientProvider)
    
    @patch("rlm_toolkit.providers.openai.OpenAIProvider")
    def test_from_openai_resilient_default(self, mock_openai):
        """Test from_openai wraps with ResilientProvider by default."""
        mock_provider = MagicMock()
        mock_openai.return_value = mock_provider
        
        rlm = RLM.from_openai("gpt-5.2")
        
        assert isinstance(rlm.root, ResilientProvider)
        assert isinstance(rlm.sub, ResilientProvider)
    
    @patch("rlm_toolkit.providers.openai.OpenAIProvider")
    def test_from_openai_resilient_false(self, mock_openai):
        """Test from_openai without resilient wrapper."""
        mock_provider = MagicMock()
        mock_openai.return_value = mock_provider
        
        rlm = RLM.from_openai("gpt-5.2", resilient=False)
        
        assert not isinstance(rlm.root, ResilientProvider)
    
    @patch("rlm_toolkit.providers.anthropic.AnthropicProvider")
    def test_from_anthropic_resilient_default(self, mock_anthropic):
        """Test from_anthropic wraps with ResilientProvider by default."""
        mock_provider = MagicMock()
        mock_anthropic.return_value = mock_provider
        
        rlm = RLM.from_anthropic("claude-opus-4.5")
        
        assert isinstance(rlm.root, ResilientProvider)
        assert isinstance(rlm.sub, ResilientProvider)


class TestResilientProviderIntegration:
    """Integration tests for ResilientProvider in RLM engine."""
    
    def test_rlm_run_with_resilient_provider(self):
        """Test RLM.run() with ResilientProvider wrapper."""
        mock = MockProvider(responses=["FINAL(done)"])
        resilient = ResilientProvider(mock)
        
        rlm = RLM(root=resilient)
        result = rlm.run(context="test context", query="test")
        
        assert result.status == "success"
        assert result.answer == "done"
    
    def test_resilient_provider_detects_openai_name(self):
        """Test auto-detection of provider name."""
        from rlm_toolkit.providers.openai import OpenAIProvider
        
        # Create with mock _get_client to avoid actual API
        inner = MagicMock(spec=OpenAIProvider)
        inner.__class__.__name__ = "OpenAIProvider"
        
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "openai"
    
    def test_resilient_provider_detects_anthropic_name(self):
        """Test auto-detection of Anthropic provider name."""
        inner = MagicMock()
        inner.__class__.__name__ = "AnthropicProvider"
        
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "anthropic"
    
    def test_resilient_provider_detects_ollama_name(self):
        """Test auto-detection of Ollama provider name."""
        inner = MagicMock()
        inner.__class__.__name__ = "OllamaProvider"
        
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "ollama"
    
    def test_resilient_provider_detects_gemini_name(self):
        """Test auto-detection of Gemini provider name."""
        inner = MagicMock()
        inner.__class__.__name__ = "GeminiProvider"
        
        resilient = ResilientProvider(inner)
        
        assert resilient._provider_name == "google"
