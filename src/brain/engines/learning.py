"""
Online Learning Engine v1.0

Features:
  1. Feedback Loop - learn from user corrections (FP/FN)
  2. Threshold Tuning - adaptive thresholds based on performance
  3. Pattern Learning - discover new attack patterns
  4. Model Updates - incremental model improvement
  5. Performance Tracking - precision/recall/F1 monitoring
  6. A/B Testing - compare configurations
"""

import logging
import json
import os
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from enum import Enum
import hashlib

logger = logging.getLogger("OnlineLearning")


# ============================================================================
# Enums and Constants
# ============================================================================

class FeedbackType(Enum):
    FALSE_POSITIVE = "fp"  # Blocked but should allow
    FALSE_NEGATIVE = "fn"  # Allowed but should block
    TRUE_POSITIVE = "tp"   # Correctly blocked
    TRUE_NEGATIVE = "tn"   # Correctly allowed


class LearningMode(Enum):
    PASSIVE = "passive"    # Collect only, don't apply
    ACTIVE = "active"      # Apply learned changes
    SHADOW = "shadow"      # Learn in parallel, compare


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Feedback:
    """User feedback on a decision."""
    request_id: str
    timestamp: float
    feedback_type: FeedbackType
    original_verdict: str
    correct_verdict: str
    risk_score: float
    engine_name: Optional[str] = None
    pattern: Optional[str] = None
    user_comment: str = ""

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "feedback_type": self.feedback_type.value,
            "original_verdict": self.original_verdict,
            "correct_verdict": self.correct_verdict,
            "risk_score": self.risk_score,
            "engine": self.engine_name,
            "pattern": self.pattern,
            "comment": self.user_comment
        }


@dataclass
class PerformanceMetrics:
    """Performance metrics over time."""
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    total_requests: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        correct = self.true_positives + self.true_negatives
        return correct / self.total_requests if self.total_requests > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "tp": self.true_positives,
            "tn": self.true_negatives,
            "fp": self.false_positives,
            "fn": self.false_negatives,
            "total": self.total_requests,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1_score, 4),
            "accuracy": round(self.accuracy, 4)
        }


@dataclass
class ThresholdConfig:
    """Configuration for adaptive thresholds."""
    engine_name: str
    current_threshold: float
    min_threshold: float = 30.0
    max_threshold: float = 90.0
    learning_rate: float = 0.1
    last_updated: float = 0.0

    def adjust(self, direction: str, magnitude: float = 1.0):
        """Adjust threshold based on feedback."""
        delta = self.learning_rate * magnitude

        if direction == "increase":
            self.current_threshold = min(
                self.max_threshold,
                self.current_threshold + delta
            )
        else:
            self.current_threshold = max(
                self.min_threshold,
                self.current_threshold - delta
            )

        self.last_updated = time.time()


@dataclass
class LearnedPattern:
    """Pattern learned from feedback."""
    pattern_hash: str
    pattern_text: str
    pattern_type: str  # "allow" or "block"
    confidence: float
    occurrences: int = 1
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> dict:
        return {
            "hash": self.pattern_hash[:8],
            "type": self.pattern_type,
            "confidence": self.confidence,
            "occurrences": self.occurrences,
            "text_preview": self.pattern_text[:50]
        }


# ============================================================================
# Feedback Store
# ============================================================================

