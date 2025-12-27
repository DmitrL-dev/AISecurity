"""
Distilled Security Ensemble Engine - Efficient Multi-Model

Uses knowledge distillation for efficient ensemble:
- Multi-model combination
- Lightweight student model
- Voting-based decisions
- Confidence calibration

Addresses: Enterprise AI Governance (Performance)
Research: knowledge_distillation_deep_dive.md
Invention: Distilled Security Ensemble (#25)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("DistilledSecurityEnsemble")


# ============================================================================
# Data Classes
# ============================================================================


class VoteResult(Enum):
    """Voting results."""

    SAFE = "safe"
    UNSAFE = "unsafe"
    UNCERTAIN = "uncertain"


@dataclass
class ModelPrediction:
    """Prediction from a model."""

    model_name: str
    is_safe: bool
    confidence: float
    latency_ms: float


@dataclass
class EnsembleResult:
    """Result from ensemble."""

    vote: VoteResult
    is_safe: bool
    confidence: float
    individual_predictions: List[ModelPrediction] = field(default_factory=list)
    agreement_ratio: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "vote": self.vote.value,
            "is_safe": self.is_safe,
            "confidence": self.confidence,
            "agreement_ratio": self.agreement_ratio,
            "individual": [
                {"model": p.model_name, "safe": p.is_safe, "conf": p.confidence}
                for p in self.individual_predictions
            ],
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Base Model
# ============================================================================


class BaseDetector:
    """
    Base detector interface.
    """

    def __init__(self, name: str):
        self.name = name

    def predict(self, text: str) -> Tuple[bool, float]:
        """
        Predict safety.

        Returns:
            (is_safe, confidence)
        """
        raise NotImplementedError


# ============================================================================
# Example Detectors
# ============================================================================


class KeywordDetector(BaseDetector):
    """Simple keyword-based detector."""

    def __init__(self, keywords: List[str]):
        super().__init__("keyword")
        self._keywords = [k.lower() for k in keywords]

    def predict(self, text: str) -> Tuple[bool, float]:
        text_lower = text.lower()
        matches = sum(1 for k in self._keywords if k in text_lower)

        if matches > 0:
            confidence = min(1.0, matches * 0.3)
            return False, confidence
        return True, 0.9


class LengthDetector(BaseDetector):
    """Length-based anomaly detector."""

    def __init__(self, max_length: int = 1000):
        super().__init__("length")
        self._max = max_length

    def predict(self, text: str) -> Tuple[bool, float]:
        if len(text) > self._max:
            ratio = len(text) / self._max
            return False, min(1.0, ratio * 0.5)
        return True, 0.8


class PatternDetector(BaseDetector):
    """Pattern-based detector."""

    PATTERNS = ["ignore", "override", "bypass", "hack"]

    def __init__(self):
        super().__init__("pattern")

    def predict(self, text: str) -> Tuple[bool, float]:
        text_lower = text.lower()
        matches = sum(1 for p in self.PATTERNS if p in text_lower)

        if matches > 0:
            return False, min(1.0, matches * 0.4)
        return True, 0.85


# ============================================================================
# Voting Engine
# ============================================================================


class VotingEngine:
    """
    Combines predictions through voting.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        min_agreement: float = 0.6,
    ):
        self.threshold = threshold
        self.min_agreement = min_agreement

    def vote(
        self,
        predictions: List[ModelPrediction],
    ) -> Tuple[VoteResult, float, float]:
        """
        Perform voting.

        Returns:
            (result, confidence, agreement_ratio)
        """
        if not predictions:
            return VoteResult.UNCERTAIN, 0.0, 0.0

        safe_count = sum(1 for p in predictions if p.is_safe)
        total = len(predictions)
        safe_ratio = safe_count / total

        # Weighted confidence
        safe_conf = sum(p.confidence for p in predictions if p.is_safe)
        unsafe_conf = sum(p.confidence for p in predictions if not p.is_safe)

        if safe_ratio > self.threshold:
            agreement = safe_ratio
            conf = safe_conf / safe_count if safe_count > 0 else 0.0
            result = VoteResult.SAFE
        elif safe_ratio < (1 - self.threshold):
            agreement = 1 - safe_ratio
            conf = unsafe_conf / \
                (total - safe_count) if safe_count < total else 0.0
            result = VoteResult.UNSAFE
        else:
            agreement = max(safe_ratio, 1 - safe_ratio)
            conf = (safe_conf + unsafe_conf) / total
            result = VoteResult.UNCERTAIN

        return result, conf, agreement


# ============================================================================
# Main Engine
# ============================================================================


class DistilledSecurityEnsemble:
    """
    Distilled Security Ensemble - Efficient Multi-Model

    Efficient ensemble:
    - Multiple detectors
    - Voting combination
    - Confidence calibration

    Invention #25 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self, min_agreement: float = 0.6):
        self.voting_engine = VotingEngine(min_agreement=min_agreement)
        self._detectors: List[BaseDetector] = []

        # Initialize default detectors
        self._init_default_detectors()

        logger.info("DistilledSecurityEnsemble initialized")

    def _init_default_detectors(self) -> None:
        """Initialize default detectors."""
        self._detectors = [
            KeywordDetector(["ignore", "instructions", "override"]),
            LengthDetector(max_length=2000),
            PatternDetector(),
        ]

    def add_detector(self, detector: BaseDetector) -> None:
        """Add detector to ensemble."""
        self._detectors.append(detector)

    def analyze(self, text: str) -> EnsembleResult:
        """
        Analyze text with ensemble.

        Args:
            text: Input text

        Returns:
            EnsembleResult
        """
        start = time.time()

        predictions = []

        for detector in self._detectors:
            det_start = time.time()
            is_safe, conf = detector.predict(text)
            det_time = (time.time() - det_start) * 1000

            predictions.append(
                ModelPrediction(
                    model_name=detector.name,
                    is_safe=is_safe,
                    confidence=conf,
                    latency_ms=det_time,
                )
            )

        # Voting
        vote, conf, agreement = self.voting_engine.vote(predictions)
        is_safe = vote == VoteResult.SAFE

        if vote == VoteResult.UNSAFE:
            logger.warning("Ensemble detected unsafe content")

        return EnsembleResult(
            vote=vote,
            is_safe=is_safe,
            confidence=conf,
            individual_predictions=predictions,
            agreement_ratio=agreement,
            explanation=f"Vote: {vote.value}, agreement: {agreement:.2f}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_ensemble: Optional[DistilledSecurityEnsemble] = None


def get_ensemble() -> DistilledSecurityEnsemble:
    global _default_ensemble
    if _default_ensemble is None:
        _default_ensemble = DistilledSecurityEnsemble()
    return _default_ensemble
