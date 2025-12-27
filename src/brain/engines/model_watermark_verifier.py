"""
Model Watermark Verifier Engine - IP Protection

Verifies model watermarks for IP protection:
- Output fingerprinting
- Statistical watermark detection
- Model attribution
- Provenance verification

Addresses: Enterprise AI Governance
Research: model_watermarking_deep_dive.md
Invention: Model Watermark Verifier (#46)
"""

import hashlib
import logging
import time
import math
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ModelWatermarkVerifier")


# ============================================================================
# Data Classes
# ============================================================================


class WatermarkType(Enum):
    """Types of watermarks."""

    STATISTICAL = "statistical"
    TOKEN_PATTERN = "token_pattern"
    EMBEDDING = "embedding"
    FINGERPRINT = "fingerprint"


@dataclass
class WatermarkResult:
    """Result from watermark verification."""

    has_watermark: bool
    confidence: float
    watermark_type: Optional[WatermarkType] = None
    model_id: str = ""
    signature: str = ""
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "has_watermark": self.has_watermark,
            "confidence": self.confidence,
            "watermark_type": (
                self.watermark_type.value if self.watermark_type else None
            ),
            "model_id": self.model_id,
            "signature": self.signature,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Fingerprint Generator
# ============================================================================


class FingerprintGenerator:
    """
    Generates fingerprints from text output.
    """

    def __init__(self, n_gram_size: int = 3):
        self.n_gram_size = n_gram_size

    def generate(self, text: str) -> str:
        """Generate fingerprint from text."""
        # Get n-grams
        words = text.lower().split()
        if len(words) < self.n_gram_size:
            return hashlib.sha256(text.encode()).hexdigest()[:16]

        ngrams = []
        for i in range(len(words) - self.n_gram_size + 1):
            ngram = " ".join(words[i: i + self.n_gram_size])
            ngrams.append(ngram)

        # Hash sorted ngrams
        ngrams_str = "|".join(sorted(set(ngrams)))
        return hashlib.sha256(ngrams_str.encode()).hexdigest()[:16]

    def similarity(self, fp1: str, fp2: str) -> float:
        """Calculate fingerprint similarity."""
        if fp1 == fp2:
            return 1.0

        # Character overlap
        set1 = set(fp1)
        set2 = set(fp2)
        overlap = len(set1 & set2)
        total = len(set1 | set2)

        return overlap / total if total > 0 else 0.0


# ============================================================================
# Statistical Watermark Detector
# ============================================================================


class StatisticalWatermarkDetector:
    """
    Detects statistical watermarks in text.
    """

    def __init__(self):
        self._known_patterns: Dict[str, List[float]] = {}

    def register_model(self, model_id: str, token_biases: List[float]) -> None:
        """Register model's token bias pattern."""
        self._known_patterns[model_id] = token_biases

    def analyze(self, text: str) -> Tuple[Optional[str], float]:
        """
        Analyze text for statistical watermarks.

        Returns:
            (model_id or None, confidence)
        """
        if not self._known_patterns:
            return None, 0.0

        # Calculate word frequency distribution
        words = text.lower().split()
        freq = Counter(words)
        total = sum(freq.values()) or 1

        # Simplified: check for specific patterns
        # In production, would use more sophisticated analysis
        best_model = None
        best_score = 0.0

        for model_id, biases in self._known_patterns.items():
            # Calculate correlation with known bias
            score = self._calculate_score(freq, total, biases)
            if score > best_score:
                best_score = score
                best_model = model_id

        return best_model, best_score

    def _calculate_score(
        self,
        freq: Counter,
        total: int,
        biases: List[float],
    ) -> float:
        """Calculate match score."""
        # Simplified scoring
        if not biases:
            return 0.0

        # Use word variety as proxy
        variety = len(freq) / (total or 1)
        target_variety = sum(biases) / len(biases)

        diff = abs(variety - target_variety)
        return max(0.0, 1.0 - diff * 5)


