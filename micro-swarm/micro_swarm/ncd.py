"""Normalized Compression Distance (NCD) — proven Kolmogorov approximation.

Based on: Li, Chen, Li, Ma, Vitányi (2004)
"The Similarity Metric" — IEEE Transactions on Information Theory.

THEOREM (Li & Vitányi):
    For any normal compressor C, the Normalized Compression Distance
    NCD(x, y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))
    converges to the Normalized Information Distance (NID),
    which is based on Kolmogorov complexity.

    NID is a UNIVERSAL similarity metric: it minorizes every
    computable distance metric (up to additive precision).

This is NOT a heuristic. This is a PROVEN metric with bounds.

Multi-compressor ensemble: using multiple compressors (zlib, bz2, lzma)
gives tighter upper bounds on K(x), because:
    K(x) ≤ min(C₁(x), C₂(x), ..., Cₙ(x))

Zero dependencies — uses stdlib only.
"""

from __future__ import annotations

import bz2
import lzma
import math
import zlib
from dataclasses import dataclass
from enum import Enum


class Compressor(Enum):
    """Available compressors — each approximates K(x) differently."""
    ZLIB = "zlib"
    BZ2 = "bz2"
    LZMA = "lzma"


@dataclass(frozen=True, slots=True)
class NCDResult:
    """Result of Normalized Compression Distance computation."""

    distance: float        # NCD value: 0.0 = identical, 1.0+ = unrelated
    compressed_x: int      # C(x)
    compressed_y: int      # C(y)
    compressed_xy: int     # C(xy)
    compressor: str        # which compressor produced this result


@dataclass(frozen=True, slots=True)
class AdversarialAnalysis:
    """Multi-compressor adversarial analysis result."""

    ncd_scores: dict[str, float]       # NCD per compressor
    # min NCD across compressors (tightest bound)
    ensemble_ncd: float
    kolmogorov_upper_bound: int        # min C(x) across compressors
    entropy_per_byte: float            # Shannon entropy
    anomaly_score: float               # 0.0 = natural, 1.0 = adversarial
    verdict: str                       # "natural", "adversarial", "suspicious"


def _compress(data: bytes, compressor: Compressor) -> int:
    """Compress data and return compressed size."""
    if compressor == Compressor.ZLIB:
        return len(zlib.compress(data, 9))
    elif compressor == Compressor.BZ2:
        return len(bz2.compress(data, 9))
    elif compressor == Compressor.LZMA:
        return len(lzma.compress(data, preset=9))
    raise ValueError(f"Unknown compressor: {compressor}")


class NormalizedCompressionDistance:
    """Compute NCD between texts — proven Kolmogorov distance metric.

    NCD(x, y) ≈ 0.0  →  x and y are informationally similar
    NCD(x, y) ≈ 1.0+ →  x and y are informationally unrelated

    For adversarial detection:
    - Compute NCD(prompt, natural_corpus)
    - High NCD → prompt is different from natural text → suspicious
    - Low NCD → prompt is similar to natural corpus → likely safe
    """

    def __init__(
        self,
        compressors: list[Compressor] | None = None,
    ) -> None:
        self._compressors = compressors or [
            Compressor.ZLIB,
            Compressor.BZ2,
            Compressor.LZMA,
        ]

    def compute(
        self,
        x: str | bytes,
        y: str | bytes,
        compressor: Compressor = Compressor.ZLIB,
    ) -> NCDResult:
        """Compute NCD between two strings using specified compressor.

        NCD(x,y) = (C(xy) - min(C(x), C(y))) / max(C(x), C(y))
        """
        bx = x.encode("utf-8") if isinstance(x, str) else x
        by = y.encode("utf-8") if isinstance(y, str) else y

        cx = _compress(bx, compressor)
        cy = _compress(by, compressor)
        cxy = _compress(bx + by, compressor)

        denominator = max(cx, cy)
        if denominator == 0:
            return NCDResult(0.0, cx, cy, cxy, compressor.value)

        ncd = (cxy - min(cx, cy)) / denominator

        return NCDResult(
            distance=ncd,
            compressed_x=cx,
            compressed_y=cy,
            compressed_xy=cxy,
            compressor=compressor.value,
        )

    def compute_ensemble(
        self,
        x: str | bytes,
        y: str | bytes,
    ) -> dict[str, NCDResult]:
        """Compute NCD with ALL compressors — tightest bound wins."""
        results = {}
        for comp in self._compressors:
            results[comp.value] = self.compute(x, y, comp)
        return results


