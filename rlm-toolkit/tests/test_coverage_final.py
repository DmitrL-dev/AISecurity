"""Additional tests for remaining coverage gaps."""

import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os

from rlm_toolkit.providers.anthropic import AnthropicProvider
from rlm_toolkit.observability.tracer import Tracer
from rlm_toolkit.observability.exporters import ConsoleExporter
from rlm_toolkit.memory.episodic import EpisodicMemory, _simple_similarity, _cosine_similarity
from rlm_toolkit.memory.base import Memory, MemoryEntry


# =============================================================================
# Anthropic Provider
# =============================================================================

class TestAnthropicProviderExtended:
    """Extended Anthropic tests."""
    
    def test_pricing_defined(self):
        """Test pricing is defined."""
        provider = AnthropicProvider("claude-3")
        
        assert hasattr(provider, 'PRICE_PER_1M_INPUT')
        assert hasattr(provider, 'PRICE_PER_1M_OUTPUT')
    
    def test_context_window(self):
        """Test context window defined."""
        provider = AnthropicProvider("claude-3")
        
        assert provider.max_context > 0
    
    @patch("rlm_toolkit.providers.anthropic.AnthropicProvider._get_client")
    def test_generate_basic(self, mock_get_client):
        """Test basic generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Hello!"
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        provider = AnthropicProvider("claude-3")
        response = provider.generate("Hi")
        
        assert response.content == "Hello!"


# =============================================================================
# Episodic Memory Extended
# =============================================================================

class TestEpisodicMemoryExtended:
    """Extended episodic memory tests."""
    
    def test_simple_similarity_identical(self):
        """Test similarity of identical strings."""
        score = _simple_similarity("hello world", "hello world")
        
        assert score == 1.0
    
    def test_simple_similarity_different(self):
        """Test similarity of different strings."""
        score = _simple_similarity("hello", "goodbye")
        
        assert score < 1.0
    
    def test_simple_similarity_partial(self):
        """Test partial overlap."""
        score = _simple_similarity("hello world", "hello there")
        
        assert 0 < score < 1
    
    def test_simple_similarity_empty(self):
        """Test empty strings."""
        score = _simple_similarity("", "hello")
        
        assert score == 0.0
    
    def test_cosine_similarity_identical(self):
        """Test cosine similarity of identical vectors."""
        score = _cosine_similarity([1.0, 0.0], [1.0, 0.0])
        
        assert abs(score - 1.0) < 0.001
    
    def test_cosine_similarity_orthogonal(self):
        """Test orthogonal vectors."""
        score = _cosine_similarity([1.0, 0.0], [0.0, 1.0])
        
        assert abs(score) < 0.001
    
    def test_cosine_similarity_different_lengths(self):
        """Test different length vectors."""
        score = _cosine_similarity([1.0], [1.0, 2.0])
        
        assert score == 0.0
    
    def test_cosine_similarity_zero_vector(self):
        """Test zero vector."""
        score = _cosine_similarity([0.0, 0.0], [1.0, 0.0])
        
        assert score == 0.0
    
    def test_with_embedding_function(self):
        """Test with embedding function."""
        def embed(text):
            return [len(text), len(text.split())]
        
        memory = EpisodicMemory(embed_fn=embed)
        
        memory.add("hello world")
        
        assert memory.size == 1
    
    def test_get_by_timerange(self):
        """Test get by time range."""
        from datetime import datetime, timedelta
        
        memory = EpisodicMemory()
        memory.add("entry 1")
        memory.add("entry 2")
        
        start = datetime.now() - timedelta(hours=1)
        results = memory.get_by_timerange(start)
        
        assert len(results) == 2
    
    def test_contiguity_retrieval(self):
        """Test contiguity settings."""
        memory = EpisodicMemory(k_similarity=2, k_contiguity=1)
        
        for i in range(10):
            memory.add(f"entry {i}")
        
        results = memory.retrieve("entry 5", k=2)
        
        assert len(results) >= 2


# =============================================================================
# Memory Entry
# =============================================================================

class TestMemoryEntry:
    """Tests for MemoryEntry."""
    
    def test_creation(self):
        """Test entry creation."""
        entry = MemoryEntry(content="test", metadata={})
        
        assert entry.content == "test"
    
    def test_with_metadata(self):
        """Test with metadata."""
        entry = MemoryEntry(
            content="test",
            metadata={"key": "value"},
        )
        
        assert entry.metadata["key"] == "value"
    
    def test_with_embedding(self):
        """Test with embedding."""
        entry = MemoryEntry(
            content="test",
            metadata={},
            embedding=[0.1, 0.2, 0.3],
        )
        
        assert len(entry.embedding) == 3


# =============================================================================
# Tracer Extended
# =============================================================================

class TestTracerExtended:
    """Extended tracer tests."""
    
    def test_tracer_creation(self):
        """Test tracer creation."""
        tracer = Tracer()
        
        assert tracer is not None


# =============================================================================
# Console Exporter Extended
# =============================================================================

class TestConsoleExporterExtended:
    """Extended console exporter tests."""
    
    def test_creation(self):
        """Test creation."""
        exporter = ConsoleExporter()
        
        assert exporter is not None


# =============================================================================
# CLI Commands Run Extended
# =============================================================================

class TestCLICommandsExtended:
    """Extended CLI command tests."""
    
    def test_parse_model_complex(self):
        """Test parse_model with colons in model name."""
        from rlm_toolkit.cli.commands import parse_model
        
        provider, model = parse_model("provider:model:version")
        
        assert provider == "provider"
        assert "model" in model
