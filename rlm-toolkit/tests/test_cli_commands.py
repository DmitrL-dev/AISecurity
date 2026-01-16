"""Extended tests for CLI commands module."""

import pytest
from unittest.mock import MagicMock, patch
import argparse

from rlm_toolkit.cli.commands import (
    parse_model,
    get_provider,
    run_command,
    eval_command,
    trace_command,
    repl_command,
)


class TestParseModel:
    """Tests for parse_model function."""
    
    def test_with_provider(self):
        """Test parsing with explicit provider."""
        provider, model = parse_model("openai:gpt-4o")
        
        assert provider == "openai"
        assert model == "gpt-4o"
    
    def test_without_provider(self):
        """Test parsing without provider defaults to ollama."""
        provider, model = parse_model("llama3")
        
        assert provider == "ollama"
        assert model == "llama3"
    
    def test_anthropic_provider(self):
        """Test parsing Anthropic provider."""
        provider, model = parse_model("anthropic:claude-3-opus")
        
        assert provider == "anthropic"
    
    def test_google_provider(self):
        """Test parsing Google provider."""
        provider, model = parse_model("google:gemini-exp")
        
        assert provider == "google"
    
    def test_case_insensitive(self):
        """Test provider name is lowercased."""
        provider, model = parse_model("OpenAI:gpt-4o")
        
        assert provider == "openai"


class TestGetProvider:
    """Tests for get_provider function."""
    
    def test_ollama_provider(self):
        """Test creating Ollama provider."""
        provider = get_provider("ollama", "llama3")
        
        assert provider.model_name == "llama3"
    
    def test_openai_provider(self):
        """Test creating OpenAI provider."""
        provider = get_provider("openai", "gpt-4o")
        
        assert provider.model_name == "gpt-4o"
    
    def test_anthropic_provider(self):
        """Test creating Anthropic provider."""
        provider = get_provider("anthropic", "claude-3")
        
        assert provider.model_name == "claude-3"
    
    def test_unknown_provider(self):
        """Test unknown provider raises error."""
        with pytest.raises(ValueError):
            get_provider("unknown", "model")


class TestEvalCommand:
    """Tests for eval_command."""
    
    def test_eval_returns_zero(self):
        """Test eval command returns 0."""
        args = argparse.Namespace(
            model="ollama:llama3",
            benchmark="oolong",
        )
        
        result = eval_command(args)
        
        assert result == 0


class TestTraceCommand:
    """Tests for trace_command."""
    
    def test_trace_returns_zero(self):
        """Test trace command returns 0."""
        args = argparse.Namespace(
            run_id="test-run-123",
            format="text",
        )
        
        result = trace_command(args)
        
        assert result == 0


class TestReplCommand:
    """Tests for repl_command."""
    
    @patch("builtins.input", side_effect=["exit"])
    def test_repl_exit(self, mock_input):
        """Test REPL exits on 'exit' command."""
        args = argparse.Namespace(
            model="ollama:llama3",
        )
        
        result = repl_command(args)
        
        assert result == 0
    
    @patch("builtins.input", side_effect=EOFError)
    def test_repl_eof(self, mock_input):
        """Test REPL handles EOF."""
        args = argparse.Namespace(
            model="ollama:llama3",
        )
        
        result = repl_command(args)
        
        assert result == 0
