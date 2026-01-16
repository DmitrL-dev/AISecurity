"""Unit tests for configuration module."""

import pytest
import os
from rlm_toolkit.core.config import (
    SecurityConfig,
    ProviderConfig,
    ObservabilityConfig,
    MemoryConfig,
    RLMConfig,
)


class TestSecurityConfig:
    """Tests for SecurityConfig."""
    
    def test_defaults(self):
        """Test default values."""
        config = SecurityConfig()
        
        assert config.sandbox is True
        assert config.max_execution_time == 30.0
        assert config.max_memory_mb == 512
        assert config.virtual_fs is True
    
    def test_custom_values(self):
        """Test custom values."""
        config = SecurityConfig(
            sandbox=False,
            max_execution_time=60.0,
            blocked_imports=["requests"],
        )
        
        assert config.sandbox is False
        assert config.max_execution_time == 60.0
        assert "requests" in config.blocked_imports


class TestProviderConfig:
    """Tests for ProviderConfig."""
    
    def test_required_fields(self):
        """Test required fields."""
        config = ProviderConfig(provider="openai", model="gpt-4o")
        
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
    
    def test_defaults(self):
        """Test default values."""
        config = ProviderConfig(provider="ollama", model="llama3")
        
        assert config.timeout == 120.0
        assert config.max_retries == 3
    
    def test_get_api_key_from_config(self):
        """Test API key from config."""
        config = ProviderConfig(
            provider="openai",
            model="gpt-4o",
            api_key="sk-test123",
        )
        
        assert config.get_api_key() == "sk-test123"
    
    def test_get_api_key_from_env_var(self, monkeypatch):
        """Test API key from environment variable."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
        
        config = ProviderConfig(provider="openai", model="gpt-4o")
        
        assert config.get_api_key() == "sk-from-env"
    
    def test_get_api_key_env_reference(self, monkeypatch):
        """Test API key with $ env var reference."""
        monkeypatch.setenv("MY_KEY", "sk-mykey")
        
        config = ProviderConfig(
            provider="openai",
            model="gpt-4o",
            api_key="$MY_KEY",
        )
        
        assert config.get_api_key() == "sk-mykey"
    
    def test_get_api_key_anthropic(self, monkeypatch):
        """Test API key for Anthropic."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")
        
        config = ProviderConfig(provider="anthropic", model="claude-3")
        
        assert config.get_api_key() == "sk-anthropic"


class TestObservabilityConfig:
    """Tests for ObservabilityConfig."""
    
    def test_defaults(self):
        """Test default values."""
        config = ObservabilityConfig()
        
        assert config.enabled is True
        assert config.console_logging is False
        assert config.langfuse is False
        assert config.langsmith is False


class TestMemoryConfig:
    """Tests for MemoryConfig."""
    
    def test_defaults(self):
        """Test default values."""
        config = MemoryConfig()
        
        assert config.enabled is False
        assert config.type == "buffer"
    
    def test_episodic(self):
        """Test episodic config."""
        config = MemoryConfig(type="episodic", k_similarity=10)
        
        assert config.type == "episodic"
        assert config.k_similarity == 10


class TestRLMConfigValidation:
    """Tests for RLMConfig validation."""
    
    def test_valid_config(self):
        """Test valid config passes validation."""
        config = RLMConfig()
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_invalid_max_iterations(self):
        """Test invalid max_iterations fails."""
        config = RLMConfig(max_iterations=0)
        errors = config.validate()
        
        assert len(errors) > 0
        assert any("max_iterations" in e for e in errors)
    
    def test_invalid_max_cost(self):
        """Test negative max_cost fails."""
        config = RLMConfig(max_cost=-1.0)
        errors = config.validate()
        
        assert any("max_cost" in e for e in errors)
    
    def test_invalid_timeout(self):
        """Test invalid timeout fails."""
        config = RLMConfig(timeout=0.5)
        errors = config.validate()
        
        assert any("timeout" in e for e in errors)


class TestRLMConfigFromDict:
    """Tests for RLMConfig.from_dict."""
    
    def test_basic_fields(self):
        """Test basic field parsing."""
        config = RLMConfig.from_dict({
            "max_iterations": 100,
            "max_cost": 50.0,
        })
        
        assert config.max_iterations == 100
        assert config.max_cost == 50.0
    
    def test_with_provider(self):
        """Test with provider config."""
        config = RLMConfig.from_dict({
            "root_provider": {
                "provider": "openai",
                "model": "gpt-4o",
            }
        })
        
        assert config.root_provider is not None
        assert config.root_provider.provider == "openai"
    
    def test_with_security(self):
        """Test with security config."""
        config = RLMConfig.from_dict({
            "security": {
                "sandbox": False,
                "max_execution_time": 60.0,
            }
        })
        
        assert config.security.sandbox is False
        assert config.security.max_execution_time == 60.0


class TestRLMConfigFromEnv:
    """Tests for RLMConfig.from_env."""
    
    def test_reads_env_vars(self, monkeypatch):
        """Test reading from environment."""
        monkeypatch.setenv("RLM_MAX_ITERATIONS", "200")
        monkeypatch.setenv("RLM_MAX_COST", "100.0")
        
        config = RLMConfig.from_env()
        
        assert config.max_iterations == 200
        assert config.max_cost == 100.0
    
    def test_sandbox_from_env(self, monkeypatch):
        """Test sandbox from env."""
        monkeypatch.setenv("RLM_SANDBOX", "false")
        
        config = RLMConfig.from_env()
        
        assert config.security.sandbox is False


class TestRLMConfigToDict:
    """Tests for RLMConfig.to_dict."""
    
    def test_basic_export(self):
        """Test basic export."""
        config = RLMConfig(max_iterations=100)
        data = config.to_dict()
        
        assert data["max_iterations"] == 100
        assert "security" in data
