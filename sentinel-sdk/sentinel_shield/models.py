"""
SENTINEL Shield SDK — Domain Models.

Clean Architecture: These models belong to the domain layer.
They have ZERO dependencies on HTTP, external APIs, or infrastructure.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Optional


class Verdict(str, enum.Enum):
    """Scan verdict from Shield."""

    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"

    @property
    def safe(self) -> bool:
        """True if prompt is safe to forward to LLM."""
        return self == Verdict.ALLOW


@dataclass(frozen=True)
class Threat:
    """Individual threat detected by an engine."""

    threat_type: str
    category: str
    severity: float
    engine: str
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EngineResult:
    """Result from a single detection engine."""

    name: str
    has_threats: bool
    threat_count: int
    threats: list[Threat] = field(default_factory=list)


@dataclass(frozen=True)
class ScanResult:
    """Complete scan result from Shield."""

    verdict: Verdict
    risk_score: float
    latency_ms: float
    engines_checked: list[str]
    threats: list[Threat]
    engine_details: list[EngineResult]
    text_hash: str

    @property
    def safe(self) -> bool:
        """True if the scanned text is safe."""
        return self.verdict.safe

    @property
    def blocked(self) -> bool:
        """True if the text was blocked."""
        return self.verdict == Verdict.BLOCK

    @property
    def threat_types(self) -> list[str]:
        """List of unique threat type names."""
        return list({t.threat_type for t in self.threats})


@dataclass(frozen=True)
class RedactResult:
    """Result from PII redaction."""

    redacted_text: str
    original_length: int
    redacted_length: int
    total_redactions: int
    redactions: list[dict[str, Any]]
    risk_score: float
    verdict: Verdict


@dataclass(frozen=True)
class HealthStatus:
    """Shield health check result."""

    status: str
    version: str
    mode: str
    uptime: float
    patterns: int

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"


@dataclass
class ShieldConfig:
    """SDK configuration.

    Attributes:
        base_url: Shield API base URL (no trailing slash).
        api_key: API key for authentication.
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retries on transient failures.
        retry_backoff: Base backoff time in seconds between retries.
    """

    base_url: str = "https://api.sentinel.dev"
    api_key: Optional[str] = None
    timeout: float = 10.0
    max_retries: int = 3
    retry_backoff: float = 0.5

    def __post_init__(self) -> None:
        # Normalize URL: strip trailing slash
        self.base_url = self.base_url.rstrip("/")

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

        # Validate retries
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