# ============================================================================
# Token Pattern Analyzer
# ============================================================================


class TokenPatternAnalyzer:
    """
    Analyzes token patterns for watermarks.
    """

    def __init__(self):
        self._patterns: Dict[str, Set[str]] = {}

    def register_pattern(self, model_id: str, markers: Set[str]) -> None:
        """Register model's marker patterns."""
        self._patterns[model_id] = markers

    def detect(self, text: str) -> Tuple[Optional[str], float]:
        """
        Detect token pattern watermarks.

        Returns:
            (model_id or None, confidence)
        """
        text_lower = text.lower()

        best_model = None
        best_score = 0.0

        for model_id, markers in self._patterns.items():
            matches = sum(1 for m in markers if m.lower() in text_lower)
            score = matches / len(markers) if markers else 0.0

            if score > best_score:
                best_score = score
                best_model = model_id

        return best_model, best_score


# ============================================================================
# Main Engine
# ============================================================================


class ModelWatermarkVerifier:
    """
    Model Watermark Verifier - IP Protection

    Comprehensive watermark verification:
    - Fingerprinting
    - Statistical detection
    - Token pattern analysis

    Invention #46 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self):
        self.fingerprinter = FingerprintGenerator()
        self.stat_detector = StatisticalWatermarkDetector()
        self.pattern_analyzer = TokenPatternAnalyzer()

        self._fingerprint_db: Dict[str, str] = {}

        logger.info("ModelWatermarkVerifier initialized")

    def register_model(
        self,
        model_id: str,
        sample_outputs: List[str] = None,
        token_biases: List[float] = None,
        markers: Set[str] = None,
    ) -> None:
        """Register a model for verification."""
        if sample_outputs:
            for output in sample_outputs:
                fp = self.fingerprinter.generate(output)
                self._fingerprint_db[fp] = model_id

        if token_biases:
            self.stat_detector.register_model(model_id, token_biases)

        if markers:
            self.pattern_analyzer.register_pattern(model_id, markers)

    def verify(self, text: str) -> WatermarkResult:
        """
        Verify watermark in text.

        Args:
            text: Text to verify

        Returns:
            WatermarkResult
        """
        start = time.time()

        # Check fingerprint
        fp = self.fingerprinter.generate(text)
        if fp in self._fingerprint_db:
            return WatermarkResult(
                has_watermark=True,
                confidence=1.0,
                watermark_type=WatermarkType.FINGERPRINT,
                model_id=self._fingerprint_db[fp],
                signature=fp,
                explanation="Exact fingerprint match",
                latency_ms=(time.time() - start) * 1000,
            )

        # Check statistical watermark
        stat_model, stat_conf = self.stat_detector.analyze(text)
        if stat_model and stat_conf > 0.7:
            return WatermarkResult(
                has_watermark=True,
                confidence=stat_conf,
                watermark_type=WatermarkType.STATISTICAL,
                model_id=stat_model,
                signature=fp,
                explanation=f"Statistical match: {stat_conf:.2f}",
                latency_ms=(time.time() - start) * 1000,
            )

        # Check token patterns
        pattern_model, pattern_conf = self.pattern_analyzer.detect(text)
        if pattern_model and pattern_conf > 0.5:
            return WatermarkResult(
                has_watermark=True,
                confidence=pattern_conf,
                watermark_type=WatermarkType.TOKEN_PATTERN,
                model_id=pattern_model,
                signature=fp,
                explanation=f"Pattern match: {pattern_conf:.2f}",
                latency_ms=(time.time() - start) * 1000,
            )

        return WatermarkResult(
            has_watermark=False,
            confidence=0.0,
            signature=fp,
            explanation="No watermark detected",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_verifier: Optional[ModelWatermarkVerifier] = None


def get_verifier() -> ModelWatermarkVerifier:
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = ModelWatermarkVerifier()
    return _default_verifier
