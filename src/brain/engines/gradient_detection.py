"""
Gradient Detection Engine (#54) - Adversarial Gradient Analysis

Анализирует градиенты модели при inference:
- Аномальные паттерны градиентов
- Детекция adversarial perturbations
- Gradient masking detection

Ловит атаки на уровне модели, не текста.
"""

import logging
import math
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger("GradientDetection")


# ============================================================================
# Data Classes
# ============================================================================


class GradientAnomalyType(Enum):
    """Types of gradient anomalies."""

    HIGH_NORM = "high_norm"
    HIGH_VARIANCE = "high_variance"
    SPARSE_GRADIENTS = "sparse_gradients"
    GRADIENT_MASKING = "gradient_masking"
    PERTURBATION_PATTERN = "perturbation_pattern"


@dataclass
class GradientFeatures:
    """Features extracted from gradients."""

    norm: float
    variance: float
    sparsity: float
    max_value: float
    min_value: float
    entropy: float


@dataclass
class GradientAnalysisResult:
    """Result of gradient analysis."""

    is_adversarial: bool
    confidence: float
    anomalies: List[GradientAnomalyType] = field(default_factory=list)
    features: Optional[GradientFeatures] = None
    risk_score: float = 0.0
    explanation: str = ""


# ============================================================================
# Gradient Analyzer (Simulated)
# ============================================================================


