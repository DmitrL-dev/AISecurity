"""Bulk tests for remaining low-coverage modules."""

import pytest
from unittest.mock import MagicMock, patch, Mock
import argparse
import sys

from rlm_toolkit.providers.google import GeminiProvider
from rlm_toolkit.providers.openai import OpenAIProvider
from rlm_toolkit.providers.anthropic import AnthropicProvider
from rlm_toolkit.cli.main import create_parser, app


# =============================================================================
# OpenAI Provider Extended Tests
# =============================================================================

class TestOpenAIProviderBulk:
    """Bulk tests for OpenAI provider."""
    
    def test_model_pricing_gpt5(self):
        """Test GPT-5 pricing."""
        provider = OpenAIProvider("gpt-5")
        
        assert provider.PRICE_PER_1M_INPUT == 8.0
        assert provider.PRICE_PER_1M_OUTPUT == 24.0
    
    def test_model_pricing_gpt4o_mini(self):
        """Test GPT-4o-mini pricing."""
        provider = OpenAIProvider("gpt-4o-mini")
        
        assert provider.PRICE_PER_1M_INPUT == 0.15
    
    def test_model_pricing_o3_mini(self):
        """Test o3-mini pricing."""
        provider = OpenAIProvider("o3-mini")
        
        assert provider.PRICE_PER_1M_INPUT == 1.10
    
    def test_unknown_model_default_pricing(self):
        """Test unknown model gets default pricing."""
        provider = OpenAIProvider("unknown-model")
        
        assert provider.PRICE_PER_1M_INPUT == 5.0  # Default
    
    def test_context_window_gpt5_2(self):
        """Test GPT-5.2 context window."""
        provider = OpenAIProvider("gpt-5.2")
        
        assert provider.max_context == 4_000_000
    
    def test_context_window_gpt4o(self):
        """Test GPT-4o context window."""
        provider = OpenAIProvider("gpt-4o")
        
        assert provider.max_context == 128_000
    
    def test_unknown_model_default_context(self):
        """Test unknown model gets default context."""
        provider = OpenAIProvider("unknown")
        
        assert provider.max_context == 128_000
    
    def test_api_key_storage(self):
        """Test API key is stored."""
        provider = OpenAIProvider("gpt-4o", api_key="test-key")
        
        assert provider._api_key == "test-key"
    
    @patch("rlm_toolkit.providers.openai.OpenAIProvider._get_client")
    def test_generate_basic(self, mock_get_client):
        """Test basic generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello!"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        provider = OpenAIProvider("gpt-4o")
        response = provider.generate("Hi")
        
        assert response.content == "Hello!"
        assert response.tokens_in == 10


# =============================================================================
# Gemini Provider Extended Tests
# =============================================================================

class TestGeminiProviderBulk:
    """Bulk tests for Gemini provider."""
    
    def test_model_pricing_gemini_3_pro(self):
        """Test Gemini 3 Pro pricing."""
        provider = GeminiProvider("gemini-3-pro")
        
        assert provider.PRICE_PER_1M_INPUT == 1.25
        assert provider.PRICE_PER_1M_OUTPUT == 5.0
    
    def test_model_pricing_gemini_2_ultra(self):
        """Test Gemini 2 Ultra pricing."""
        provider = GeminiProvider("gemini-2-ultra")
        
        assert provider.PRICE_PER_1M_INPUT == 10.0
    
    def test_model_pricing_flash(self):
        """Test Flash model pricing."""
        provider = GeminiProvider("gemini-2.0-flash")
        
        assert provider.PRICE_PER_1M_INPUT == 0.075
    
    def test_unknown_model_default_pricing(self):
        """Test unknown model gets default."""
        provider = GeminiProvider("unknown")
        
        assert provider.PRICE_PER_1M_INPUT == 1.25
    
    def test_context_window_10m(self):
        """Test 10M context window."""
        provider = GeminiProvider("gemini-3-pro")
        
        assert provider.max_context == 10_000_000
    
    def test_context_window_2m(self):
        """Test 2M context window."""
        provider = GeminiProvider("gemini-2-ultra")
        
        assert provider.max_context == 2_000_000
    
    def test_unknown_model_default_context(self):
        """Test unknown model default context."""
        provider = GeminiProvider("unknown")
        
        assert provider.max_context == 1_000_000
    
    def test_api_key_storage(self):
        """Test API key storage."""
        provider = GeminiProvider("gemini-3-pro", api_key="test-key")
        
        assert provider._api_key == "test-key"
    
    @patch("rlm_toolkit.providers.google.GeminiProvider._get_client")
    def test_generate_with_system_prompt(self, mock_get_client):
        """Test generation with system prompt."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response"
        mock_client.generate_content.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        provider = GeminiProvider("gemini-3-pro")
        response = provider.generate("Hi", system_prompt="Be helpful")
        
        assert response.content == "Response"


# =============================================================================
# Anthropic Provider Extended Tests  
# =============================================================================

