"""
SENTINEL Shield — Python SDK for AI Firewall.

Sub-millisecond prompt injection detection powered by Rust + C.

Usage:
    from sentinel_shield import Shield

    shield = Shield(api_key="sk-...")
    result = shield.scan("user prompt here")

    if result.safe:
        # forward to LLM
        pass
"""

from .client import Shield
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    ServerError,
    ShieldError,
    TimeoutError,
    ValidationError,
)
from .models import (
    EngineResult,
    HealthStatus,
    RedactResult,
    ScanResult,
    ShieldConfig,
    Threat,
    Verdict,
)

__all__ = [
    # Client
    "Shield",
    # Config
    "ShieldConfig",
    # Results
    "ScanResult",
    "RedactResult",
    "HealthStatus",
    "Threat",
    "EngineResult",
    "Verdict",
    # Exceptions
    "ShieldError",
    "AuthenticationError",
    "ConnectionError",
    "RateLimitError",
    "ServerError",
    "TimeoutError",
    "ValidationError",
]

__version__ = "0.1.0"
