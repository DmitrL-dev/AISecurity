"""
Intent Prediction Engine (#49) - Predictive Security

Предсказывает следующий шаг атаки:
- Markov модель переходов
- Sequence analysis
- Early warning system

Блокирует атаки ДО их завершения.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("IntentPrediction")


# ============================================================================
# Data Classes
# ============================================================================


class Intent(Enum):
    """Predicted user intents."""

    BENIGN = "benign"
    CURIOUS = "curious"
    PROBING = "probing"
    TESTING = "testing"
    ATTACKING = "attacking"
    JAILBREAKING = "jailbreaking"
    EXFILTRATING = "exfiltrating"


class ThreatLevel(Enum):
    """Predicted threat level."""

    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class PredictionResult:
    """Result of intent prediction."""

    current_intent: Intent
    predicted_next: Intent
    threat_level: ThreatLevel
    attack_probability: float
    confidence: float
    trajectory: List[Intent] = field(default_factory=list)
    warning: str = ""
    should_block: bool = False


# ============================================================================
# Intent Patterns
# ============================================================================

# Patterns indicating different intents
INTENT_PATTERNS = {
    Intent.PROBING: [
        r"what\s+(can|do)\s+you\s+(do|know)",
        r"tell\s+me\s+about\s+(your|the)\s+(limits|rules)",
        r"are\s+you\s+able\s+to",
        r"what\s+are\s+(your|the)\s+restrictions",
    ],
    Intent.TESTING: [
        r"let('s|us)?\s+(try|test|see)",
        r"can\s+you\s+(please\s+)?try",
        r"what\s+(happens|if)\s+",
        r"would\s+you\s+(be\s+able|mind)",
    ],
    Intent.ATTACKING: [
        r"ignore\s+(all\s+)?(previous|prior)",
        r"forget\s+(your|all)\s+(instructions|rules)",
        r"you\s+must\s+(now|always)",
        r"override\s+(your|the)",
    ],
    Intent.JAILBREAKING: [
        r"you\s+are\s+(now|no\s+longer)",
        r"pretend\s+(to\s+be|you\s+are)",
        r"act\s+as\s+(if|a)",
        r"roleplay\s+as",
        r"DAN|jailbreak|developer\s+mode",
    ],
    Intent.EXFILTRATING: [
        r"show\s+me\s+(your|the)\s+(prompt|instructions)",
        r"repeat\s+(everything|all)",
        r"what\s+(were|are)\s+you\s+told",
        r"print\s+(your|the)\s+(config|system)",
    ],
}

# Transition probabilities (simplified Markov model)
TRANSITION_PROBS = {
    Intent.BENIGN: {
        Intent.BENIGN: 0.85,
        Intent.CURIOUS: 0.10,
        Intent.PROBING: 0.04,
        Intent.TESTING: 0.01,
    },
    Intent.CURIOUS: {
        Intent.BENIGN: 0.50,
        Intent.CURIOUS: 0.30,
        Intent.PROBING: 0.15,
        Intent.TESTING: 0.05,
    },
    Intent.PROBING: {
        Intent.BENIGN: 0.20,
        Intent.CURIOUS: 0.20,
        Intent.PROBING: 0.30,
        Intent.TESTING: 0.20,
        Intent.ATTACKING: 0.10,
    },
    Intent.TESTING: {
        Intent.BENIGN: 0.10,
        Intent.PROBING: 0.20,
        Intent.TESTING: 0.30,
        Intent.ATTACKING: 0.25,
        Intent.JAILBREAKING: 0.15,
    },
    Intent.ATTACKING: {
        Intent.TESTING: 0.10,
        Intent.ATTACKING: 0.40,
        Intent.JAILBREAKING: 0.30,
        Intent.EXFILTRATING: 0.20,
    },
    Intent.JAILBREAKING: {
        Intent.ATTACKING: 0.30,
        Intent.JAILBREAKING: 0.40,
        Intent.EXFILTRATING: 0.30,
    },
    Intent.EXFILTRATING: {
        Intent.ATTACKING: 0.20,
        Intent.JAILBREAKING: 0.20,
        Intent.EXFILTRATING: 0.60,
    },
}


# ============================================================================
# Intent Classifier
# ============================================================================


class IntentClassifier:
    """Classifies current message intent."""

    def __init__(self):
        self._patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

    def classify(self, message: str) -> Tuple[Intent, float]:
        """
        Classify message intent.

        Returns:
            (intent, confidence)
        """
        scores = defaultdict(float)

        for intent, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.search(message):
                    scores[intent] += 0.25

        if not scores:
            return Intent.BENIGN, 0.8

        # Find best match
        best_intent = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_intent])

        return best_intent, confidence


# ============================================================================
# Trajectory Analyzer
# ============================================================================


class TrajectoryAnalyzer:
    """Analyzes conversation trajectory for attack patterns."""

    ESCALATION_PATTERNS = [
        [Intent.CURIOUS, Intent.PROBING, Intent.TESTING],
        [Intent.PROBING, Intent.TESTING, Intent.ATTACKING],
        [Intent.TESTING, Intent.ATTACKING, Intent.JAILBREAKING],
        [Intent.PROBING, Intent.ATTACKING, Intent.EXFILTRATING],
    ]

    def analyze(self, trajectory: List[Intent]) -> Tuple[bool, float, str]:
        """
        Analyze trajectory for attack escalation.

        Returns:
            (is_escalating, escalation_score, pattern_name)
        """
        if len(trajectory) < 3:
            return False, 0.0, ""

        recent = trajectory[-3:]

        for pattern in self.ESCALATION_PATTERNS:
            if recent == pattern:
                return True, 1.0, f"{pattern[0].value}→{pattern[-1].value}"

        # Check for gradual escalation
        threat_levels = [self._intent_to_threat(i) for i in recent]
        if all(
            threat_levels[i] <= threat_levels[i + 1]
            for i in range(len(threat_levels) - 1)
        ):
            if threat_levels[-1] > threat_levels[0]:
                score = (threat_levels[-1] - threat_levels[0]) / 4
                return True, score, "gradual_escalation"

        return False, 0.0, ""

    def _intent_to_threat(self, intent: Intent) -> int:
        """Map intent to threat level."""
        mapping = {
            Intent.BENIGN: 0,
            Intent.CURIOUS: 1,
            Intent.PROBING: 2,
            Intent.TESTING: 3,
            Intent.ATTACKING: 4,
            Intent.JAILBREAKING: 4,
            Intent.EXFILTRATING: 4,
        }
        return mapping.get(intent, 0)


# ============================================================================
# Markov Predictor
# ============================================================================


class MarkovPredictor:
    """Predicts next intent using transition probabilities."""

    def predict_next(self, current: Intent) -> Tuple[Intent, float]:
        """
        Predict most likely next intent.

        Returns:
            (predicted_intent, probability)
        """
        probs = TRANSITION_PROBS.get(current, {Intent.BENIGN: 1.0})

        best_next = max(probs, key=probs.get)
        probability = probs[best_next]

        return best_next, probability

    def calculate_attack_probability(
        self, trajectory: List[Intent], horizon: int = 3
    ) -> float:
        """
        Calculate probability of attack within horizon steps.

        Uses forward simulation through Markov chain.
        """
        if not trajectory:
            return 0.0

        current = trajectory[-1]
        attack_intents = {Intent.ATTACKING,
                          Intent.JAILBREAKING, Intent.EXFILTRATING}

        if current in attack_intents:
            return 1.0

        # Simulate forward
        prob_attack = 0.0
        prob_current_state = 1.0

        state = current
        for step in range(horizon):
            probs = TRANSITION_PROBS.get(state, {Intent.BENIGN: 1.0})

            # Sum probability of reaching attack state
            for intent, prob in probs.items():
                if intent in attack_intents:
                    prob_attack += prob_current_state * prob

            # Move to most likely non-attack state
            non_attack_probs = {
                k: v for k, v in probs.items() if k not in attack_intents
            }
            if non_attack_probs:
                state = max(non_attack_probs, key=non_attack_probs.get)
                prob_current_state *= non_attack_probs[state]
            else:
                break

        return min(1.0, prob_attack)


class AdaptiveMarkovPredictor(MarkovPredictor):
    """
    Markov predictor with test-time learning (Titans/MIRAS inspired).

    Unlike static MarkovPredictor, this class:
    - Learns from attack outcomes
    - Adapts transition probabilities over time
    - Uses regularization to avoid catastrophic forgetting

    Usage:
        predictor = AdaptiveMarkovPredictor()
        pred = predictor.predict_next(Intent.PROBING)

        # After knowing the outcome
        predictor.learn(trajectory, was_attack=True)
    """

    def __init__(
        self,
        learning_rate: float = 0.05,
        regularization: float = 0.1,
        momentum: float = 0.9,
    ):
        super().__init__()

        # Learned adjustments on top of base probabilities
        self.deltas: Dict[Intent, Dict[Intent, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Hyperparameters
        self.learning_rate = learning_rate
        self.regularization = regularization  # Retention gate strength
        self.momentum = momentum

        # Momentum buffers
        self.momentum_buffer: Dict[Intent, Dict[Intent, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        # Statistics
        self.learn_count = 0
        self.attack_learn_count = 0

    def predict_next(
        self, current: Intent, context: Optional[List[Intent]] = None
    ) -> Tuple[Intent, float]:
        """
        Predict with adaptive probabilities.

        Args:
            current: Current intent
            context: Optional trajectory context (unused for now)

        Returns:
            (predicted_intent, probability)
        """
        base_probs = TRANSITION_PROBS.get(current, {Intent.BENIGN: 1.0})

        # Apply learned deltas with regularization
        adjusted = {}
        for intent in Intent:
            base = base_probs.get(intent, 0.0)
            delta = self.deltas[current][intent]
            # Regularization pulls toward prior
            adjusted[intent] = base + delta * (1 - self.regularization)

        # Ensure non-negative and normalize
        adjusted = {k: max(0, v) for k, v in adjusted.items()}
        total = sum(adjusted.values())
        if total > 0:
            adjusted = {k: v / total for k, v in adjusted.items()}
        else:
            adjusted = {Intent.BENIGN: 1.0}

        best = max(adjusted, key=adjusted.get)
        return best, adjusted[best]

    def learn(self, trajectory: List[Intent], was_attack: bool) -> None:
        """
        Update transition probabilities based on outcome.

        This is the key test-time learning from Titans:
        - was_attack=True: strengthen transitions in trajectory
        - was_attack=False: weaken transitions (false positive)

        Args:
            trajectory: Sequence of intents
            was_attack: Whether this turned out to be an attack
        """
        if len(trajectory) < 2:
            return

        self.learn_count += 1
        if was_attack:
            self.attack_learn_count += 1

        # Direction of update
        direction = 1.0 if was_attack else -0.5

        for i in range(len(trajectory) - 1):
            from_state = trajectory[i]
            to_state = trajectory[i + 1]

            # Compute gradient
            grad = direction * self.learning_rate

            # Momentum update
            old_momentum = self.momentum_buffer[from_state][to_state]
            new_momentum = self.momentum * \
                old_momentum + (1 - self.momentum) * grad
            self.momentum_buffer[from_state][to_state] = new_momentum

            # Apply update
            self.deltas[from_state][to_state] += new_momentum

        logger.debug(
            f"AdaptiveMarkov learned: trajectory length={len(trajectory)}, "
            f"was_attack={was_attack}, total_learns={self.learn_count}"
        )

    def get_learned_transitions(self) -> Dict[str, Dict[str, float]]:
        """Get learned delta values for inspection."""
        return {
            from_state.value: {
                to_state.value: delta
                for to_state, delta in to_deltas.items()
                if abs(delta) > 0.001
            }
            for from_state, to_deltas in self.deltas.items()
            if any(abs(d) > 0.001 for d in to_deltas.values())
        }

    def reset_learning(self) -> None:
        """Reset all learned deltas."""
        self.deltas = defaultdict(lambda: defaultdict(float))
        self.momentum_buffer = defaultdict(lambda: defaultdict(float))
        self.learn_count = 0
        self.attack_learn_count = 0


# ============================================================================
# Main Engine
# ============================================================================


class IntentPredictionEngine:
    """
    Engine #49: Intent Prediction

    Predicts attack trajectory and provides early warnings
    before attacks complete.
    """

    BLOCK_THRESHOLD = 0.75
    WARN_THRESHOLD = 0.50

    def __init__(self):
        self.classifier = IntentClassifier()
        self.trajectory_analyzer = TrajectoryAnalyzer()
        self.predictor = MarkovPredictor()

        # Session tracking
        self._sessions: Dict[str, List[Intent]] = defaultdict(list)

        logger.info("IntentPredictionEngine initialized")

    def predict(
        self, message: str, session_id: Optional[str] = None
    ) -> PredictionResult:
        """
        Predict user intent and attack probability.

        Args:
            message: Current user message
            session_id: Session identifier for trajectory tracking

        Returns:
            PredictionResult with predictions
        """
        # Classify current intent
        current_intent, confidence = self.classifier.classify(message)

        # Update trajectory
        if session_id:
            self._sessions[session_id].append(current_intent)
            trajectory = self._sessions[session_id]
        else:
            trajectory = [current_intent]

        # Predict next intent
        predicted_next, next_prob = self.predictor.predict_next(current_intent)

        # Calculate attack probability
        attack_prob = self.predictor.calculate_attack_probability(trajectory)

        # Analyze trajectory for escalation
        is_escalating, escalation_score, pattern = self.trajectory_analyzer.analyze(
            trajectory
        )

        # Combine scores
        if is_escalating:
            attack_prob = max(attack_prob, escalation_score)

        # Determine threat level
        if attack_prob >= 0.8:
            threat_level = ThreatLevel.CRITICAL
        elif attack_prob >= 0.6:
            threat_level = ThreatLevel.HIGH
        elif attack_prob >= 0.4:
            threat_level = ThreatLevel.MEDIUM
        elif attack_prob >= 0.2:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = ThreatLevel.NONE

        # Generate warning
        warning = ""
        should_block = False

        if attack_prob >= self.BLOCK_THRESHOLD:
            warning = f"HIGH PROBABILITY ATTACK: {attack_prob:.0%}"
            should_block = True
        elif attack_prob >= self.WARN_THRESHOLD:
            warning = f"Potential attack trajectory detected: {pattern or current_intent.value}"

        result = PredictionResult(
            current_intent=current_intent,
            predicted_next=predicted_next,
            threat_level=threat_level,
            attack_probability=attack_prob,
            confidence=confidence,
            trajectory=trajectory[-5:],  # Last 5
            warning=warning,
            should_block=should_block,
        )

        if warning:
            logger.warning(
                f"Intent prediction: {current_intent.value} → {predicted_next.value}, "
                f"attack_prob={attack_prob:.2f}"
            )

        return result

    def reset_session(self, session_id: str):
        """Reset trajectory for session."""
        if session_id in self._sessions:
            del self._sessions[session_id]


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[IntentPredictionEngine] = None


def get_engine() -> IntentPredictionEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = IntentPredictionEngine()
    return _default_engine


def predict_intent(message: str, session_id: Optional[str] = None) -> PredictionResult:
    return get_engine().predict(message, session_id)
