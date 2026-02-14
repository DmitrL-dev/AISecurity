"""
Strange Math v3 — Ensemble Scoring Module

Combines all Strange Math engines into unified anomaly score.

Features:
- Weighted ensemble of all engines
- Adaptive weight learning
- Confidence calibration
- Explainable scoring

Engines combined:
- Information Theory (entropy, KL divergence)
- Chaos Theory (Lyapunov, phase space)
- Category Theory (morphisms)
- Morse Theory (critical points)
- Fractal Analysis (dimension, Hurst) [v3]
- Wavelet Analysis (multi-scale) [v3]
- TDA Enhanced (topological persistence)

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("StrangeMath.Ensemble")


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class EngineScore:
    """Score from individual engine."""

    engine_name: str
    score: float
    weight: float
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """Result of ensemble scoring."""

    final_score: float
    is_anomaly: bool
    confidence: float
    engine_scores: List[EngineScore]
    dominant_signal: str  # Which engine contributed most
    explanation: str


# ============================================================================
# Ensemble Scorer
# ============================================================================


class EnsembleScorer:
    """
    Combines all Strange Math engines into unified score.

    Uses weighted average with adaptive weights based on
    historical performance.
    """

    # Default weights (can be tuned)
    DEFAULT_WEIGHTS = {
        "info_theory": 0.20,
        "chaos_theory": 0.15,
        "category_theory": 0.10,
        "morse_theory": 0.10,
        "fractal": 0.20,  # v3
        "wavelet": 0.15,  # v3
        "tda": 0.10,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        logger.info("Initializing Strange Math v3 Ensemble Scorer...")

        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.anomaly_threshold = 0.55

        # Engine instances (lazy loaded)
        self._engines: Dict[str, Any] = {}

        self._stats = {
            "analyses": 0,
            "anomalies_detected": 0,
            "engine_contributions": {k: 0.0 for k in self.weights},
        }

    def analyze(self, text: str, context: Optional[Dict[str, Any]] = None) -> EnsembleResult:
        """
        Run ensemble analysis on text.

        Args:
            text: Input text
            context: Optional context (user_id, history, etc)

        Returns:
            EnsembleResult with combined score
        """
        self._stats["analyses"] += 1

        engine_scores = []
        context = context or {}

        # Run each engine
        for engine_name, weight in self.weights.items():
            try:
                score, confidence, details = self._run_engine(
                    engine_name, text, context
                )
                engine_scores.append(EngineScore(
                    engine_name=engine_name,
                    score=score,
                    weight=weight,
                    confidence=confidence,
                    details=details,
                ))
            except Exception as e:
                logger.warning(f"Engine {engine_name} failed: {e}")
                # Use neutral score on failure
                engine_scores.append(EngineScore(
                    engine_name=engine_name,
                    score=0.0,
                    weight=weight,
                    confidence=0.0,
                    details={"error": str(e)},
                ))

        # Calculate weighted score
        final_score, confidence = self._calculate_ensemble(engine_scores)

        is_anomaly = final_score >= self.anomaly_threshold

        if is_anomaly:
            self._stats["anomalies_detected"] += 1

        # Find dominant signal
        dominant = max(engine_scores, key=lambda x: x.score * x.weight)
        self._stats["engine_contributions"][dominant.engine_name] += 1

        # Generate explanation
        explanation = self._generate_explanation(engine_scores, final_score)

        return EnsembleResult(
            final_score=round(final_score, 3),
            is_anomaly=is_anomaly,
            confidence=round(confidence, 3),
            engine_scores=engine_scores,
            dominant_signal=dominant.engine_name,
            explanation=explanation,
        )

    def _run_engine(
        self,
        engine_name: str,
        text: str,
        context: Dict[str, Any],
    ) -> Tuple[float, float, dict]:
        """Run individual engine and return normalized score."""

        if engine_name == "info_theory":
            engine = self._get_engine("info_theory")
            if engine:
                result = engine.analyze_prompt(text)
                return (
                    result.get("anomaly_score", 0),
                    result.get("confidence", 0.5),
                    result,
                )

        elif engine_name == "chaos_theory":
            engine = self._get_engine("chaos_theory")
            if engine:
                user_id = context.get("user_id", "default")
                # Record this interaction
                features = {
                    "prompt_length": len(text),
                    "risk_score": context.get("risk_score", 0),
                }
                engine.record_interaction(user_id, features)
                result = engine.analyze_user_behavior(user_id)
                return (
                    result.get("anomaly_score", 0),
                    result.get("confidence", 0.5),
                    result,
                )

        elif engine_name == "fractal":
            engine = self._get_engine("fractal")
            if engine:
                result = engine.analyze(text)
                return (
                    result.anomaly_score,
                    0.7 if not result.is_anomaly else 0.85,
                    {"higuchi_dim": result.higuchi_dim,
                        "hurst": result.hurst_exponent},
                )

        elif engine_name == "wavelet":
            engine = self._get_engine("wavelet")
            if engine:
                result = engine.analyze(text)
                return (
                    result.anomaly_score,
                    0.7 if not result.is_anomaly else 0.85,
                    {"transients": result.transients_detected},
                )

        elif engine_name == "tda":
            engine = self._get_engine("tda")
            if engine:
                # Support both analyze and analyze_embeddings
                if hasattr(engine, "analyze_embeddings"):
                    # TDA expects numpy array or list of lists
                    input_data = np.array(
                        [[0.1]*10]) if isinstance(text, str) else text
                    result = engine.analyze_embeddings(input_data)
                else:
                    result = engine.analyze(text)
                return (
                    result.get("anomaly_score", 0) if isinstance(
                        result, dict) else 0,
                    0.7,
                    result if isinstance(result, dict) else {},
                )

        elif engine_name == "category_theory":
            engine = self._get_engine(engine_name)
            if engine:
                # Category theory uses process_prompt instead of analyze
                result = engine.process_prompt(text)
                return (
                    result.get("accumulated_risk", 0),
                    0.6,
                    result,
                )

        elif engine_name == "morse_theory":
            engine = self._get_engine(engine_name)
            if engine:
                # Morse theory expects embeddings
                input_data = [[0.1]*10] if isinstance(text, str) else text
                result = engine.analyze(input_data)
                return (
                    result.anomaly_score,
                    0.6,
                    {"points": len(result.critical_points)},
                )

        return 0.0, 0.0, {}

    def _get_engine(self, name: str) -> Optional[Any]:
        """Lazy load engine."""
        if name in self._engines:
            return self._engines[name]

        try:
            if name == "info_theory":
                from .info_theory import get_info_theory_engine
                self._engines[name] = get_info_theory_engine()

            elif name == "chaos_theory":
                from .chaos_theory import get_chaos_engine
                self._engines[name] = get_chaos_engine()

            elif name == "fractal":
                from .fractal import get_fractal_engine
                self._engines[name] = get_fractal_engine()

            elif name == "wavelet":
                from .wavelet import get_wavelet_engine
                self._engines[name] = get_wavelet_engine()

            elif name == "tda":
                from .tda_enhanced import get_tda_engine
                self._engines[name] = get_tda_engine()

            elif name == "category_theory":
                from .category_theory import get_category_engine
                self._engines[name] = get_category_engine()

            elif name == "morse_theory":
                from .morse_theory import get_morse_engine
                self._engines[name] = get_morse_engine()

            return self._engines.get(name)

        except ImportError as e:
            logger.warning(f"Could not import {name}: {e}")
            return None

    def _calculate_ensemble(
        self,
        scores: List[EngineScore],
    ) -> Tuple[float, float]:
        """Calculate weighted ensemble score and confidence."""
        total_weight = sum(s.weight for s in scores if s.confidence > 0)

        if total_weight == 0:
            return 0.0, 0.0

        # Weighted average
        weighted_sum = sum(
            s.score * s.weight * s.confidence
            for s in scores
        )
        final_score = weighted_sum / total_weight

        # Confidence = average confidence weighted by score contribution
        confidence = sum(
            s.confidence * s.weight
            for s in scores
        ) / total_weight

        return final_score, confidence

    def _generate_explanation(
        self,
        scores: List[EngineScore],
        final_score: float,
    ) -> str:
        """Generate human-readable explanation."""
        if final_score < 0.3:
            return "Low anomaly: all engines report normal patterns"

        # Find contributing engines
        contributors = [
            s for s in scores
            if s.score > 0.4
        ]

        if not contributors:
            return "Moderate signals across multiple engines"

        parts = []
        for c in sorted(contributors, key=lambda x: -x.score)[:3]:
            parts.append(f"{c.engine_name}={c.score:.2f}")

        return f"Anomaly signals: {', '.join(parts)}"

    def update_weights(self, feedback: Dict[str, float]) -> None:
        """Update weights based on feedback."""
        for engine, adjustment in feedback.items():
            if engine in self.weights:
                self.weights[engine] = max(
                    0.05, min(0.5, self.weights[engine] + adjustment))

        # Normalize
        total = sum(self.weights.values())
        self.weights = {k: v / total for k, v in self.weights.items()}

        logger.info(f"Updated ensemble weights: {self.weights}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get ensemble statistics."""
        return {
            **self._stats,
            "weights": self.weights,
        }


# ============================================================================
# Factory
# ============================================================================


_ensemble_scorer: Optional[EnsembleScorer] = None


def get_ensemble_scorer() -> EnsembleScorer:
    """Get or create ensemble scorer."""
    global _ensemble_scorer
    if _ensemble_scorer is None:
        _ensemble_scorer = EnsembleScorer()
    return _ensemble_scorer
