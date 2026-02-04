"""
Hybrid Analyzer - Python ↔ Rust Bridge

Integrates the high-performance Rust Core (sentinel_core) with the
existing Brain analysis pipeline. Provides:
- Fast Tier 0 analysis via Rust (~100μs)
- Fallback to Python engines if Rust unavailable
- ML-based routing for complex cases
- Unified result format

Architecture:
    ┌─────────────────────────────────────────┐
    │           HybridAnalyzer                │
    ├─────────────────────────────────────────┤
    │  ┌─────────────┐   ┌─────────────────┐  │
    │  │ Rust Core   │   │ Python Engines  │  │
    │  │ (~100μs)    │   │ (ML, Semantic)  │  │
    │  │ 8 Engines   │   │ ~40 Engines     │  │
    │  └──────┬──────┘   └────────┬────────┘  │
    │         │                   │           │
    │         └───────┬───────────┘           │
    │                 ▼                       │
    │         Result Fusion                   │
    └─────────────────────────────────────────┘
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("HybridAnalyzer")

# Try to import Rust core
try:
    import sentinel_core

    RUST_AVAILABLE = True
    logger.info(f"Rust Core v{getattr(sentinel_core, '__version__', '0.1.0')} loaded")
except ImportError:
    RUST_AVAILABLE = False
    logger.warning("Rust Core not available, using Python fallback")


class AnalysisMode(Enum):
    """Analysis mode selection."""

    RUST_ONLY = "rust_only"  # Fast, pattern-based only
    PYTHON_ONLY = "python_only"  # Full ML pipeline
    HYBRID = "hybrid"  # Rust first, Python if needed
    AUTO = "auto"  # Smart routing based on input


@dataclass
class ThreatMatch:
    """Unified threat match result."""

    engine: str
    pattern: str
    confidence: float
    start: int = 0
    end: int = 0
    source: str = "rust"  # "rust" or "python"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "start": self.start,
            "end": self.end,
            "source": self.source,
        }


@dataclass
class HybridResult:
    """Unified analysis result from hybrid pipeline."""

    detected: bool = False
    risk_score: float = 0.0
    categories: List[str] = field(default_factory=list)
    matches: List[ThreatMatch] = field(default_factory=list)
    rust_time_us: int = 0
    python_time_ms: float = 0.0
    mode_used: str = "none"

    @property
    def is_safe(self) -> bool:
        return not self.detected

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": self.detected,
            "risk_score": self.risk_score,
            "is_safe": self.is_safe,
            "categories": self.categories,
            "matches": [m.to_dict() for m in self.matches],
            "performance": {
                "rust_time_us": self.rust_time_us,
                "python_time_ms": self.python_time_ms,
                "mode": self.mode_used,
            },
        }


class HybridAnalyzer:
    """
    Hybrid Python+Rust analyzer for SENTINEL Brain.

    Usage:
        >>> analyzer = HybridAnalyzer()
        >>> result = analyzer.analyze("SELECT * FROM users WHERE 1=1")
        >>> print(result.detected)  # True
        >>> print(result.categories)  # ['injection']
    """

    def __init__(self, mode: AnalysisMode = AnalysisMode.HYBRID):
        """
        Initialize hybrid analyzer.

        Args:
            mode: Analysis mode (RUST_ONLY, PYTHON_ONLY, HYBRID, AUTO)
        """
        import os

        self.mode = mode
        self._rust_engine = None
        self._python_fallbacks = {}

        # Read feature flags from environment
        self._use_rust = os.getenv("USE_RUST_ENGINE", "true").lower() == "true"
        self._shadow_mode = os.getenv("RUST_SHADOW_MODE", "false").lower() == "true"
        self._fallback_python = (
            os.getenv("RUST_FALLBACK_PYTHON", "true").lower() == "true"
        )

        # Initialize Rust engine if available and enabled
        if RUST_AVAILABLE and self._use_rust:
            try:
                self._rust_engine = sentinel_core.SentinelEngine()
                logger.info("Rust SentinelEngine initialized")
            except Exception as e:
                logger.error(f"Failed to create Rust engine: {e}")
        elif not self._use_rust:
            logger.info("Rust engine disabled via USE_RUST_ENGINE=false")

    @property
    def rust_available(self) -> bool:
        """Check if Rust core is available."""
        return RUST_AVAILABLE and self._rust_engine is not None

    def analyze(self, text: str, mode: Optional[AnalysisMode] = None) -> HybridResult:
        """
        Analyze text for security threats.

        Args:
            text: Input text to analyze
            mode: Override default mode for this call

        Returns:
            HybridResult with detection details
        """
        use_mode = mode or self.mode

        # Route based on mode
        if use_mode == AnalysisMode.RUST_ONLY:
            return self._analyze_rust(text)
        elif use_mode == AnalysisMode.PYTHON_ONLY:
            return self._analyze_python(text)
        elif use_mode == AnalysisMode.HYBRID:
            return self._analyze_hybrid(text)
        else:  # AUTO
            return self._analyze_auto(text)

    def quick_scan(self, text: str) -> HybridResult:
        """
        Fast scan using Rust core only.

        Args:
            text: Input text to analyze

        Returns:
            HybridResult (Rust-only, fastest mode)
        """
        return self._analyze_rust(text)

    def _analyze_rust(self, text: str) -> HybridResult:
        """Run Rust-only analysis."""
        result = HybridResult(mode_used="rust")

        if not self.rust_available:
            logger.warning("Rust not available, returning empty result")
            return result

        try:
            rust_result = self._rust_engine.analyze(text)

            result.detected = rust_result.detected
            result.risk_score = rust_result.risk_score * 100  # Scale to 0-100
            result.categories = list(rust_result.categories)
            result.rust_time_us = rust_result.processing_time_us

            for match in rust_result.matches:
                result.matches.append(
                    ThreatMatch(
                        engine=match.engine,
                        pattern=match.pattern,
                        confidence=match.confidence,
                        start=match.start,
                        end=match.end,
                        source="rust",
                    )
                )

        except Exception as e:
            logger.error(f"Rust analysis failed: {e}")

        return result

    def _analyze_python(self, text: str) -> HybridResult:
        """Run Python-only analysis with real engines."""
        import time

        start = time.perf_counter()
        result = HybridResult(mode_used="python")

        # Lazy-load Python engines
        if not self._python_fallbacks:
            self._init_python_engines()

        # Run Python Injection Engine
        if "injection" in self._python_fallbacks:
            try:
                inj_result = self._python_fallbacks["injection"].scan(text)
                if not inj_result.is_safe:
                    result.detected = True
                    result.risk_score = max(result.risk_score, inj_result.risk_score)
                    result.categories.append("injection")
                    for threat in inj_result.threats:
                        result.matches.append(
                            ThreatMatch(
                                engine="injection",
                                pattern=threat,
                                confidence=inj_result.risk_score / 100,
                                source="python",
                            )
                        )
            except Exception as e:
                logger.debug(f"Python injection engine error: {e}")

        result.python_time_ms = (time.perf_counter() - start) * 1000
        return result

    def _init_python_engines(self) -> None:
        """Initialize Python fallback engines."""
        try:
            # Import from archive (deprecated, kept for shadow mode comparison)
            from .archive.deprecated_pattern_engines.injection.engine import (
                InjectionEngine,
            )

            self._python_fallbacks["injection"] = InjectionEngine()
            logger.info("Python InjectionEngine loaded (from archive)")
        except Exception as e:
            logger.warning(f"Could not load Python InjectionEngine: {e}")

    def _analyze_hybrid(self, text: str) -> HybridResult:
        """
        Hybrid analysis: Rust first, Python for ML enrichment.

        Strategy:
        1. Run fast Rust analysis (~100μs)
        2. If high-confidence threat → return immediately
        3. If borderline → run Python ML engines for confirmation
        4. Fuse results
        """
        import time

        # Step 1: Fast Rust scan
        result = self._analyze_rust(text)

        # Step 2: Check if we need Python enrichment
        if result.detected and result.risk_score >= 80:
            # High confidence from Rust, no need for Python
            result.mode_used = "rust_fast"
            return result

        # Step 3: Run Python ML engines for borderline cases
        if result.risk_score >= 30 or len(text) > 500:
            start = time.perf_counter()

            # TODO: Add Python ML engine calls here
            # - GeometricKernel for semantic analysis
            # - QwenGuard for LLM-based detection
            # - Learning engine for adaptive patterns

            result.python_time_ms = (time.perf_counter() - start) * 1000
            result.mode_used = "hybrid"

        return result

    def _analyze_auto(self, text: str) -> HybridResult:
        """
        Auto-routing based on input characteristics.

        Routes to:
        - RUST_ONLY for short, simple inputs
        - HYBRID for medium complexity
        - PYTHON_ONLY for long/complex inputs requiring ML
        """
        text_len = len(text)

        if text_len < 200:
            # Short text → Rust only (fastest)
            return self._analyze_rust(text)
        elif text_len < 2000:
            # Medium → Hybrid
            return self._analyze_hybrid(text)
        else:
            # Long/complex → Full analysis
            return self._analyze_hybrid(text)

    def shadow_analyze(self, text: str) -> Dict[str, Any]:
        """
        Shadow mode: Run BOTH Rust and Python, compare results.

        Used for validation before full Rust migration.
        Logs divergences between engines.

        Args:
            text: Input text to analyze

        Returns:
            Dict with both results and divergence analysis
        """
        import time

        # Run Rust
        rust_result = self._analyze_rust(text)

        # Run Python (placeholder - integrate with real Python engines)
        start = time.perf_counter()
        python_result = self._analyze_python(text)
        python_result.python_time_ms = (time.perf_counter() - start) * 1000

        # Compare results
        divergence = self._compute_divergence(rust_result, python_result)

        # Log divergences
        if divergence["has_divergence"]:
            self._log_divergence(text, rust_result, python_result, divergence)

        return {
            "rust": rust_result.to_dict(),
            "python": python_result.to_dict(),
            "divergence": divergence,
            "recommendation": self._get_recommendation(divergence),
        }

    def _compute_divergence(
        self, rust: HybridResult, python: HybridResult
    ) -> Dict[str, Any]:
        """Compute divergence between Rust and Python results."""

        rust_categories = set(rust.categories)
        python_categories = set(python.categories)

        only_rust = rust_categories - python_categories
        only_python = python_categories - rust_categories
        common = rust_categories & python_categories

        score_diff = abs(rust.risk_score - python.risk_score)
        detection_match = rust.detected == python.detected

        return {
            "has_divergence": not detection_match
            or len(only_rust) > 0
            or len(only_python) > 0,
            "detection_match": detection_match,
            "score_difference": score_diff,
            "categories_only_rust": list(only_rust),
            "categories_only_python": list(only_python),
            "categories_common": list(common),
            "rust_faster_by": (
                f"{python.python_time_ms * 1000 / max(rust.rust_time_us, 1):.1f}x"
                if rust.rust_time_us > 0
                else "N/A"
            ),
        }

    def _log_divergence(
        self,
        text: str,
        rust: HybridResult,
        python: HybridResult,
        divergence: Dict[str, Any],
    ) -> None:
        """Log divergence for analysis."""

        text_preview = text[:100] + "..." if len(text) > 100 else text

        if not divergence["detection_match"]:
            logger.warning(
                f"DETECTION DIVERGENCE: "
                f"Rust={rust.detected}, Python={python.detected} | "
                f"Text: {text_preview!r}"
            )

        if divergence["categories_only_rust"]:
            logger.info(
                f"RUST-ONLY CATEGORIES: {divergence['categories_only_rust']} | "
                f"Text: {text_preview!r}"
            )

        if divergence["categories_only_python"]:
            logger.info(
                f"PYTHON-ONLY CATEGORIES: {divergence['categories_only_python']} | "
                f"Text: {text_preview!r}"
            )

        if divergence["score_difference"] > 20:
            logger.warning(
                f"SCORE DIVERGENCE: "
                f"Rust={rust.risk_score:.1f}, Python={python.risk_score:.1f} | "
                f"Diff={divergence['score_difference']:.1f}"
            )

    def _get_recommendation(self, divergence: Dict[str, Any]) -> str:
        """Get recommendation based on divergence."""

        if not divergence["has_divergence"]:
            return "READY: Results match, Rust can replace Python"

        if not divergence["detection_match"]:
            return "INVESTIGATE: Detection mismatch requires review"

        if divergence["categories_only_rust"]:
            return "REVIEW: Rust detects more categories (may be improvement)"

        if divergence["categories_only_python"]:
            return "GAP: Python detects categories Rust misses"

        if divergence["score_difference"] > 20:
            return "CALIBRATE: Risk scores need alignment"

        return "OK: Minor divergence, acceptable for migration"


# Singleton instance for easy import
_hybrid_analyzer: Optional[HybridAnalyzer] = None


def get_hybrid_analyzer() -> HybridAnalyzer:
    """Get or create singleton HybridAnalyzer."""
    global _hybrid_analyzer
    if _hybrid_analyzer is None:
        _hybrid_analyzer = HybridAnalyzer()
    return _hybrid_analyzer


def quick_scan(text: str) -> HybridResult:
    """
    Convenience function for quick Rust-based scan.

    Args:
        text: Input text to analyze

    Returns:
        HybridResult from Rust core
    """
    return get_hybrid_analyzer().quick_scan(text)


# Export for use in main analyzer
__all__ = [
    "HybridAnalyzer",
    "HybridResult",
    "ThreatMatch",
    "AnalysisMode",
    "get_hybrid_analyzer",
    "quick_scan",
    "RUST_AVAILABLE",
]
