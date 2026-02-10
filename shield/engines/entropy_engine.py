"""
SENTINEL Shield v2.0 — Entropy Detection Engine

Detects suspicious payloads using:
1. Shannon entropy (high entropy = possible encoded/encrypted data)
2. Compression ratio (incompressible = random/encrypted)
3. Character distribution analysis (uniform dist = suspicious)
"""

import math
import zlib
import logging
from collections import Counter
from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.engines.entropy")


class EntropyEngine(BaseEngine):
    """
    Entropy-based anomaly detection.

    High entropy in user input is suspicious — normal text has
    entropy ~3.5-4.5 bits/char (English), encoded attacks have 5.5+.
    """

    def __init__(
        self,
        weight: float = 0.7,
        entropy_threshold: float = 5.5,
        compression_ratio_threshold: float = 0.85,
        min_text_length: int = 20,
    ):
        super().__init__(name="entropy", weight=weight)
        self.entropy_threshold = entropy_threshold
        self.compression_ratio_threshold = compression_ratio_threshold
        self.min_text_length = min_text_length

    def _shannon_entropy(self, text: str) -> float:
        """Calculate Shannon entropy in bits per character."""
        if not text:
            return 0.0
        freq = Counter(text)
        length = len(text)
        entropy = -sum(
            (count / length) * math.log2(count / length) for count in freq.values()
        )
        return entropy

    def _compression_ratio(self, text: str) -> float:
        """
        Calculate compression ratio.
        Low ratio = compressible (normal text)
        High ratio = incompressible (random/encrypted)
        """
        if not text:
            return 0.0
        original = text.encode("utf-8")
        compressed = zlib.compress(original, 9)
        return len(compressed) / len(original)

    def _char_class_analysis(self, text: str) -> dict:
        """Analyze character class distribution."""
        total = len(text) or 1
        alpha = sum(1 for c in text if c.isalpha())
        digit = sum(1 for c in text if c.isdigit())
        space = sum(1 for c in text if c.isspace())
        special = total - alpha - digit - space
        non_ascii = sum(1 for c in text if ord(c) > 127)

        return {
            "alpha_ratio": alpha / total,
            "digit_ratio": digit / total,
            "space_ratio": space / total,
            "special_ratio": special / total,
            "non_ascii_ratio": non_ascii / total,
        }

    def analyze(self, text: str) -> EngineResult:
        threats: list[ThreatMatch] = []
        max_risk = 0.0

        if len(text) < self.min_text_length:
            return EngineResult(engine_name=self.name, risk_score=0.0)

        # 1. Shannon entropy
        entropy = self._shannon_entropy(text)
        if entropy > self.entropy_threshold:
            risk = min((entropy - self.entropy_threshold) / 2.5, 1.0) * 0.7
            threats.append(
                ThreatMatch(
                    threat_type="high_entropy",
                    risk_score=risk,
                    engine=self.name,
                    description=f"Shannon entropy {entropy:.2f} bits/char exceeds threshold {self.entropy_threshold}",
                    metadata={"entropy": round(entropy, 3)},
                )
            )
            max_risk = max(max_risk, risk)

        # 2. Compression ratio
        comp_ratio = self._compression_ratio(text)
        if comp_ratio > self.compression_ratio_threshold:
            risk = (
                min((comp_ratio - self.compression_ratio_threshold) / 0.15, 1.0) * 0.6
            )
            threats.append(
                ThreatMatch(
                    threat_type="incompressible_payload",
                    risk_score=risk,
                    engine=self.name,
                    description=f"Compression ratio {comp_ratio:.2f} suggests encoded/random data",
                    metadata={"compression_ratio": round(comp_ratio, 3)},
                )
            )
            max_risk = max(max_risk, risk)

        # 3. Character distribution anomalies
        chars = self._char_class_analysis(text)

        # Suspiciously low alpha ratio with high special chars
        if chars["alpha_ratio"] < 0.3 and chars["special_ratio"] > 0.3:
            risk = 0.5
            threats.append(
                ThreatMatch(
                    threat_type="abnormal_char_distribution",
                    risk_score=risk,
                    engine=self.name,
                    description="Low alphabetic / high special character ratio",
                    metadata=chars,
                )
            )
            max_risk = max(max_risk, risk)

        # High non-ASCII ratio (potential unicode obfuscation)
        if chars["non_ascii_ratio"] > 0.3:
            risk = 0.6
            threats.append(
                ThreatMatch(
                    threat_type="unicode_obfuscation",
                    risk_score=risk,
                    engine=self.name,
                    description=f"Non-ASCII ratio {chars['non_ascii_ratio']:.0%} suggests unicode obfuscation",
                    metadata=chars,
                )
            )
            max_risk = max(max_risk, risk)

        return EngineResult(
            engine_name=self.name,
            risk_score=max_risk,
            threats=threats,
        )