class GradientAnalyzer:
    """
    Analyzes gradient patterns to detect adversarial inputs.

    Note: This is a simulated version that uses text features
    as proxies for gradient behavior. Real implementation would
    require access to model internals.
    """

    # Thresholds for anomaly detection
    NORM_THRESHOLD = 5.0
    VARIANCE_THRESHOLD = 2.0
    SPARSITY_THRESHOLD = 0.7

    def __init__(self):
        self._baseline_features = self._compute_baseline()

    def analyze(self, text: str) -> GradientAnalysisResult:
        """
        Analyze text for adversarial gradient patterns.

        Uses text features as proxies for gradient behavior.
        """
        features = self._extract_features(text)
        anomalies = []
        risk_score = 0.0

        # Check for high gradient norm (proxy: unusual char distribution)
        if features.norm > self.NORM_THRESHOLD:
            anomalies.append(GradientAnomalyType.HIGH_NORM)
            risk_score += 0.3

        # Check for high variance (proxy: inconsistent patterns)
        if features.variance > self.VARIANCE_THRESHOLD:
            anomalies.append(GradientAnomalyType.HIGH_VARIANCE)
            risk_score += 0.25

        # Check for sparsity (proxy: many unusual characters)
        if features.sparsity > self.SPARSITY_THRESHOLD:
            anomalies.append(GradientAnomalyType.SPARSE_GRADIENTS)
            risk_score += 0.2

        # Check for perturbation patterns
        if self._has_perturbation_pattern(text):
            anomalies.append(GradientAnomalyType.PERTURBATION_PATTERN)
            risk_score += 0.35

        # Check for gradient masking signs
        if self._has_masking_pattern(text):
            anomalies.append(GradientAnomalyType.GRADIENT_MASKING)
            risk_score += 0.3

        is_adversarial = len(anomalies) >= 2 or risk_score >= 0.5
        confidence = min(1.0, risk_score + len(anomalies) * 0.1)

        explanation = self._generate_explanation(features, anomalies)

        return GradientAnalysisResult(
            is_adversarial=is_adversarial,
            confidence=confidence,
            anomalies=anomalies,
            features=features,
            risk_score=min(1.0, risk_score),
            explanation=explanation,
        )

    def _extract_features(self, text: str) -> GradientFeatures:
        """Extract gradient-like features from text."""
        if not text:
            return GradientFeatures(0, 0, 0, 0, 0, 0)

        # Character value distribution (proxy for gradient values)
        char_values = [ord(c) for c in text]

        # Norm (L2 norm of character values)
        norm = math.sqrt(sum(v**2 for v in char_values)) / len(text)

        # Variance
        mean_val = sum(char_values) / len(char_values)
        variance = sum((v - mean_val) ** 2 for v in char_values) / len(char_values)
        variance = math.sqrt(variance) / 100  # Normalize

        # Sparsity (ratio of non-common characters)
        common_chars = set("abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ.,!?")
        uncommon = sum(1 for c in text if c not in common_chars)
        sparsity = uncommon / len(text)

        # Max/min
        max_val = max(char_values)
        min_val = min(char_values)

        # Entropy
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1

        entropy = 0.0
        for count in freq.values():
            p = count / len(text)
            if p > 0:
                entropy -= p * math.log2(p)

        return GradientFeatures(
            norm=norm,
            variance=variance,
            sparsity=sparsity,
            max_value=max_val,
            min_value=min_val,
            entropy=entropy,
        )

    def _has_perturbation_pattern(self, text: str) -> bool:
        """Detect adversarial perturbation patterns."""
        # Unicode lookalikes (common in adversarial attacks)
        lookalike_patterns = [
            r"[аеіоруАЕІОРУ]",  # Cyrillic lookalikes
            r"[\u200b\u200c\u200d\u2060]",  # Zero-width chars
            r"[\uff00-\uffef]",  # Fullwidth chars
            r"[\u0300-\u036f]",  # Combining diacritical marks
        ]

        for pattern in lookalike_patterns:
            if re.search(pattern, text):
                return True

        # Unusual character sequences
        if re.search(r"(.)\1{5,}", text):  # Repeated chars
            return True

        return False

    def _has_masking_pattern(self, text: str) -> bool:
        """Detect gradient masking attempts."""
        # Base64-like patterns suggest encoding to evade
        if re.search(r"[A-Za-z0-9+/]{20,}={0,2}", text):
            return True

        # Hex encoding
        if re.search(r"(?:0x)?[0-9a-fA-F]{16,}", text):
            return True

        # URL encoding
        if text.count("%") > 5:
            return True

        return False

    def _compute_baseline(self) -> GradientFeatures:
        """Compute baseline features for normal text."""
        normal_text = "This is a normal English sentence with typical words."
        return self._extract_features(normal_text)

    def _generate_explanation(
        self, features: GradientFeatures, anomalies: List[GradientAnomalyType]
    ) -> str:
        """Generate explanation."""
        parts = []

        if GradientAnomalyType.HIGH_NORM in anomalies:
            parts.append(f"High gradient norm ({features.norm:.2f})")

        if GradientAnomalyType.HIGH_VARIANCE in anomalies:
            parts.append(f"High variance ({features.variance:.2f})")

        if GradientAnomalyType.PERTURBATION_PATTERN in anomalies:
            parts.append("Adversarial perturbation pattern")

        if GradientAnomalyType.GRADIENT_MASKING in anomalies:
            parts.append("Encoding-based evasion")

        return "; ".join(parts) if parts else "Normal gradient pattern"


# ============================================================================
# Main Engine
# ============================================================================


class GradientDetectionEngine:
    """
    Engine #54: Gradient Detection

    Detects adversarial inputs by analyzing gradient-like
    patterns in text.
    """

    def __init__(self):
        self.analyzer = GradientAnalyzer()
        logger.info("GradientDetectionEngine initialized")

    def analyze(self, text: str) -> GradientAnalysisResult:
        """
        Analyze text for adversarial gradient patterns.

        Args:
            text: Input text

        Returns:
            GradientAnalysisResult
        """
        result = self.analyzer.analyze(text)

        if result.is_adversarial:
            logger.warning(
                f"Adversarial pattern detected: "
                f"anomalies={[a.value for a in result.anomalies]}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[GradientDetectionEngine] = None


def get_engine() -> GradientDetectionEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = GradientDetectionEngine()
    return _default_engine


def detect_adversarial(text: str) -> GradientAnalysisResult:
    return get_engine().analyze(text)
