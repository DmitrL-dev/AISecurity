"""Unit tests for core module components."""

import pytest
from rlm_toolkit.core.config import RLMConfig, SecurityConfig, ProviderConfig
from rlm_toolkit.core.context import LazyContext
from rlm_toolkit.core.exceptions import (
    RLMError,
    ProviderError,
    SecurityError,
    ConfigurationError,
    BudgetExceededError,
    ExecutionTimeoutError,
    IterationLimitError,
    RateLimitError,
    AuthenticationError,
    BlockedImportError,
)
from rlm_toolkit.core.state import RLMState


class TestRLMConfig:
    """Tests for RLMConfig."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = RLMConfig()
        
        assert config.max_iterations > 0
        assert config.max_cost > 0
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = RLMConfig(
            max_iterations=50,
            max_cost=10.0,
            timeout=600.0,
        )
        
        assert config.max_iterations == 50
        assert config.max_cost == 10.0
        assert config.timeout == 600.0
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = RLMConfig()
        errors = config.validate()
        
        # Default config should be valid
        assert len(errors) == 0
    
    def test_invalid_config_negative_iterations(self):
        """Test invalid config with negative iterations."""
        config = RLMConfig(max_iterations=-1)
        errors = config.validate()
        
        assert len(errors) > 0


class TestSecurityConfig:
    """Tests for SecurityConfig."""
    
    def test_default_security_config(self):
        """Test default security configuration."""
        config = SecurityConfig()
        
        assert config.sandbox is True
        assert config.max_execution_time > 0
    
    def test_custom_security_config(self):
        """Test custom security configuration."""
        config = SecurityConfig(
            sandbox=False,
            max_execution_time=60.0,
            max_memory_mb=1024,
        )
        
        assert config.sandbox is False
        assert config.max_execution_time == 60.0


class TestProviderConfig:
    """Tests for ProviderConfig."""
    
    def test_provider_config(self):
        """Test provider configuration."""
        config = ProviderConfig(
            provider="openai",
            model="gpt-4",
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"


class TestLazyContext:
    """Tests for LazyContext."""
    
    def test_from_string(self):
        """Test creating from string."""
        ctx = LazyContext("Hello, World!")
        
        assert len(ctx) == 13
        assert "Hello" in str(ctx)
    
    def test_from_file(self, tmp_path):
        """Test creating from file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("File content here")
        
        ctx = LazyContext(str(test_file))
        
        assert "File content" in str(ctx)
    
    def test_length(self):
        """Test length calculation."""
        ctx = LazyContext("12345")
        assert len(ctx) == 5
    
    def test_slice(self):
        """Test slicing context."""
        ctx = LazyContext("Hello, World!")
        
        sliced = ctx.slice(0, 5)
        assert sliced == "Hello"
    
    def test_hash(self):
        """Test hash computation."""
        ctx = LazyContext("test content")
        
        hash_val = ctx.hash
        assert len(hash_val) == 16
    
    def test_chunks(self):
        """Test chunk iteration."""
        content = "a" * 1000
        ctx = LazyContext(content)
        
        chunks = list(ctx.chunks(size=100))
        assert len(chunks) == 10


class TestRLMExceptions:
    """Tests for exception hierarchy."""
    
    def test_rlm_error_base(self):
        """Test base RLM error."""
        error = RLMError("Test error")
        assert "Test error" in str(error)
        assert isinstance(error, Exception)
    
    def test_provider_error(self):
        """Test provider error."""
        error = ProviderError("API failed", provider="openai", status_code=500)
        
        assert "API failed" in str(error)
        assert error.provider == "openai"
        assert error.status_code == 500
    
    def test_security_error(self):
        """Test security error."""
        error = SecurityError("Blocked operation", violation_type="import")
        assert isinstance(error, RLMError)
    
    def test_configuration_error(self):
        """Test configuration error."""
        error = ConfigurationError("Invalid config")
        assert isinstance(error, RLMError)
    
    def test_budget_exceeded_error(self):
        """Test budget exceeded error."""
        error = BudgetExceededError(budget=10.0, spent=15.0)
        
        assert error.budget == 10.0
        assert error.spent == 15.0
    
    def test_execution_timeout_error(self):
        """Test execution timeout error."""
        error = ExecutionTimeoutError(timeout=30.0)
        assert error.timeout == 30.0
    
    def test_iteration_limit_error(self):
        """Test iteration limit error."""
        error = IterationLimitError(max_iterations=50, current=100)
        assert "100" in str(error)
    
    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError(provider="openai", retry_after=60.0)
        assert error.retry_after == 60.0
    
    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError(provider="anthropic")
        assert "anthropic" in str(error)
    
    def test_blocked_import_error(self):
        """Test blocked import error."""
        error = BlockedImportError(module="os")
        assert "os" in str(error)


class TestRLMState:
    """Tests for RLMState."""
    
    def test_state_creation(self):
        """Test state creation."""
        state = RLMState()
        
        assert state.iteration == 0
        assert state.total_cost == 0.0
    
    def test_state_increment(self):
        """Test state increment."""
        state = RLMState()
        state.iteration = 5
        state.total_cost = 1.5
        
        assert state.iteration == 5
        assert state.total_cost == 1.5
