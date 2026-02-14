"""
Cross-Engine Intelligence v1.0 - Ensemble Analysis

Features:
  1. Ensemble Voting - weighted combination of engine results
  2. Attack Chain Detection - multi-step attack patterns
  3. Confidence Calibration - adjust scores based on agreement
  4. Engine Correlation - detect which engines fire together
  5. Fusion Strategies - majority, weighted, Bayesian
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time

logger = logging.getLogger("CrossEngineIntelligence")


# ============================================================================
# Enums and Constants
# ============================================================================

class FusionStrategy(Enum):
    MAJORITY = "majority"      # >50% engines agree
    WEIGHTED = "weighted"      # Weight by engine accuracy
    MAX = "max"                # Take highest risk
    BAYESIAN = "bayesian"      # Bayesian combination
    UNANIMOUS = "unanimous"    # All must agree to block


class AttackPhase(Enum):
    RECONNAISSANCE = "reconnaissance"  # Testing limits
    PREPARATION = "preparation"        # Building context
    EXPLOITATION = "exploitation"      # Actual attack
    EXFILTRATION = "exfiltration"      # Data extraction


# Engine weights (based on accuracy/importance)
DEFAULT_ENGINE_WEIGHTS = {
    "injection": 1.0,
    "qwen3guard": 0.9,
    "knowledge_guard": 0.85,
    "pii": 0.8,
    "query": 0.75,
    "geometric": 0.6,
    "behavioral": 0.7,
    "language": 0.5,
    "streaming": 0.8,
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class EngineResult:
    """Standardized engine result."""
    engine_name: str
    is_safe: bool
    risk_score: float
    threats: List[str] = field(default_factory=list)
    confidence: float = 1.0
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "engine": self.engine_name,
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "threats": self.threats,
            "confidence": self.confidence,
            "latency_ms": self.latency_ms
        }


@dataclass
class EnsembleResult:
    """Combined result from all engines."""
    is_safe: bool
    risk_score: float
    confidence: float
    strategy: FusionStrategy
    threats: List[str] = field(default_factory=list)
    engine_results: List[EngineResult] = field(default_factory=list)
    agreement_ratio: float = 0.0
    attack_chain: Optional['AttackChain'] = None

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "strategy": self.strategy.value,
            "threats": self.threats,
            "agreement_ratio": self.agreement_ratio,
            "engines_triggered": [e.engine_name for e in self.engine_results if not e.is_safe],
            "attack_chain": self.attack_chain.to_dict() if self.attack_chain else None
        }


@dataclass
class AttackChain:
    """Detected multi-step attack sequence."""
    phases: List[AttackPhase]
    steps: List[Dict[str, Any]]
    confidence: float
    total_risk: float

    def to_dict(self) -> dict:
        return {
            "phases": [p.value for p in self.phases],
            "step_count": len(self.steps),
            "confidence": self.confidence,
            "total_risk": self.total_risk
        }


# ============================================================================
# Attack Chain Detector
# ============================================================================

class AttackChainDetector:
    """Detects multi-step attack patterns across requests."""

    # Attack patterns (sequence of threat types that indicate chain)
    ATTACK_PATTERNS = {
        "prompt_injection_chain": [
            (["role_confusion", "persona_shift"], AttackPhase.PREPARATION),
            (["prompt_injection", "jailbreak"], AttackPhase.EXPLOITATION),
        ],
        "data_exfil_chain": [
            (["reconnaissance", "probing"], AttackPhase.RECONNAISSANCE),
            (["system_prompt", "data_exfil"], AttackPhase.EXFILTRATION),
        ],
        "gradual_escalation": [
            (["low_risk", "medium_risk"], AttackPhase.RECONNAISSANCE),
            (["hypothetical_bypass", "fiction_shield"], AttackPhase.PREPARATION),
            (["prompt_injection", "jailbreak"], AttackPhase.EXPLOITATION),
        ],
    }

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)

    def add_request(self, session_id: str, threats: List[str], risk_score: float):
        """Add request to session history."""
        self.sessions[session_id].append({
            "threats": threats,
            "risk_score": risk_score,
            "timestamp": time.time()
        })

        # Keep only recent requests
        if len(self.sessions[session_id]) > self.window_size:
            self.sessions[session_id] = self.sessions[session_id][-self.window_size:]

    def detect(self, session_id: str) -> Optional[AttackChain]:
        """Detect if current session matches an attack chain pattern."""
        if session_id not in self.sessions:
            return None

        history = self.sessions[session_id]
        if len(history) < 2:
            return None

        # Collect all threats from session
        all_threats = []
        for req in history:
            all_threats.extend(req["threats"])

        # Check against known patterns
        for pattern_name, pattern_phases in self.ATTACK_PATTERNS.items():
            matched_phases = []
            matched_steps = []

            for phase_threats, phase_type in pattern_phases:
                # Check if any threat from this phase was seen
                for threat in phase_threats:
                    if any(threat in t.lower() for t in all_threats):
                        matched_phases.append(phase_type)
                        matched_steps.append({
                            "phase": phase_type.value,
                            "matched_threat": threat
                        })
                        break

            # If we matched multiple phases, it's an attack chain
            if len(matched_phases) >= 2:
                total_risk = sum(r["risk_score"] for r in history)
                confidence = len(matched_phases) / len(pattern_phases)

                return AttackChain(
                    phases=matched_phases,
                    steps=matched_steps,
                    confidence=confidence,
                    total_risk=min(100, total_risk)
                )

        # Check for risk escalation pattern
        risks = [r["risk_score"] for r in history]
        if len(risks) >= 3:
            # Monotonically increasing risk
            if all(risks[i] <= risks[i+1] for i in range(len(risks)-1)):
                if risks[-1] > risks[0] + 30:  # Significant escalation
                    return AttackChain(
                        phases=[AttackPhase.RECONNAISSANCE,
                                AttackPhase.EXPLOITATION],
                        steps=[{"phase": "escalation",
                                "risk_delta": risks[-1] - risks[0]}],
                        confidence=0.7,
                        total_risk=min(100, risks[-1] + 20)
                    )

        return None


# ============================================================================
# Confidence Calibrator
# ============================================================================

class ConfidenceCalibrator:
    """Calibrates confidence based on engine agreement."""

    def __init__(self):
        # Track historical accuracy per engine
        self.engine_accuracy: Dict[str, List[float]] = defaultdict(list)

    def calibrate(self, engine_results: List[EngineResult]) -> float:
        """
        Calculate calibrated confidence based on engine agreement.
        Returns confidence score 0-1.
        """
        if not engine_results:
            return 0.0

        # Count votes
        block_votes = sum(1 for e in engine_results if not e.is_safe)
        total_votes = len(engine_results)

        if total_votes == 0:
            return 0.0

        agreement_ratio = block_votes / total_votes

        # High agreement = high confidence
        if agreement_ratio >= 0.8:
            return 0.95
        elif agreement_ratio >= 0.6:
            return 0.8
        elif agreement_ratio >= 0.4:
            return 0.6
        elif agreement_ratio > 0:
            return 0.4
        else:
            return 0.9  # All agree it's safe

    def update_accuracy(self, engine_name: str, was_correct: bool):
        """Update engine accuracy based on feedback."""
        self.engine_accuracy[engine_name].append(1.0 if was_correct else 0.0)
        # Keep last 100 samples
        if len(self.engine_accuracy[engine_name]) > 100:
            self.engine_accuracy[engine_name] = self.engine_accuracy[engine_name][-100:]

    def get_engine_accuracy(self, engine_name: str) -> float:
        """Get historical accuracy for engine."""
        history = self.engine_accuracy.get(engine_name, [])
        if not history:
            return 0.8  # Default
        return sum(history) / len(history)


# ============================================================================
# Fusion Engine
# ============================================================================

class FusionEngine:
    """Combines results from multiple engines."""

    def __init__(self,
                 strategy: FusionStrategy = FusionStrategy.WEIGHTED,
                 weights: Dict[str, float] = None,
                 threshold: float = 70.0):
        self.strategy = strategy
        self.weights = weights or DEFAULT_ENGINE_WEIGHTS
        self.threshold = threshold

    def fuse(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """
        Combine engine results.
        Returns (is_safe, combined_risk_score).
        """
        if not results:
            return True, 0.0

        if self.strategy == FusionStrategy.MAX:
            return self._fuse_max(results)
        elif self.strategy == FusionStrategy.MAJORITY:
            return self._fuse_majority(results)
        elif self.strategy == FusionStrategy.WEIGHTED:
            return self._fuse_weighted(results)
        elif self.strategy == FusionStrategy.UNANIMOUS:
            return self._fuse_unanimous(results)
        elif self.strategy == FusionStrategy.BAYESIAN:
            return self._fuse_bayesian(results)
        else:
            return self._fuse_max(results)

    def _fuse_max(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """Take maximum risk score."""
        max_risk = max(r.risk_score for r in results)
        return max_risk < self.threshold, max_risk

    def _fuse_majority(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """Majority vote."""
        block_votes = sum(1 for r in results if not r.is_safe)
        is_safe = block_votes <= len(results) / 2
        avg_risk = sum(r.risk_score for r in results) / len(results)
        return is_safe, avg_risk

    def _fuse_weighted(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """Weighted average by engine importance."""
        total_weight = 0.0
        weighted_risk = 0.0

        for r in results:
            weight = self.weights.get(r.engine_name, 0.5)
            weighted_risk += r.risk_score * weight
            total_weight += weight

        if total_weight == 0:
            return True, 0.0

        final_risk = weighted_risk / total_weight
        return final_risk < self.threshold, final_risk

    def _fuse_unanimous(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """All engines must agree to block."""
        all_block = all(not r.is_safe for r in results)
        max_risk = max(r.risk_score for r in results)
        return not all_block, max_risk

    def _fuse_bayesian(self, results: List[EngineResult]) -> Tuple[bool, float]:
        """Bayesian combination of probabilities."""
        # Convert risk scores to probabilities
        probs = [r.risk_score / 100.0 for r in results]

        # Naive Bayes combination
        prob_threat = 0.1  # Prior probability of threat

        for p in probs:
            # P(threat|evidence) ∝ P(evidence|threat) * P(threat)
            likelihood_threat = p
            likelihood_safe = 1 - p

            posterior_threat = likelihood_threat * prob_threat
            posterior_safe = likelihood_safe * (1 - prob_threat)

            # Normalize
            total = posterior_threat + posterior_safe
            if total > 0:
                prob_threat = posterior_threat / total

        final_risk = prob_threat * 100
        return final_risk < self.threshold, final_risk


# ============================================================================
# Main Cross-Engine Intelligence
# ============================================================================

class CrossEngineIntelligence:
    """
    Cross-Engine Intelligence v1.0

    Combines results from multiple detection engines using:
      - Ensemble voting
      - Attack chain detection
      - Confidence calibration
    """

    def __init__(self,
                 strategy: FusionStrategy = FusionStrategy.WEIGHTED,
                 threshold: float = 70.0):
        logger.info("Initializing Cross-Engine Intelligence v1.0...")

        self.fusion = FusionEngine(strategy=strategy, threshold=threshold)
        self.calibrator = ConfidenceCalibrator()
        self.chain_detector = AttackChainDetector()

        logger.info(
            f"Cross-Engine Intelligence initialized (strategy={strategy.value})")

    def analyze(self,
                engine_results: List[EngineResult],
                session_id: str = None) -> EnsembleResult:
        """
        Analyze combined engine results.

        Args:
            engine_results: Results from individual engines
            session_id: Session ID for attack chain detection

        Returns:
            EnsembleResult with combined verdict
        """
        # Fuse results
        is_safe, risk_score = self.fusion.fuse(engine_results)

        # Calculate confidence
        confidence = self.calibrator.calibrate(engine_results)

        # Collect all threats
        all_threats = []
        for r in engine_results:
            all_threats.extend(r.threats)

        # Calculate agreement ratio
        if engine_results:
            block_votes = sum(1 for r in engine_results if not r.is_safe)
            agreement_ratio = max(block_votes, len(
                engine_results) - block_votes) / len(engine_results)
        else:
            agreement_ratio = 1.0

        # Detect attack chain
        attack_chain = None
        if session_id and all_threats:
            self.chain_detector.add_request(
                session_id, all_threats, risk_score)
            attack_chain = self.chain_detector.detect(session_id)

            # Boost risk if attack chain detected
            if attack_chain:
                risk_score = max(risk_score, attack_chain.total_risk)
                if risk_score >= self.fusion.threshold:
                    is_safe = False

        return EnsembleResult(
            is_safe=is_safe,
            risk_score=risk_score,
            confidence=confidence,
            strategy=self.fusion.strategy,
            threats=list(set(all_threats)),
            engine_results=engine_results,
            agreement_ratio=agreement_ratio,
            attack_chain=attack_chain
        )

    def create_engine_result(self,
                             engine_name: str,
                             result_dict: dict) -> EngineResult:
        """Helper to create EngineResult from engine output dict."""
        return EngineResult(
            engine_name=engine_name,
            is_safe=result_dict.get("is_safe", True),
            risk_score=result_dict.get("risk_score", 0.0),
            threats=result_dict.get("threats", []),
            confidence=result_dict.get("confidence", 1.0),
            latency_ms=result_dict.get("latency_ms", 0.0)
        )


# ============================================================================
# Factory
# ============================================================================

def create_intelligence(strategy: str = "weighted") -> CrossEngineIntelligence:
    """Create intelligence instance with specified strategy."""
    strategy_map = {
        "majority": FusionStrategy.MAJORITY,
        "weighted": FusionStrategy.WEIGHTED,
        "max": FusionStrategy.MAX,
        "bayesian": FusionStrategy.BAYESIAN,
        "unanimous": FusionStrategy.UNANIMOUS,
    }
    return CrossEngineIntelligence(
        strategy=strategy_map.get(strategy, FusionStrategy.WEIGHTED)
    )
