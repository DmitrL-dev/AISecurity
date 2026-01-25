"""
Strange Math Engine — Information Theory Module
Uses KL Divergence and entropy analysis for prompt anomaly detection.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import Counter

logger = logging.getLogger("StrangeMath.InfoTheory")


@dataclass
class EntropyResult:
    """Result of entropy analysis."""
    shannon_entropy: float  # Bits
    normalized_entropy: float  # 0-1
    is_anomaly: bool
    anomaly_score: float  # 0-100


@dataclass
class DivergenceResult:
    """Result of KL divergence analysis."""
    kl_divergence: float
    js_divergence: float  # Jensen-Shannon (symmetric)
    cross_entropy: float
    is_anomaly: bool
    anomaly_score: float


class InfoTheoryEngine:
    """
    Information-theoretic analysis of prompts.
    Detects anomalies using entropy and distribution divergence.
    """

    def __init__(self):
        logger.info("Initializing Information Theory Engine...")

        # Reference distribution (learned from normal prompts)
        self.reference_char_dist: Optional[Dict[str, float]] = None
        self.reference_word_dist: Optional[Dict[str, float]] = None

        # Thresholds
        self.entropy_low_threshold = 2.0  # Below = suspicious (too uniform)
        self.entropy_high_threshold = 5.0  # Above = suspicious (too random)
        self.kl_threshold = 2.0  # KL divergence threshold

        # Initialize with default English distribution
        self._init_reference_distribution()

        logger.info("Info Theory Engine initialized")

    def _init_reference_distribution(self):
        """Initialize with typical English character distribution."""
        # English letter frequencies (approximate)
        self.reference_char_dist = {
            ' ': 0.18, 'e': 0.11, 't': 0.09, 'a': 0.08, 'o': 0.07,
            'i': 0.07, 'n': 0.07, 's': 0.06, 'h': 0.06, 'r': 0.05,
            'l': 0.04, 'd': 0.04, 'c': 0.03, 'u': 0.03, 'm': 0.02,
            'w': 0.02, 'f': 0.02, 'g': 0.02, 'y': 0.02, 'p': 0.02,
            'b': 0.01, 'v': 0.01, 'k': 0.01, 'j': 0.001, 'x': 0.001,
            'q': 0.001, 'z': 0.001,
        }

    def calculate_entropy(self, text: str) -> EntropyResult:
        """
        Calculate Shannon entropy of text.
        Low entropy = uniform/repetitive, High entropy = random/noisy.
        """
        if not text:
            return EntropyResult(0, 0, False, 0)

        # Character frequency
        freq = Counter(text.lower())
        total = len(text)

        # Shannon entropy: H(X) = -Σ p(x) * log2(p(x))
        entropy = 0.0
        for count in freq.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        # Maximum possible entropy for this alphabet size
        max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1
        normalized = entropy / max_entropy if max_entropy > 0 else 0

        # Anomaly detection
        is_anomaly = (entropy < self.entropy_low_threshold or
                      entropy > self.entropy_high_threshold)

        # Anomaly score (distance from normal range)
        if entropy < self.entropy_low_threshold:
            anomaly_score = (self.entropy_low_threshold - entropy) * 25
        elif entropy > self.entropy_high_threshold:
            anomaly_score = (entropy - self.entropy_high_threshold) * 15
        else:
            anomaly_score = 0

        anomaly_score = min(anomaly_score, 100)

        return EntropyResult(
            shannon_entropy=entropy,
            normalized_entropy=normalized,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
        )

    def calculate_kl_divergence(
        self,
        text: str,
        reference: Optional[Dict[str, float]] = None
    ) -> DivergenceResult:
        """
        Calculate KL divergence between text distribution and reference.
        High divergence = text is unusual compared to reference.

        KL(P||Q) = Σ P(x) * log(P(x) / Q(x))
        """
        if not text:
            return DivergenceResult(0, 0, 0, False, 0)

        reference = reference or self.reference_char_dist

        # Calculate observed distribution
        text_lower = text.lower()
        freq = Counter(text_lower)
        total = len(text_lower)

        observed = {char: count / total for char, count in freq.items()}

        # Smooth distributions (avoid log(0))
        epsilon = 1e-10

        # Calculate KL divergence
        kl_divergence = 0.0
        cross_entropy = 0.0

        for char, p in observed.items():
            q = reference.get(char, epsilon)
            if p > 0:
                kl_divergence += p * math.log2(p / q)
                cross_entropy -= p * math.log2(q)

        # Jensen-Shannon divergence (symmetric)
        # JS(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M), where M = (P+Q)/2
        m = {}
        all_chars = set(observed.keys()) | set(reference.keys())
        for char in all_chars:
            m[char] = (observed.get(char, 0) +
                       reference.get(char, epsilon)) / 2

        js_divergence = 0.0
        for char in all_chars:
            p = observed.get(char, epsilon)
            q = reference.get(char, epsilon)
            m_val = m[char]
            if p > 0 and m_val > 0:
                js_divergence += 0.5 * p * math.log2(p / m_val)
            if q > 0 and m_val > 0:
                js_divergence += 0.5 * q * math.log2(q / m_val)

        # Anomaly detection
        is_anomaly = kl_divergence > self.kl_threshold
        anomaly_score = min(kl_divergence * 30, 100)

        return DivergenceResult(
            kl_divergence=kl_divergence,
            js_divergence=js_divergence,
            cross_entropy=cross_entropy,
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
        )

    def analyze_prompt(self, text: str) -> Dict:
        """
        Full information-theoretic analysis of prompt.
        """
        entropy_result = self.calculate_entropy(text)
        divergence_result = self.calculate_kl_divergence(text)

        # Combined anomaly score
        combined_score = (entropy_result.anomaly_score +
                          divergence_result.anomaly_score) / 2

        # Word-level analysis
        words = text.split()
        word_lengths = [len(w) for w in words]

        word_stats = {
            "count": len(words),
            "avg_length": sum(word_lengths) / len(word_lengths) if words else 0,
            "max_length": max(word_lengths) if words else 0,
            "unique_ratio": len(set(words)) / len(words) if words else 0,
        }

        # Detect specific patterns
        patterns = self._detect_patterns(text)

        logger.info(
            f"Info analysis: entropy={entropy_result.shannon_entropy:.2f}, "
            f"kl={divergence_result.kl_divergence:.2f}, score={combined_score:.1f}"
        )

        return {
            "entropy": {
                "shannon": entropy_result.shannon_entropy,
                "normalized": entropy_result.normalized_entropy,
                "is_anomaly": entropy_result.is_anomaly,
            },
            "divergence": {
                "kl": divergence_result.kl_divergence,
                "js": divergence_result.js_divergence,
                "is_anomaly": divergence_result.is_anomaly,
            },
            "word_stats": word_stats,
            "patterns": patterns,
            "combined_anomaly_score": combined_score,
            "is_anomaly": combined_score > 50,
        }

    def _detect_patterns(self, text: str) -> List[str]:
        """Detect suspicious patterns using info theory."""
        patterns = []

        # Repetition detection (low entropy in windows)
        window_size = 50
        for i in range(0, len(text) - window_size, window_size):
            window = text[i:i + window_size]
            entropy = self.calculate_entropy(window)
            if entropy.shannon_entropy < 1.5:
                patterns.append(f"low_entropy_window_at_{i}")

        # Character sequence analysis
        if len(set(text)) < 10 and len(text) > 50:
            patterns.append("limited_alphabet")

        # Check for encoding patterns (base64, hex, etc.)
        text_lower = text.lower()
        if all(c in '0123456789abcdef ' for c in text_lower) and len(text) > 20:
            patterns.append("possible_hex_encoding")

        import re
        if re.match(r'^[A-Za-z0-9+/=\s]+$', text) and len(text) > 50:
            patterns.append("possible_base64")

        return patterns

    def update_reference(self, normal_prompts: List[str]):
        """Update reference distribution from normal prompts."""
        all_text = " ".join(normal_prompts).lower()
        freq = Counter(all_text)
        total = len(all_text)

        self.reference_char_dist = {
            char: count / total for char, count in freq.items()
        }

        logger.info(
            f"Updated reference distribution from {len(normal_prompts)} prompts")


# Singleton
_info_engine = None


def get_info_theory_engine() -> InfoTheoryEngine:
    global _info_engine
    if _info_engine is None:
        _info_engine = InfoTheoryEngine()
    return _info_engine