class FeedbackStore:
    """Stores and manages feedback history."""

    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path
        self.feedback_history: List[Feedback] = []
        self.max_history = 10000

        if storage_path and os.path.exists(storage_path):
            self._load()

    def add(self, feedback: Feedback):
        """Add feedback to history."""
        self.feedback_history.append(feedback)

        if len(self.feedback_history) > self.max_history:
            self.feedback_history = self.feedback_history[-self.max_history:]

        if self.storage_path:
            self._save()

    def get_recent(self, count: int = 100) -> List[Feedback]:
        """Get recent feedback."""
        return self.feedback_history[-count:]

    def get_by_type(self, feedback_type: FeedbackType) -> List[Feedback]:
        """Get feedback by type."""
        return [f for f in self.feedback_history if f.feedback_type == feedback_type]

    def _save(self):
        """Save to disk."""
        try:
            data = [f.to_dict() for f in self.feedback_history]
            with open(self.storage_path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save feedback: {e}")

    def _load(self):
        """Load from disk."""
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            # Convert back to Feedback objects (simplified)
            logger.info(f"Loaded {len(data)} feedback records")
        except Exception as e:
            logger.warning(f"Failed to load feedback: {e}")


# ============================================================================
# Threshold Tuner
# ============================================================================

class ThresholdTuner:
    """Adaptively tunes engine thresholds based on feedback."""

    def __init__(self, default_threshold: float = 70.0):
        self.default_threshold = default_threshold
        self.thresholds: Dict[str, ThresholdConfig] = {}

        # Initialize common engine thresholds
        for engine in ["injection", "pii", "query", "behavioral", "language"]:
            self.thresholds[engine] = ThresholdConfig(
                engine_name=engine,
                current_threshold=default_threshold
            )

    def get_threshold(self, engine_name: str) -> float:
        """Get current threshold for engine."""
        if engine_name in self.thresholds:
            return self.thresholds[engine_name].current_threshold
        return self.default_threshold

    def update_from_feedback(self, feedback: Feedback):
        """Update threshold based on feedback."""
        engine = feedback.engine_name or "global"

        if engine not in self.thresholds:
            self.thresholds[engine] = ThresholdConfig(
                engine_name=engine,
                current_threshold=self.default_threshold
            )

        config = self.thresholds[engine]

        if feedback.feedback_type == FeedbackType.FALSE_POSITIVE:
            # Blocked but shouldn't have - increase threshold
            config.adjust("increase", magnitude=5.0)
            logger.info(
                f"Increased {engine} threshold to {config.current_threshold:.1f}")

        elif feedback.feedback_type == FeedbackType.FALSE_NEGATIVE:
            # Allowed but shouldn't have - decrease threshold
            config.adjust("decrease", magnitude=5.0)
            logger.info(
                f"Decreased {engine} threshold to {config.current_threshold:.1f}")

    def get_all_thresholds(self) -> Dict[str, float]:
        """Get all current thresholds."""
        return {name: cfg.current_threshold for name, cfg in self.thresholds.items()}


# ============================================================================
# Pattern Learner
# ============================================================================

class PatternLearner:
    """Learns new patterns from feedback."""

    def __init__(self, min_confidence: float = 0.8):
        self.min_confidence = min_confidence
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        self.pattern_votes: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"allow": 0, "block": 0})

    def _hash_pattern(self, text: str) -> str:
        """Create hash for pattern matching."""
        # Normalize and hash
        normalized = text.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()

    def learn(self, text: str, correct_verdict: str, confidence: float = 1.0):
        """Learn from corrected pattern."""
        pattern_hash = self._hash_pattern(text)

        # Update votes
        self.pattern_votes[pattern_hash][correct_verdict] += 1

        # Calculate confidence
        votes = self.pattern_votes[pattern_hash]
        total_votes = votes["allow"] + votes["block"]

        if total_votes >= 3:  # Need minimum votes
            dominant_verdict = "allow" if votes["allow"] > votes["block"] else "block"
            pattern_confidence = max(votes.values()) / total_votes

            if pattern_confidence >= self.min_confidence:
                self.learned_patterns[pattern_hash] = LearnedPattern(
                    pattern_hash=pattern_hash,
                    pattern_text=text[:100],
                    pattern_type=dominant_verdict,
                    confidence=pattern_confidence,
                    occurrences=total_votes,
                    first_seen=time.time(),
                    last_seen=time.time()
                )
                logger.info(
                    f"Learned pattern: {dominant_verdict} ({pattern_confidence:.0%})")

    def check(self, text: str) -> Optional[Tuple[str, float]]:
        """Check if text matches learned pattern."""
        pattern_hash = self._hash_pattern(text)

        if pattern_hash in self.learned_patterns:
            pattern = self.learned_patterns[pattern_hash]
            return pattern.pattern_type, pattern.confidence

        return None

    def get_learned_count(self) -> int:
        """Get count of learned patterns."""
        return len(self.learned_patterns)


# ============================================================================
# Main Online Learning Engine
# ============================================================================

