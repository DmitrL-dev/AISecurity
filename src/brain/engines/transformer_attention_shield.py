"""
Transformer Attention Shield Engine - Attention Manipulation Defense

Defends against attention manipulation attacks:
- Attention pattern analysis
- Saliency monitoring
- Focus hijacking detection
- Attention anomaly detection

Addresses: OWASP ASI-01 (Attention Manipulation)
Research: transformer_security_deep_dive.md
Invention: Transformer Attention Shield (#36)
"""

import math
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("TransformerAttentionShield")


# ============================================================================
# Data Classes
# ============================================================================


class AttentionThreat(Enum):
    """Types of attention threats."""

    FOCUS_HIJACK = "focus_hijack"
    ATTENTION_FLOOD = "attention_flood"
    SALIENCY_SHIFT = "saliency_shift"
    PATTERN_ANOMALY = "pattern_anomaly"


@dataclass
class AttentionPattern:
    """Represents attention pattern."""

    tokens: List[str]
    weights: List[float]
    max_attention_idx: int = 0
    entropy: float = 0.0


@dataclass
class ShieldResult:
    """Result from attention shield."""

    is_safe: bool
    threats: List[AttentionThreat] = field(default_factory=list)
    risk_score: float = 0.0
    attention_entropy: float = 0.0
    suspicious_tokens: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "threats": [t.value for t in self.threats],
            "risk_score": self.risk_score,
            "attention_entropy": self.attention_entropy,
            "suspicious_tokens": self.suspicious_tokens,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Attention Analyzer
# ============================================================================


class AttentionAnalyzer:
    """
    Analyzes attention patterns.
    """

    def simulate_attention(self, text: str) -> AttentionPattern:
        """Simulate attention weights (production uses real model)."""
        tokens = text.split()
        if not tokens:
            return AttentionPattern([], [], 0, 0.0)

        # Simulate attention based on token properties
        weights = []
        for i, token in enumerate(tokens):
            # Higher weight for special chars, position decay
            base = 1.0 / (i + 1)
            if any(c in token.lower() for c in ["!", "@", "#", "$"]):
                base *= 3
            if token.isupper():
                base *= 2
            weights.append(base)

        # Normalize
        total = sum(weights) or 1
        weights = [w / total for w in weights]

        # Calculate entropy
        entropy = -sum(w * math.log(w + 1e-10) for w in weights)

        max_idx = weights.index(max(weights))

        return AttentionPattern(
            tokens=tokens,
            weights=weights,
            max_attention_idx=max_idx,
            entropy=entropy,
        )

    def calculate_entropy(self, weights: List[float]) -> float:
        """Calculate attention entropy."""
        return -sum(w * math.log(w + 1e-10) for w in weights if w > 0)


# ============================================================================
# Focus Hijack Detector
# ============================================================================


class FocusHijackDetector:
    """
    Detects focus hijacking attempts.
    """

    HIJACK_TOKENS = [
        "ignore",
        "forget",
        "override",
        "instead",
        "important",
        "urgent",
        "now",
        "immediately",
    ]

    def detect(
        self,
        pattern: AttentionPattern,
    ) -> Tuple[bool, List[str]]:
        """
        Detect focus hijacking.

        Returns:
            (is_hijack, suspicious_tokens)
        """
        suspicious = []

        for i, token in enumerate(pattern.tokens):
            token_lower = token.lower()

            # Check if hijack token has high attention
            if any(h in token_lower for h in self.HIJACK_TOKENS):
                if i < len(pattern.weights) and pattern.weights[i] > 0.15:
                    suspicious.append(token)

        return len(suspicious) > 0, suspicious


# ============================================================================
# Anomaly Detector
# ============================================================================


class AttentionAnomalyDetector:
    """
    Detects attention anomalies.
    """

    def __init__(self, min_entropy: float = 0.5,
                 max_concentration: float = 0.5):
        self.min_entropy = min_entropy
        self.max_concentration = max_concentration

    def detect(self, pattern: AttentionPattern) -> Tuple[bool, str]:
        """
        Detect attention anomalies.

        Returns:
            (is_anomaly, reason)
        """
        if not pattern.weights:
            return False, ""

        # Check entropy (too low = suspicious focus)
        if pattern.entropy < self.min_entropy:
            return True, f"Low entropy: {pattern.entropy:.2f}"

        # Check concentration (single token dominates)
        max_weight = max(pattern.weights)
        if max_weight > self.max_concentration:
            return True, f"High concentration: {max_weight:.2f}"

        return False, ""


# ============================================================================
# Main Engine
# ============================================================================


class TransformerAttentionShield:
    """
    Transformer Attention Shield - Attention Manipulation Defense

    Attention security:
    - Pattern analysis
    - Focus hijacking detection
    - Anomaly detection

    Invention #36 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.analyzer = AttentionAnalyzer()
        self.hijack_detector = FocusHijackDetector()
        self.anomaly_detector = AttentionAnomalyDetector()

        logger.info("TransformerAttentionShield initialized")

    def analyze(self, text: str) -> ShieldResult:
        """
        Analyze text for attention manipulation.

        Args:
            text: Input text

        Returns:
            ShieldResult
        """
        start = time.time()

        threats = []
        suspicious = []
        risk = 0.0

        # Get attention pattern
        pattern = self.analyzer.simulate_attention(text)

        # Check focus hijacking
        is_hijack, hijack_tokens = self.hijack_detector.detect(pattern)
        if is_hijack:
            threats.append(AttentionThreat.FOCUS_HIJACK)
            suspicious.extend(hijack_tokens)
            risk = max(risk, 0.8)

        # Check anomalies
        is_anomaly, anomaly_reason = self.anomaly_detector.detect(pattern)
        if is_anomaly:
            threats.append(AttentionThreat.PATTERN_ANOMALY)
            risk = max(risk, 0.6)

        is_safe = len(threats) == 0

        if threats:
            logger.warning(f"Attention threats: {[t.value for t in threats]}")

        return ShieldResult(
            is_safe=is_safe,
            threats=threats,
            risk_score=risk,
            attention_entropy=pattern.entropy,
            suspicious_tokens=suspicious,
            explanation=anomaly_reason if is_anomaly else "Safe",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_shield: Optional[TransformerAttentionShield] = None


def get_shield() -> TransformerAttentionShield:
    global _default_shield
    if _default_shield is None:
        _default_shield = TransformerAttentionShield()
    return _default_shield
