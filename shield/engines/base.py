"""
SENTINEL Shield v2.0 — Base Engine Interface

All detection engines inherit from BaseEngine.
Each engine returns EngineResult with risk_score and matched threats.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class ThreatMatch:
    """Single threat detection result."""

    threat_type: str  # e.g., "prompt_injection", "jailbreak", "pii_snils"
    risk_score: float  # 0.0 - 1.0
    engine: str  # engine name that detected it
    description: str = ""
    matched_text: str = ""  # snippet that triggered detection
    category: str = ""  # high-level category
    metadata: dict = field(default_factory=dict)


@dataclass
class EngineResult:
    """Result from a single detection engine."""

    engine_name: str
    risk_score: float = 0.0  # max risk from this engine
    threats: list[ThreatMatch] = field(default_factory=list)
    latency_ms: float = 0.0
    error: Optional[str] = None

    @property
    def has_threats(self) -> bool:
        return len(self.threats) > 0


class BaseEngine(ABC):
    """
    Abstract base class for detection engines.

    Each engine:
    1. Has a name and weight (for fusion)
    2. Can analyze text synchronously or asynchronously
    3. Returns EngineResult
    """

    def __init__(self, name: str, weight: float = 1.0, enabled: bool = True):
        self.name = name
        self.weight = weight
        self.enabled = enabled
        self._total_checks = 0
        self._total_detections = 0

    @abstractmethod
    def analyze(self, text: str) -> EngineResult:
        """
        Analyze text for threats.
        Must be implemented by each engine.
        """
        ...

    def safe_analyze(self, text: str) -> EngineResult:
        """Analyze with error handling and timing."""
        if not self.enabled:
            return EngineResult(engine_name=self.name)

        start = time.perf_counter()
        try:
            result = self.analyze(text)
            result.latency_ms = (time.perf_counter() - start) * 1000
            self._total_checks += 1
            if result.has_threats:
                self._total_detections += 1
            return result
        except Exception as e:
            return EngineResult(
                engine_name=self.name,
                latency_ms=(time.perf_counter() - start) * 1000,
                error=str(e),
            )

    def stats(self) -> dict:
        return {
            "name": self.name,
            "enabled": self.enabled,
            "weight": self.weight,
            "total_checks": self._total_checks,
            "total_detections": self._total_detections,
            "detection_rate": (
                self._total_detections / max(self._total_checks, 1) * 100
            ),
        }
