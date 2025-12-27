"""
SENTINEL Security Engine Base Classes

Provides abstract base classes for all security engines:
- BaseEngine: Core engine interface
- BaseDetector: Detection-specific base
- BaseGuard: Protection-specific base
- BaseAnalyzer: Analysis-specific base

All engines should inherit from appropriate base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar
import logging
import time


# ============================================================================
# Type Variables
# ============================================================================

T = TypeVar("T")  # Result type
I = TypeVar("I")  # Input type


# ============================================================================
# Common Enums
# ============================================================================


class Severity(Enum):
    """Threat severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def score(self) -> float:
        """Numeric score for severity."""
        return {
            Severity.INFO: 0.0,
            Severity.LOW: 0.25,
            Severity.MEDIUM: 0.5,
            Severity.HIGH: 0.75,
            Severity.CRITICAL: 1.0,
        }[self]


class Action(Enum):
    """Security actions."""

    ALLOW = "allow"
    BLOCK = "block"
    ALERT = "alert"
    CHALLENGE = "challenge"
    MONITOR = "monitor"
    QUARANTINE = "quarantine"


# ============================================================================
# Base Result Classes
# ============================================================================


@dataclass
class BaseResult:
    """Base class for all engine results."""

    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class DetectionResult(BaseResult):
    """Result from detection engines."""

    detected: bool = False
    confidence: float = 0.0
    severity: Severity = Severity.INFO
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update(
            {
                "detected": self.detected,
                "confidence": self.confidence,
                "severity": self.severity.value,
                "details": self.details,
            }
        )
        return result


@dataclass
class ValidationResult(BaseResult):
    """Result from validation engines."""

    is_valid: bool = True
    violations: List[str] = field(default_factory=list)
    score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update(
            {
                "is_valid": self.is_valid,
                "violations": self.violations,
                "score": self.score,
            }
        )
        return result


@dataclass
class AnalysisResult(BaseResult):
    """Result from analysis engines."""

    findings: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update(
            {
                "findings": self.findings,
                "risk_score": self.risk_score,
                "recommendations": self.recommendations,
            }
        )
        return result


# ============================================================================
# Abstract Base Classes
# ============================================================================


class BaseEngine(ABC):
    """
    Abstract base class for all security engines.

    All engines must implement:
    - name property
    - version property
    - analyze method
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize engine.

        Args:
            config: Optional configuration dictionary
        """
        self._config = config or {}
        self._logger = logging.getLogger(self.__class__.__name__)
        self._initialized = True
        self._logger.info(f"{self.name} v{self.version} initialized")

    @property
    @abstractmethod
    def name(self) -> str:
        """Engine name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Engine version."""
        pass

    @abstractmethod
    def analyze(self, input_data: Any) -> BaseResult:
        """
        Analyze input data.

        Args:
            input_data: Data to analyze

        Returns:
            BaseResult or subclass
        """
        pass

    def _measure_time(self, func, *args, **kwargs):
        """Measure execution time of function."""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000
        return result, elapsed

    @property
    def config(self) -> Dict[str, Any]:
        """Get engine configuration."""
        return self._config.copy()

    def health_check(self) -> bool:
        """Check if engine is healthy."""
        return self._initialized


class BaseDetector(BaseEngine):
    """Base class for detection engines."""

    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """
        Detect threats in text.

        Args:
            text: Input text to analyze

        Returns:
            DetectionResult
        """
        pass

    def analyze(self, input_data: Any) -> DetectionResult:
        """Analyze by detecting."""
        if isinstance(input_data, str):
            return self.detect(input_data)
        raise TypeError(f"Expected str, got {type(input_data)}")


class BaseGuard(BaseEngine):
    """Base class for protection/guard engines."""

    @abstractmethod
    def check(self, text: str) -> ValidationResult:
        """
        Check text for violations.

        Args:
            text: Input text to check

        Returns:
            ValidationResult
        """
        pass

    def analyze(self, input_data: Any) -> ValidationResult:
        """Analyze by checking."""
        if isinstance(input_data, str):
            return self.check(input_data)
        raise TypeError(f"Expected str, got {type(input_data)}")


class BaseAnalyzer(BaseEngine):
    """Base class for analysis engines."""

    @abstractmethod
    def analyze_content(self, text: str) -> AnalysisResult:
        """
        Analyze text content.

        Args:
            text: Input text to analyze

        Returns:
            AnalysisResult
        """
        pass

    def analyze(self, input_data: Any) -> AnalysisResult:
        """Analyze content."""
        if isinstance(input_data, str):
            return self.analyze_content(input_data)
        raise TypeError(f"Expected str, got {type(input_data)}")


# ============================================================================
# Utility Mixins
# ============================================================================


class CacheMixin:
    """Mixin for engines that need caching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, Any] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key in self._cache:
            self._cache_hits += 1
            return self._cache[key]
        self._cache_misses += 1
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()


class MetricsMixin:
    """Mixin for engines that track metrics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._total_calls = 0
        self._total_detections = 0
        self._total_latency_ms = 0.0

    def _record_call(self, detected: bool, latency_ms: float) -> None:
        """Record a call for metrics."""
        self._total_calls += 1
        if detected:
            self._total_detections += 1
        self._total_latency_ms += latency_ms

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get engine metrics."""
        return {
            "total_calls": self._total_calls,
            "total_detections": self._total_detections,
            "detection_rate": (
                self._total_detections / self._total_calls
                if self._total_calls > 0
                else 0.0
            ),
            "avg_latency_ms": (
                self._total_latency_ms / self._total_calls
                if self._total_calls > 0
                else 0.0
            ),
        }