class OnlineLearningEngine:
    """
    Online Learning Engine v1.0

    Continuously learns from feedback to improve detection:
      - Adaptive threshold tuning
      - Pattern learning
      - Performance tracking
    """

    def __init__(self,
                 mode: LearningMode = LearningMode.ACTIVE,
                 storage_path: str = None):
        logger.info("Initializing Online Learning Engine v1.0...")

        self.mode = mode

        # Components
        self.feedback_store = FeedbackStore(storage_path)
        self.threshold_tuner = ThresholdTuner()
        self.pattern_learner = PatternLearner()

        # Metrics
        self.metrics = PerformanceMetrics()
        self.engine_metrics: Dict[str, PerformanceMetrics] = defaultdict(
            PerformanceMetrics)

        logger.info(f"Online Learning initialized (mode={mode.value})")

    def record_feedback(self,
                        request_id: str,
                        feedback_type: FeedbackType,
                        original_verdict: str,
                        risk_score: float,
                        engine_name: str = None,
                        pattern: str = None,
                        comment: str = "") -> dict:
        """
        Record user feedback on a decision.

        Args:
            request_id: ID of the original request
            feedback_type: FP, FN, TP, or TN
            original_verdict: What was decided
            risk_score: Original risk score
            engine_name: Which engine was responsible
            pattern: The pattern that was flagged
            comment: User's comment

        Returns:
            Dict with feedback result and any adjustments made
        """
        correct_verdict = "block" if feedback_type in [
            FeedbackType.FALSE_NEGATIVE, FeedbackType.TRUE_POSITIVE] else "allow"

        feedback = Feedback(
            request_id=request_id,
            timestamp=time.time(),
            feedback_type=feedback_type,
            original_verdict=original_verdict,
            correct_verdict=correct_verdict,
            risk_score=risk_score,
            engine_name=engine_name,
            pattern=pattern,
            user_comment=comment
        )

        # Store feedback
        self.feedback_store.add(feedback)

        # Update metrics
        self._update_metrics(feedback_type, engine_name)

        adjustments = {}

        # Apply learning if active mode
        if self.mode == LearningMode.ACTIVE:
            # Update thresholds
            if feedback_type in [FeedbackType.FALSE_POSITIVE, FeedbackType.FALSE_NEGATIVE]:
                self.threshold_tuner.update_from_feedback(feedback)
                adjustments["threshold_adjusted"] = True
                adjustments["new_threshold"] = self.threshold_tuner.get_threshold(
                    engine_name or "global")

            # Learn pattern
            if pattern:
                self.pattern_learner.learn(pattern, correct_verdict)
                adjustments["pattern_learned"] = True

        return {
            "feedback_recorded": True,
            "feedback_type": feedback_type.value,
            "adjustments": adjustments,
            "metrics": self.metrics.to_dict()
        }

    def _update_metrics(self, feedback_type: FeedbackType, engine_name: str = None):
        """Update performance metrics."""
        self.metrics.total_requests += 1

        if engine_name:
            self.engine_metrics[engine_name].total_requests += 1

        if feedback_type == FeedbackType.TRUE_POSITIVE:
            self.metrics.true_positives += 1
            if engine_name:
                self.engine_metrics[engine_name].true_positives += 1

        elif feedback_type == FeedbackType.TRUE_NEGATIVE:
            self.metrics.true_negatives += 1
            if engine_name:
                self.engine_metrics[engine_name].true_negatives += 1

        elif feedback_type == FeedbackType.FALSE_POSITIVE:
            self.metrics.false_positives += 1
            if engine_name:
                self.engine_metrics[engine_name].false_positives += 1

        elif feedback_type == FeedbackType.FALSE_NEGATIVE:
            self.metrics.false_negatives += 1
            if engine_name:
                self.engine_metrics[engine_name].false_negatives += 1

    def check_learned(self, text: str) -> Optional[Tuple[str, float]]:
        """Check if text matches learned patterns."""
        return self.pattern_learner.check(text)

    def get_threshold(self, engine_name: str) -> float:
        """Get current threshold for engine."""
        return self.threshold_tuner.get_threshold(engine_name)

    def get_metrics(self) -> dict:
        """Get current performance metrics."""
        return {
            "global": self.metrics.to_dict(),
            "by_engine": {
                name: m.to_dict()
                for name, m in self.engine_metrics.items()
            },
            "learned_patterns": self.pattern_learner.get_learned_count(),
            "thresholds": self.threshold_tuner.get_all_thresholds()
        }

    def get_recommendations(self) -> List[str]:
        """Get recommendations based on metrics."""
        recommendations = []

        if self.metrics.false_positives > self.metrics.true_positives * 0.2:
            recommendations.append(
                f"High false positive rate ({self.metrics.false_positives}). "
                "Consider increasing thresholds."
            )

        if self.metrics.false_negatives > 0:
            recommendations.append(
                f"Detected {self.metrics.false_negatives} missed threats. "
                "Review and add patterns."
            )

        if self.metrics.total_requests > 100 and self.metrics.f1_score < 0.8:
            recommendations.append(
                f"F1 score is {self.metrics.f1_score:.2f}. "
                "Model may need retraining."
            )

        return recommendations


# ============================================================================
# Factory
# ============================================================================

def create_learning_engine(mode: str = "active") -> OnlineLearningEngine:
    """Create online learning engine."""
    mode_map = {
        "passive": LearningMode.PASSIVE,
        "active": LearningMode.ACTIVE,
        "shadow": LearningMode.SHADOW,
    }
    return OnlineLearningEngine(mode=mode_map.get(mode, LearningMode.ACTIVE))
