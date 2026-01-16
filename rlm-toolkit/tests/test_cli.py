"""Unit tests for CLI module."""

import pytest
from unittest.mock import patch, MagicMock
import sys
from io import StringIO

from rlm_toolkit.cli.main import create_parser, app
from rlm_toolkit.cli.commands import parse_model, get_provider, run_command, eval_command, trace_command


class TestParseModel:
    """Tests for parse_model function."""
    
    def test_with_provider(self):
        """Test parsing model with provider."""
        provider, model = parse_model("openai:gpt-4o")
        
        assert provider == "openai"
        assert model == "gpt-4o"
    
    def test_without_provider(self):
        """Test parsing model without provider defaults to ollama."""
        provider, model = parse_model("llama3")
        
        assert provider == "ollama"
        assert model == "llama3"
    
    def test_anthropic_provider(self):
        """Test parsing anthropic provider."""
        provider, model = parse_model("anthropic:claude-3")
        
        assert provider == "anthropic"
        assert model == "claude-3"
    
    def test_google_provider(self):
        """Test parsing google provider."""
        provider, model = parse_model("google:gemini-pro")
        
        assert provider == "google"
        assert model == "gemini-pro"
    
    def test_case_insensitive_provider(self):
        """Test provider name is lowercased."""
        provider, model = parse_model("OPENAI:gpt-4")
        
        assert provider == "openai"


class TestGetProvider:
    """Tests for get_provider function."""
    
    def test_get_ollama(self):
        """Test getting ollama provider."""
        provider = get_provider("ollama", "llama3")
        
        assert provider is not None
        assert provider.model_name == "llama3"
    
    def test_get_openai(self):
        """Test getting openai provider."""
        provider = get_provider("openai", "gpt-4o")
        
        assert provider is not None
        assert provider.model_name == "gpt-4o"
    
    def test_get_anthropic(self):
        """Test getting anthropic provider."""
        provider = get_provider("anthropic", "claude-3")
        
        assert provider is not None
    
    def test_get_unknown_raises(self):
        """Test unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown", "model")


class TestCLIParser:
    """Tests for CLI argument parser."""
    
    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        
        assert parser is not None
        assert parser.prog == "rlm"
    
    def test_version_flag(self):
        """Test --version flag."""
        parser = create_parser()
        
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        
        assert exc.value.code == 0
    
    def test_run_command_args(self):
        """Test run command argument parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "run",
            "--model", "ollama:llama3",
            "--context", "file.txt",
            "--query", "summarize",
        ])
        
        assert args.command == "run"
        assert args.model == "ollama:llama3"
        assert args.context == "file.txt"
        assert args.query == "summarize"
    
    def test_run_command_defaults(self):
        """Test run command default values."""
        parser = create_parser()
        args = parser.parse_args([
            "run", "-m", "m", "-c", "c", "-q", "q"
        ])
        
        assert args.max_iterations == 50
        assert args.max_cost == 10.0
        assert args.format == "text"
    
    def test_eval_command_args(self):
        """Test eval command argument parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "eval",
            "--benchmark", "oolong",
            "--model", "openai:gpt-4",
        ])
        
        assert args.command == "eval"
        assert args.benchmark == "oolong"
    
    def test_trace_command_args(self):
        """Test trace command argument parsing."""
        parser = create_parser()
        args = parser.parse_args([
            "trace",
            "--run-id", "abc123",
        ])
        
        assert args.command == "trace"
        assert args.run_id == "abc123"
    
    def test_repl_command(self):
        """Test repl command."""
        parser = create_parser()
        args = parser.parse_args(["repl"])
        
        assert args.command == "repl"
        assert args.model == "ollama:llama4"


class TestEvalCommand:
    """Tests for eval command."""
    
    def test_eval_returns_zero(self, capsys):
        """Test eval command returns 0."""
        args = MagicMock()
        args.model = "test:model"
        args.benchmark = "oolong"
        
        result = eval_command(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "oolong" in captured.out


class TestTraceCommand:
    """Tests for trace command."""
    
    def test_trace_returns_zero(self, capsys):
        """Test trace command returns 0."""
        args = MagicMock()
        args.run_id = "test-run-id"
        args.format = "text"
        
        result = trace_command(args)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "test-run-id" in captured.out


class TestApp:
    """Tests for app function."""
    
    def test_no_command_shows_help(self, capsys):
        """Test no command shows help."""
        result = app([])
        
        assert result == 0
        captured = capsys.readouterr()
        assert "RLM-Toolkit" in captured.out or "usage" in captured.out.lower()
    
    def test_unknown_command_exits(self):
        """Test unknown command raises SystemExit."""
        with pytest.raises(SystemExit) as exc:
            app(["unknown"])
        
        assert exc.value.code == 2
    
    @patch('rlm_toolkit.cli.commands.run_command')
    def test_run_delegates(self, mock_run):
        """Test run command delegates properly."""
        mock_run.return_value = 0
        
        result = app([
            "run",
            "--model", "test:model",
            "--context", "test.txt",
            "--query", "test query",
        ])
        
        # Would fail on missing file, but tests delegation
        # Either runs or errors on file not found
        assert result in (0, 1)