class TestAnthropicProviderBulk:
    """Bulk tests for Anthropic provider."""
    
    def test_default_model(self):
        """Test default model."""
        provider = AnthropicProvider()
        
        assert "claude" in provider.model_name.lower()
    
    def test_custom_model(self):
        """Test custom model."""
        provider = AnthropicProvider("claude-4-opus")
        
        assert provider.model_name == "claude-4-opus"
    
    def test_api_key_storage(self):
        """Test API key storage."""
        provider = AnthropicProvider("claude-3", api_key="test")
        
        assert provider._api_key == "test"


# =============================================================================
# CLI Main Tests
# =============================================================================

class TestCLIParserBulk:
    """Bulk tests for CLI parser."""
    
    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()
        
        assert parser is not None
        assert parser.prog == "rlm"
    
    def test_version_flag(self):
        """Test version flag exists."""
        parser = create_parser()
        
        # Should not raise
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0
    
    def test_run_subcommand(self):
        """Test run subcommand parsing."""
        parser = create_parser()
        
        args = parser.parse_args([
            "run",
            "--model", "ollama:llama3",
            "--context", "test.txt",
            "--query", "summarize",
        ])
        
        assert args.command == "run"
        assert args.model == "ollama:llama3"
    
    def test_eval_subcommand(self):
        """Test eval subcommand parsing."""
        parser = create_parser()
        
        args = parser.parse_args([
            "eval",
            "--benchmark", "oolong",
            "--model", "openai:gpt-4o",
        ])
        
        assert args.command == "eval"
        assert args.benchmark == "oolong"
    
    def test_trace_subcommand(self):
        """Test trace subcommand parsing."""
        parser = create_parser()
        
        args = parser.parse_args([
            "trace",
            "--run-id", "abc123",
        ])
        
        assert args.command == "trace"
        assert args.run_id == "abc123"
    
    def test_repl_subcommand(self):
        """Test repl subcommand parsing."""
        parser = create_parser()
        
        args = parser.parse_args(["repl"])
        
        assert args.command == "repl"
    
    def test_max_iterations_default(self):
        """Test max iterations default."""
        parser = create_parser()
        
        args = parser.parse_args([
            "run", "-m", "test", "-c", "f.txt", "-q", "q",
        ])
        
        assert args.max_iterations == 50
    
    def test_max_cost_default(self):
        """Test max cost default."""
        parser = create_parser()
        
        args = parser.parse_args([
            "run", "-m", "test", "-c", "f.txt", "-q", "q",
        ])
        
        assert args.max_cost == 10.0
    
    def test_format_choices(self):
        """Test format choices."""
        parser = create_parser()
        
        args = parser.parse_args([
            "run", "-m", "test", "-c", "f.txt", "-q", "q",
            "--format", "json",
        ])
        
        assert args.format == "json"


class TestCLIAppBulk:
    """Bulk tests for CLI app function."""
    
    def test_no_command_shows_help(self, capsys):
        """Test no command shows help."""
        result = app([])
        
        assert result == 0
    
    def test_eval_command(self):
        """Test eval command."""
        result = app([
            "eval",
            "--benchmark", "oolong",
            "--model", "test:model",
        ])
        
        assert result == 0
    
    def test_trace_command(self):
        """Test trace command."""
        result = app([
            "trace",
            "--run-id", "test-123",
        ])
        
        assert result == 0
    
    @patch("builtins.input", side_effect=["exit"])
    def test_repl_command(self, mock_input):
        """Test repl command."""
        result = app(["repl"])
        
        assert result == 0


# =============================================================================
# Platform Guards Extended Tests
# =============================================================================

class TestPlatformGuardsBulk:
    """Bulk tests for platform guards."""
    
    def test_guard_config_custom(self):
        """Test custom guard config."""
        from rlm_toolkit.security.platform_guards import GuardConfig
        
        config = GuardConfig(
            timeout_seconds=120.0,
            memory_mb=2048,
            cpu_percent=90,
        )
        
        assert config.timeout_seconds == 120.0
        assert config.memory_mb == 2048
        assert config.cpu_percent == 90
    
    def test_create_guards_returns_guards(self):
        """Test create_guards returns object."""
        from rlm_toolkit.security.platform_guards import create_guards
        
        guards = create_guards()
        
        assert guards is not None
        assert hasattr(guards, "platform_name")
        assert hasattr(guards, "capabilities")
    
    def test_guards_execute_simple_function(self):
        """Test guards can execute simple function."""
        from rlm_toolkit.security.platform_guards import create_guards
        
        guards = create_guards()
        
        def add(a, b):
            return a + b
        
        success, result = guards.execute_with_timeout(add, timeout=1.0, a=1, b=2)
        
        assert success is True
        assert result == 3
    
    def test_guards_execute_with_args(self):
        """Test guards with positional args."""
        from rlm_toolkit.security.platform_guards import create_guards
        
        guards = create_guards()
        
        def multiply(x, y):
            return x * y
        
        success, result = guards.execute_with_timeout(multiply, 1.0, 3, 4)
        
        assert success is True
        assert result == 12