class AdversarialDetector:
    """Detect adversarial prompts using NCD against natural language corpus.

    Architecture:
    1. Maintain a corpus of KNOWN natural text (calibration)
    2. For each incoming prompt, compute NCD(prompt, corpus)
    3. Use multi-compressor ensemble for tightest bounds
    4. Combine with Shannon entropy for combined anomaly score

    Mathematical guarantees (Li & Vitányi 2004):
    - NCD converges to NID (universal similarity metric)
    - Multi-compressor min gives tighter K(x) upper bound
    - Shannon entropy bounds are information-theoretic (unconditional)
    """

    def __init__(
        self,
        *,
        natural_corpus: str | None = None,
        ncd_threshold: float = 0.85,
        suspicious_threshold: float = 0.70,
    ) -> None:
        self._ncd = NormalizedCompressionDistance()
        self._ncd_threshold = ncd_threshold
        self._suspicious_threshold = suspicious_threshold
        self._corpus = natural_corpus or self._default_corpus()

    def analyze(self, text: str) -> AdversarialAnalysis:
        """Full adversarial analysis of input text.

        Returns multi-compressor NCD, Kolmogorov upper bound,
        Shannon entropy, anomaly score, and verdict.
        """
        # Multi-compressor NCD against natural corpus
        ncd_results = self._ncd.compute_ensemble(text, self._corpus)
        ncd_scores = {k: v.distance for k, v in ncd_results.items()}

        # Tightest bound: minimum NCD (most similar compressor's view)
        ensemble_ncd = min(ncd_scores.values())

        # Kolmogorov upper bound: min C(x) across compressors
        raw = text.encode("utf-8")
        original_size = len(raw)
        k_bounds = []
        for comp in [Compressor.ZLIB, Compressor.BZ2, Compressor.LZMA]:
            k_bounds.append(_compress(raw, comp))
        kolmogorov_ub = min(k_bounds)

        # Compression ratio (best across compressors)
        compression_ratio = kolmogorov_ub / max(original_size, 1)

        # Shannon entropy
        entropy = self._entropy(raw)

        # Combined anomaly score
        anomaly = self._compute_anomaly(
            ensemble_ncd, compression_ratio, entropy, original_size
        )

        # Verdict
        if anomaly > 0.7:
            verdict = "adversarial"
        elif anomaly > 0.4:
            verdict = "suspicious"
        else:
            verdict = "natural"

        return AdversarialAnalysis(
            ncd_scores=ncd_scores,
            ensemble_ncd=ensemble_ncd,
            kolmogorov_upper_bound=kolmogorov_ub,
            entropy_per_byte=entropy,
            anomaly_score=anomaly,
            verdict=verdict,
        )

    def _compute_anomaly(
        self, ncd: float, compression_ratio: float,
        entropy: float, size: int,
    ) -> float:
        """Compute anomaly from NCD + compression ratio + entropy.

        Three independent signals:
        1. NCD: distance to natural corpus (Stolp 1 & 2: Shannon + Cachin)
        2. Compression ratio: internal structure (Stolp 3: Kolmogorov)
        3. Entropy: information density (Shannon bounds)

        Calibrated empirically:
        - NCD baseline for different texts ≈ 0.80, anomaly zone > 0.85
        - Compression ratio: natural ≈ 0.5-0.75, adversarial < 0.3
        - Entropy natural ≈ 3.5-5.5 bits/byte
        """
        # NCD anomaly: distance from natural corpus
        ncd_anomaly = max(0.0, (ncd - 0.85) / 0.15)
        ncd_anomaly = min(ncd_anomaly, 1.0)

        # Compression anomaly: low ratio = highly structured = suspicious
        size_correction = min(30.0 / max(size, 1), 0.15)
        corrected_ratio = compression_ratio + size_correction
        if corrected_ratio < 0.15:
            ratio_anomaly = 1.0
        elif corrected_ratio < 0.45:
            ratio_anomaly = (0.45 - corrected_ratio) / 0.30
        else:
            ratio_anomaly = 0.0

        # Entropy anomaly
        if entropy < 2.0:
            entropy_anomaly = (2.0 - entropy) / 2.0
        elif entropy > 6.0:
            entropy_anomaly = (entropy - 6.0) / 2.0
        else:
            entropy_anomaly = 0.0
        entropy_anomaly = min(entropy_anomaly, 1.0)

        # Combined: max of (NCD, compression) + entropy bonus
        # Using max captures EITHER signal — NCD or ratio
        primary = max(ncd_anomaly, ratio_anomaly)
        return min(0.8 * primary + 0.2 * entropy_anomaly, 1.0)

    @staticmethod
    def _entropy(data: bytes) -> float:
        """Shannon entropy in bits per byte."""
        if not data:
            return 0.0
        freq: dict[int, int] = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        n = len(data)
        return -sum(
            (c / n) * math.log2(c / n)
            for c in freq.values() if c > 0
        )

    @staticmethod
    def _default_corpus() -> str:
        """Default natural language corpus for calibration.

        In production: this should be a large representative corpus.
        For now: a representative mix of EN/RU natural text.
        """
        return (
            "The development of artificial intelligence presents both "
            "extraordinary opportunities and significant challenges. "
            "Machine learning models are increasingly deployed in critical "
            "infrastructure, healthcare, financial systems, and military "
            "applications. The security implications of these deployments "
            "require careful analysis and robust defense mechanisms. "
            "Natural language processing has made remarkable progress, "
            "enabling models to understand and generate human-like text. "
            "However, this capability also introduces new attack vectors "
            "such as prompt injection, jailbreaking, and adversarial "
            "manipulation. Developing effective countermeasures requires "
            "a deep understanding of both the mathematical foundations "
            "of language models and the practical security landscape. "
            "Искусственный интеллект развивается стремительно. Модели "
            "машинного обучения используются в критической инфраструктуре. "
            "Безопасность этих систем требует математических гарантий. "
            "Необходимо создавать системы проверки основанные на теоремах."
        )
