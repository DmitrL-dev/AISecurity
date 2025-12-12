"""
Hallucination Detection Engine
Uses Self-Consistency + Token Confidence scoring to detect hallucinations.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
import torch

logger = logging.getLogger("HallucinationEngine")


@dataclass
class HallucinationResult:
    """Result of hallucination analysis."""
    is_hallucination: bool
    # 0-1, higher = more confident (less hallucination)
    confidence_score: float
    entropy: float  # Token entropy, higher = more uncertain
    low_confidence_spans: List[str]
    risk_score: float  # 0-100 for Sentinel pipeline


class HallucinationEngine:
    """
    Detects hallucinations using:
    1. Token-level confidence (logprob analysis)
    2. Self-consistency (if multiple responses available)
    3. Entropy-based uncertainty estimation
    """

    def __init__(self):
        logger.info("Initializing Hallucination Detection Engine...")

        # Thresholds
        self.entropy_threshold = 2.0  # Bits, above = uncertain
        self.confidence_threshold = 0.3  # Below = low confidence
        self.hallucination_risk_threshold = 0.6

        logger.info("Hallucination Engine initialized.")

    def analyze_logprobs(
        self,
        tokens: List[str],
        logprobs: List[float]
    ) -> HallucinationResult:
        """
        Analyze token logprobs to detect hallucinations.
        Low logprobs indicate the model is uncertain = potential hallucination.

        Args:
            tokens: List of generated tokens
            logprobs: Log probabilities for each token
        """
        if not tokens or not logprobs:
            return HallucinationResult(
                is_hallucination=False,
                confidence_score=1.0,
                entropy=0.0,
                low_confidence_spans=[],
                risk_score=0.0,
            )

        # Convert logprobs to probabilities
        probs = [math.exp(lp) for lp in logprobs]

        # Calculate average confidence
        avg_confidence = sum(probs) / len(probs)

        # Calculate entropy per token
        entropies = []
        for lp in logprobs:
            p = math.exp(lp)
            if p > 0:
                entropy = -p * math.log2(p) if p < 1 else 0
                entropies.append(entropy)

        avg_entropy = sum(entropies) / len(entropies) if entropies else 0

        # Find low-confidence spans
        low_conf_spans = []
        current_span = []

        for i, (token, prob) in enumerate(zip(tokens, probs)):
            if prob < self.confidence_threshold:
                current_span.append(token)
            else:
                if current_span:
                    low_conf_spans.append("".join(current_span))
                    current_span = []

        if current_span:
            low_conf_spans.append("".join(current_span))

        # Calculate hallucination risk
        # High entropy + low confidence = high risk
        risk_factors = [
            avg_entropy / 3.0,  # Normalize entropy to ~0-1
            1.0 - avg_confidence,
            # Ratio of low-conf spans
            len(low_conf_spans) / max(len(tokens) / 10, 1),
        ]

        hallucination_risk = sum(risk_factors) / len(risk_factors)
        is_hallucination = hallucination_risk > self.hallucination_risk_threshold

        # Convert to Sentinel risk score (0-100)
        risk_score = min(hallucination_risk * 100, 100)

        logger.info(
            f"Hallucination analysis: entropy={avg_entropy:.2f}, "
            f"confidence={avg_confidence:.2f}, risk={risk_score:.1f}"
        )

        return HallucinationResult(
            is_hallucination=is_hallucination,
            confidence_score=avg_confidence,
            entropy=avg_entropy,
            low_confidence_spans=low_conf_spans[:5],  # Top 5
            risk_score=risk_score,
        )

    def self_consistency_check(
        self,
        responses: List[str],
        embedder=None
    ) -> Tuple[float, List[str]]:
        """
        Check consistency across multiple responses to same prompt.
        Inconsistent responses indicate hallucination.

        Args:
            responses: List of responses to same prompt
            embedder: Optional sentence transformer for semantic comparison
        """
        if len(responses) < 2:
            return 1.0, []  # Can't check consistency with single response

        inconsistencies = []

        if embedder:
            # Semantic similarity between responses
            embeddings = embedder.encode(responses)

            # Pairwise cosine similarity
            similarities = []
            for i in range(len(responses)):
                for j in range(i + 1, len(responses)):
                    sim = self._cosine_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)

                    if sim < 0.7:  # Low similarity = inconsistent
                        inconsistencies.append(
                            f"Response {i+1} vs {j+1}: {sim:.2f} similarity"
                        )

            consistency_score = sum(similarities) / len(similarities)
        else:
            # Simple word overlap check
            word_sets = [set(r.lower().split()) for r in responses]

            overlaps = []
            for i in range(len(word_sets)):
                for j in range(i + 1, len(word_sets)):
                    intersection = word_sets[i] & word_sets[j]
                    union = word_sets[i] | word_sets[j]
                    jaccard = len(intersection) / len(union) if union else 0
                    overlaps.append(jaccard)

                    if jaccard < 0.3:
                        inconsistencies.append(
                            f"Response {i+1} vs {j+1}: {jaccard:.2f} overlap"
                        )

            consistency_score = sum(overlaps) / \
                len(overlaps) if overlaps else 1.0

        return consistency_score, inconsistencies

    def _cosine_similarity(self, a, b) -> float:
        """Calculate cosine similarity between vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)

    def analyze_response(
        self,
        response: str,
        tokens: Optional[List[str]] = None,
        logprobs: Optional[List[float]] = None,
    ) -> HallucinationResult:
        """
        Full hallucination analysis on response.
        Uses available signals (logprobs if available, heuristics otherwise).
        """
        if tokens and logprobs:
            return self.analyze_logprobs(tokens, logprobs)

        # Heuristic analysis without logprobs
        # Look for hallucination indicators

        indicators = [
            (r"I think", 0.1),
            (r"I believe", 0.1),
            (r"probably", 0.15),
            (r"might be", 0.15),
            (r"I'm not sure", 0.3),
            (r"I don't know", 0.2),
            (r"approximately", 0.1),
            (r"around \d+", 0.1),
        ]

        import re
        uncertainty_score = 0.0

        for pattern, weight in indicators:
            if re.search(pattern, response, re.IGNORECASE):
                uncertainty_score += weight

        # Cap at 1.0
        uncertainty_score = min(uncertainty_score, 1.0)

        # Convert to result
        is_hallucination = uncertainty_score > 0.5
        risk_score = uncertainty_score * 70  # Scale to Sentinel threshold

        return HallucinationResult(
            is_hallucination=is_hallucination,
            confidence_score=1.0 - uncertainty_score,
            entropy=uncertainty_score * 3,  # Pseudo-entropy
            low_confidence_spans=[],
            risk_score=risk_score,
        )


# Singleton
_hallucination_engine = None


def get_hallucination_engine() -> HallucinationEngine:
    global _hallucination_engine
    if _hallucination_engine is None:
        _hallucination_engine = HallucinationEngine()
    return _hallucination_engine
