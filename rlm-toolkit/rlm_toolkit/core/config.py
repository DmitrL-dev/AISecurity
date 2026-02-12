"""
Configuration
=============

Pydantic-based configuration with validation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


@dataclass
class SecurityConfig:
    """Security configuration.
    
    Attributes:
        sandbox: Enable code sandbox
        max_execution_time: Max seconds per code execution
        max_memory_mb: Max memory in MB
        blocked_imports: Additional imports to block
        blocked_builtins: Additional builtins to block
        virtual_fs: Enable virtual filesystem
        virtual_fs_quota_mb: Virtual FS quota in MB
    """
    sandbox: bool = True
    max_execution_time: float = 30.0
    max_memory_mb: int = 512
    blocked_imports: List[str] = field(default_factory=list)
    blocked_builtins: List[str] = field(default_factory=list)
    virtual_fs: bool = True
    virtual_fs_quota_mb: int = 100


@dataclass
class ProviderConfig:
    """Provider configuration.
    
    Attributes:
        provider: Provider name (openai, anthropic, ollama, google)
        model: Model identifier
        api_key: API key (or env var name)
        base_url: Custom base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
    """
    provider: str
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        if self.api_key:
            # Check if it's an env var reference
            if self.api_key.startswith("$"):
                return os.environ.get(self.api_key[1:])
            return self.api_key
        
        # Default env var names
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        var_name = env_vars.get(self.provider.lower())
        if var_name:
            return os.environ.get(var_name)
        return None


@dataclass
class ObservabilityConfig:
    """Observability configuration.
    
    Attributes:
        enabled: Enable observability
        console_logging: Log to console
        langfuse: Enable Langfuse
        langsmith: Enable LangSmith
        trace_all: Trace all operations (verbose)
    """
    enabled: bool = True
    console_logging: bool = False
    langfuse: bool = False
    langsmith: bool = False
    trace_all: bool = False


@dataclass
class MemoryConfig:
    """Memory configuration.
    
    Attributes:
        enabled: Enable memory
        type: Memory type (buffer, episodic)
        max_entries: Maximum entries
        k_similarity: Similarity results (episodic)
        k_contiguity: Contiguity window (episodic)
    """
    enabled: bool = False
    type: str = "buffer"
    max_entries: int = 1000
    k_similarity: int = 5
    k_contiguity: int = 2


@dataclass
class RLMConfig:
    """Complete RLM configuration.
    
    Combines all sub-configurations with validation.
    
    Example:
        >>> config = RLMConfig(
        ...     max_iterations=50,
        ...     max_cost=10.0,
        ...     root_provider=ProviderConfig("openai", "gpt-5.2"),
        ... )
    
    Attributes:
        max_iterations: Maximum REPL iterations
        max_subcalls: Maximum sub-LLM calls
        max_cost: Maximum cost in USD
        timeout: Total timeout in seconds
        root_provider: Root provider config
        sub_provider: Sub-provider config (optional)
        security: Security configuration
        observability: Observability configuration
        memory: Memory configuration
    """
    max_iterations: int = 50
    max_subcalls: int = 100
    max_cost: float = 10.0
    timeout: float = 600.0
    
    root_provider: Optional[ProviderConfig] = None
    sub_provider: Optional[ProviderConfig] = None
    
    security: SecurityConfig = field(default_factory=SecurityConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    
    def validate(self) -> List[str]:
        """Validate configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if self.max_iterations < 1:
            errors.append("max_iterations must be >= 1")
        
        if self.max_iterations > 1000:
            errors.append("max_iterations should be <= 1000")
        
        if self.max_cost < 0:
            errors.append("max_cost must be >= 0")
        
        if self.timeout < 1:
            errors.append("timeout must be >= 1")
        
        if self.security.max_execution_time < 0.1:
            errors.append("max_execution_time must be >= 0.1")
        
        if self.security.max_memory_mb < 64:
            errors.append("max_memory_mb must be >= 64")
        
        if self.memory.enabled and self.memory.type not in ("buffer", "episodic"):
            errors.append(f"Unknown memory type: {self.memory.type}")
        
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RLMConfig":
        """Create config from dictionary."""
        config = cls()
        
        # Simple fields
        for key in ["max_iterations", "max_subcalls", "max_cost", "timeout"]:
            if key in data:
                setattr(config, key, data[key])
        
        # Root provider
        if "root_provider" in data:
            rp = data["root_provider"]
            config.root_provider = ProviderConfig(**rp)
        
        # Sub provider
        if "sub_provider" in data:
            sp = data["sub_provider"]
            config.sub_provider = ProviderConfig(**sp)
        
        # Security
        if "security" in data:
            config.security = SecurityConfig(**data["security"])
        
        # Observability
        if "observability" in data:
            config.observability = ObservabilityConfig(**data["observability"])
        
        # Memory
        if "memory" in data:
            config.memory = MemoryConfig(**data["memory"])
        
        return config
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "RLMConfig":
        """Load config from YAML file."""
        import yaml
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_env(cls) -> "RLMConfig":
        """Create config from environment variables."""
        config = cls()
        
        # RLM_ prefix
        if os.environ.get("RLM_MAX_ITERATIONS"):
            config.max_iterations = int(os.environ["RLM_MAX_ITERATIONS"])
        
        if os.environ.get("RLM_MAX_COST"):
            config.max_cost = float(os.environ["RLM_MAX_COST"])
        
        if os.environ.get("RLM_TIMEOUT"):
            config.timeout = float(os.environ["RLM_TIMEOUT"])
        
        if os.environ.get("RLM_SANDBOX"):
            config.security.sandbox = os.environ["RLM_SANDBOX"].lower() in ("true", "1", "yes")
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Export config to dictionary."""
        from dataclasses import asdict
        return asdict(self)
