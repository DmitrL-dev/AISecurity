"""
Proactive Defense Engine (#45) - Anomaly-Based Zero-Day Detection

Упреждающая защита от неизвестных атак:
- Anomaly Baseline — отклонения от нормы
- Invariant Checking — нарушения инвариантов
- Thermodynamic Bounds — физические ограничения
- Causal Validation — причинно-следственный анализ

Safeguards против False Positives:
- Tiered Response (warn before block)
- User Reputation scoring
- Ensemble voting with signature detectors
"""

import re
import math
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger("ProactiveDefense")


# ============================================================================
# Data Classes
# ============================================================================


class AnomalyType(Enum):
    """Types of anomalies detected."""

    ENTROPY_SPIKE = "entropy_spike"
    ENTROPY_DROP = "entropy_drop"
    INVARIANT_VIOLATION = "invariant_violation"
    THERMODYNAMIC_ANOMALY = "thermodynamic_anomaly"
    CAUSAL_BREAK = "causal_break"
    DISTRIBUTION_SHIFT = "distribution_shift"


class ResponseTier(Enum):
    """Tiered response levels."""

    ALLOW = "allow"
    LOG = "log"
    WARN = "warn"
    CHALLENGE = "challenge"
    BLOCK = "block"


@dataclass
class UserReputation:
    """User trust score."""

    user_id: str
    trust_score: float = 0.5  # 0.0 (untrusted) to 1.0 (fully trusted)
    total_requests: int = 0
    blocked_requests: int = 0
    false_positives: int = 0  # User contested and was right


@dataclass
class ProactiveResult:
    """Result from Proactive Defense analysis."""

    response_tier: ResponseTier
    anomaly_score: float
    is_anomalous: bool
    anomaly_types: List[AnomalyType] = field(default_factory=list)
    invariant_violations: List[str] = field(default_factory=list)
    entropy_delta: float = 0.0
    thermodynamic_score: float = 0.0
    confidence: float = 0.0
    explanation: str = ""
    recommendation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "response_tier": self.response_tier.value,
            "anomaly_score": self.anomaly_score,
            "is_anomalous": self.is_anomalous,
            "anomaly_types": [t.value for t in self.anomaly_types],
            "invariant_violations": self.invariant_violations,
            "entropy_delta": self.entropy_delta,
            "thermodynamic_score": self.thermodynamic_score,
            "confidence": self.confidence,
            "explanation": self.explanation,
            "recommendation": self.recommendation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Entropy Calculator
# ============================================================================


class EntropyAnalyzer:
    """Shannon entropy analysis for text."""

    def __init__(self, baseline_entropy: float = 4.5):
        # English text typically has entropy ~4.0-4.5 bits/char
        self.baseline_entropy = baseline_entropy
        self._history = deque(maxlen=100)

    def calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0

        # Character frequency
        freq = {}
        for char in text.lower():
            freq[char] = freq.get(char, 0) + 1

        total = len(text)
        entropy = 0.0

        for count in freq.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def analyze(self, text: str) -> Tuple[float, float, bool, bool]:
        """
        Analyze entropy anomalies.

        Returns:
            (entropy, delta_from_baseline, is_spike, is_drop)
        """
        entropy = self.calculate_entropy(text)
        self._history.append(entropy)

        # Compare to baseline
        delta = entropy - self.baseline_entropy

        # Spike: unusually high entropy (random/encrypted data)
        is_spike = entropy > 6.0  # Near maximum for ASCII

        # Drop: unusually low entropy (repeated patterns)
        is_drop = entropy < 2.5 and len(text) > 50

        return entropy, delta, is_spike, is_drop

    def get_conditional_entropy(self, current: str, context: str) -> float:
        """
        Calculate conditional entropy H(current|context).
        Detects if current is "surprising" given context.
        """
        # Simplified: use n-gram overlap as proxy
        current_ngrams = set(self._get_ngrams(current, 3))
        context_ngrams = set(self._get_ngrams(context, 3))

        if not context_ngrams:
            return self.calculate_entropy(current)

        overlap = len(current_ngrams & context_ngrams)
        surprise = 1.0 - (overlap / max(len(current_ngrams), 1))

        return self.calculate_entropy(current) * (1 + surprise)

    def _get_ngrams(self, text: str, n: int) -> List[str]:
        """Extract n-grams from text."""
        text = text.lower()
        return [text[i : i + n] for i in range(len(text) - n + 1)]


# ============================================================================
# Invariant Checker
# ============================================================================


class InvariantChecker:
    """Checks semantic invariants that should always hold."""

    INVARIANTS = [
        # (name, check_function_name)
        ("intent_consistency", "_check_intent_consistency"),
        ("no_role_confusion", "_check_role_confusion"),
        ("output_bounds", "_check_output_bounds"),
        ("causality", "_check_causality"),
    ]

    def check_all(
        self,
        current_input: str,
        expected_output: Optional[str] = None,
        conversation: Optional[List[dict]] = None,
    ) -> Tuple[List[str], float]:
        """
        Check all invariants.

        Returns:
            (list of violations, violation_score)
        """
        violations = []

        # Intent consistency check
        if conversation and len(conversation) >= 2:
            if self._check_intent_consistency(current_input, conversation):
                violations.append("intent_shift_detected")

        # Role confusion check
        if self._check_role_confusion(current_input):
            violations.append("role_confusion_attempt")

        # Output causality (if output provided)
        if expected_output:
            if self._check_causality(current_input, expected_output):
                violations.append("output_not_caused_by_input")

        score = len(violations) / len(self.INVARIANTS)
        return violations, score

    def _check_intent_consistency(self, current: str, conversation: List[dict]) -> bool:
        """Check if intent changes suspiciously mid-conversation."""
        # Patterns indicating intent shift
        shift_patterns = [
            r"actually\s*,?\s*(now|instead|forget)",
            r"(but|however)\s+now\s+I\s+(want|need)",
            r"change\s+(of|in)\s+plans?",
            r"new\s+instructions?",
        ]

        for pattern in shift_patterns:
            if re.search(pattern, current, re.IGNORECASE):
                return True

        return False

    def _check_role_confusion(self, text: str) -> bool:
        """Check for attempts to confuse roles."""
        confusion_patterns = [
            r"you\s+are\s+(the\s+)?user",
            r"I\s+am\s+(the\s+)?assistant",
            r"swap\s+(our\s+)?roles",
            r"pretend\s+I('m|\s+am)\s+(the\s+)?AI",
        ]

        for pattern in confusion_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        return False

    def _check_causality(self, input_text: str, output: str) -> bool:
        """
        Check if output contains info not caused by input.
        Simplified: check for PII/secrets appearing in output
        but not in input.
        """
        # Patterns that shouldn't appear unless in input
        sensitive_patterns = [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Card
        ]

        for pattern in sensitive_patterns:
            output_matches = set(re.findall(pattern, output))
            input_matches = set(re.findall(pattern, input_text))

            # Found in output but not in input
            leaked = output_matches - input_matches
            if leaked:
                return True

        return False


# ============================================================================
# Thermodynamic Analyzer
# ============================================================================


class ThermodynamicAnalyzer:
    """
    Applies thermodynamic principles to detect anomalies.

    Key insight: Natural text follows certain "energy" patterns.
    Attacks often violate these.
    """

    def __init__(self):
        self._temperature = 1.0  # System "temperature" (baseline)

    def calculate_free_energy(
        self, text: str, prior_distribution: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate variational free energy (surprise).

        F = D_KL(q||p) - E[log p(x|z)]

        Simplified: how "surprising" is this text?
        """
        # Character distribution of text
        q = self._get_distribution(text)

        # Prior: expected English distribution
        p = prior_distribution or self._english_prior()

        # KL divergence
        kl = 0.0
        for char, prob in q.items():
            if prob > 0 and char in p and p[char] > 0:
                kl += prob * math.log(prob / p[char])

        return kl

    def check_second_law(self, messages: List[str]) -> Tuple[bool, float]:
        """
        Second Law: entropy should not decrease spontaneously.

        In conversation, sudden entropy drop = suspicious.
        """
        if len(messages) < 2:
            return False, 0.0

        entropies = [self._entropy(m) for m in messages]

        # Check for significant drops
        for i in range(1, len(entropies)):
            drop = entropies[i - 1] - entropies[i]
            if drop > 1.5:  # Significant drop threshold
                return True, drop

        return False, 0.0

    def calculate_energy_landscape(self, text: str) -> float:
        """
        Calculate "energy" of text in semantic space.

        Low energy = common/expected
        High energy = rare/anomalous
        """
        # Proxy: use character surprisal sum
        prior = self._english_prior()

        energy = 0.0
        for char in text.lower():
            if char in prior:
                # Surprisal = -log(p)
                energy += -math.log(prior[char] + 1e-10)
            else:
                energy += 10.0  # Unknown character = high energy

        # Normalize by length
        return energy / max(len(text), 1)

    def _entropy(self, text: str) -> float:
        """Calculate Shannon entropy."""
        if not text:
            return 0.0

        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1

        total = len(text)
        return -sum((c / total) * math.log2(c / total) for c in freq.values() if c > 0)

    def _get_distribution(self, text: str) -> Dict[str, float]:
        """Get character probability distribution."""
        freq = {}
        for c in text.lower():
            freq[c] = freq.get(c, 0) + 1

        total = len(text) or 1
        return {c: count / total for c, count in freq.items()}

    def _english_prior(self) -> Dict[str, float]:
        """Approximate English character distribution."""
        return {
            " ": 0.18,
            "e": 0.11,
            "t": 0.08,
            "a": 0.07,
            "o": 0.07,
            "i": 0.06,
            "n": 0.06,
            "s": 0.06,
            "h": 0.05,
            "r": 0.05,
            "d": 0.04,
            "l": 0.03,
            "c": 0.03,
            "u": 0.03,
            "m": 0.02,
            "w": 0.02,
            "f": 0.02,
            "g": 0.02,
            "y": 0.02,
            "p": 0.02,
            "b": 0.01,
            "v": 0.01,
            "k": 0.01,
            "j": 0.001,
            "x": 0.001,
            "q": 0.001,
            "z": 0.001,
        }


# ============================================================================
# Reputation Manager
# ============================================================================


class ReputationManager:
    """Manages user trust scores for adaptive thresholds."""

    def __init__(self):
        self._users: Dict[str, UserReputation] = {}

    def get_or_create(self, user_id: str) -> UserReputation:
        """Get or create user reputation."""
        if user_id not in self._users:
            self._users[user_id] = UserReputation(user_id=user_id)
        return self._users[user_id]

    def record_request(self, user_id: str, was_blocked: bool):
        """Record a request outcome."""
        rep = self.get_or_create(user_id)
        rep.total_requests += 1

        if was_blocked:
            rep.blocked_requests += 1
            rep.trust_score = max(0.0, rep.trust_score - 0.1)
        else:
            # Slowly build trust
            rep.trust_score = min(1.0, rep.trust_score + 0.01)

    def record_false_positive(self, user_id: str):
        """User contested a block and was right."""
        rep = self.get_or_create(user_id)
        rep.false_positives += 1
        rep.trust_score = min(1.0, rep.trust_score + 0.15)

    def get_threshold_modifier(self, user_id: str) -> float:
        """
        Get threshold modifier based on trust.

        Higher trust = higher threshold (less strict)
        """
        rep = self.get_or_create(user_id)

        # New users: modifier = 1.0 (baseline)
        # Trusted users: modifier up to 1.3 (30% more lenient)
        # Untrusted users: modifier down to 0.7 (30% stricter)

        return 0.7 + (rep.trust_score * 0.6)


# ============================================================================
# Main Engine
# ============================================================================


class ProactiveDefense:
    """
    Engine #45: Proactive Defense

    Detects unknown attacks through anomaly detection
    with safeguards against false positives.
    """

    # Thresholds for tiered response
    THRESHOLDS = {
        ResponseTier.LOG: 0.3,
        ResponseTier.WARN: 0.5,
        ResponseTier.CHALLENGE: 0.7,
        ResponseTier.BLOCK: 0.9,
    }

    def __init__(
        self,
        enable_thermodynamic: bool = True,
        enable_invariants: bool = True,
        enable_reputation: bool = True,
    ):
        self.entropy_analyzer = EntropyAnalyzer()
        self.invariant_checker = InvariantChecker()
        self.thermo_analyzer = ThermodynamicAnalyzer()
        self.reputation_mgr = ReputationManager()

        self.enable_thermodynamic = enable_thermodynamic
        self.enable_invariants = enable_invariants
        self.enable_reputation = enable_reputation

        logger.info("ProactiveDefense initialized")

    def analyze(
        self,
        text: str,
        user_id: Optional[str] = None,
        conversation: Optional[List[str]] = None,
        signature_score: float = 0.0,  # Score from other detectors
    ) -> ProactiveResult:
        """
        Analyze text for anomalies.

        Args:
            text: Input text
            user_id: User identifier for reputation
            conversation: Previous messages
            signature_score: Score from signature-based detectors

        Returns:
            ProactiveResult
        """
        import time

        start = time.time()

        anomaly_types = []
        explanations = []
        total_score = 0.0
        weights = 0.0

        # 1. Entropy analysis
        entropy, delta, is_spike, is_drop = self.entropy_analyzer.analyze(text)

        if is_spike:
            anomaly_types.append(AnomalyType.ENTROPY_SPIKE)
            explanations.append(f"Entropy spike: {entropy:.2f}")
            total_score += 0.6
            weights += 1.0
        elif is_drop:
            anomaly_types.append(AnomalyType.ENTROPY_DROP)
            explanations.append(f"Entropy drop: {entropy:.2f}")
            total_score += 0.4
            weights += 1.0
        else:
            weights += 1.0  # Normal entropy counts

        # 2. Invariant checking
        violations = []
        if self.enable_invariants:
            conv_dicts = [{"content": m} for m in (conversation or [])]
            violations, inv_score = self.invariant_checker.check_all(
                text, conversation=conv_dicts
            )

            if violations:
                anomaly_types.append(AnomalyType.INVARIANT_VIOLATION)
                explanations.extend(violations[:2])
                total_score += inv_score
                weights += 1.0
            else:
                weights += 1.0

        # 3. Thermodynamic analysis
        thermo_score = 0.0
        if self.enable_thermodynamic:
            # Free energy (surprise)
            free_energy = self.thermo_analyzer.calculate_free_energy(text)

            # Energy landscape
            energy = self.thermo_analyzer.calculate_energy_landscape(text)

            # Second law check
            if conversation:
                violated, drop = self.thermo_analyzer.check_second_law(
                    conversation + [text]
                )
                if violated:
                    anomaly_types.append(AnomalyType.THERMODYNAMIC_ANOMALY)
                    explanations.append(f"Entropy decrease: {drop:.2f}")
                    thermo_score = 0.5

            # High free energy = surprising
            if free_energy > 2.0:
                anomaly_types.append(AnomalyType.DISTRIBUTION_SHIFT)
                thermo_score = max(thermo_score, min(1.0, free_energy / 4.0))

            total_score += thermo_score
            weights += 1.0

        # 4. Combine with signature score (ensemble)
        if signature_score > 0:
            total_score += signature_score
            weights += 1.0

        # Calculate final anomaly score
        anomaly_score = total_score / max(weights, 1.0)

        # 5. Apply reputation modifier
        threshold_mod = 1.0
        if self.enable_reputation and user_id:
            threshold_mod = self.reputation_mgr.get_threshold_modifier(user_id)

        # 6. Determine response tier
        adjusted_score = anomaly_score / threshold_mod

        if adjusted_score >= self.THRESHOLDS[ResponseTier.BLOCK]:
            tier = ResponseTier.BLOCK
        elif adjusted_score >= self.THRESHOLDS[ResponseTier.CHALLENGE]:
            tier = ResponseTier.CHALLENGE
        elif adjusted_score >= self.THRESHOLDS[ResponseTier.WARN]:
            tier = ResponseTier.WARN
        elif adjusted_score >= self.THRESHOLDS[ResponseTier.LOG]:
            tier = ResponseTier.LOG
        else:
            tier = ResponseTier.ALLOW

        # Build recommendation
        if tier == ResponseTier.BLOCK:
            recommendation = "Block request, high anomaly score"
        elif tier == ResponseTier.CHALLENGE:
            recommendation = "Challenge user, request confirmation"
        elif tier == ResponseTier.WARN:
            recommendation = "Allow with warning, monitor closely"
        elif tier == ResponseTier.LOG:
            recommendation = "Allow, log for analysis"
        else:
            recommendation = "Allow, normal request"

        result = ProactiveResult(
            response_tier=tier,
            anomaly_score=anomaly_score,
            is_anomalous=len(anomaly_types) > 0,
            anomaly_types=anomaly_types,
            invariant_violations=violations,
            entropy_delta=delta,
            thermodynamic_score=thermo_score,
            confidence=1.0 - (1.0 / (weights + 1)),
            explanation="; ".join(explanations[:3]) or "Normal",
            recommendation=recommendation,
            latency_ms=(time.time() - start) * 1000,
        )

        if anomaly_types:
            logger.info(
                f"Proactive: tier={tier.value}, score={anomaly_score:.2f}, "
                f"types={[t.value for t in anomaly_types]}"
            )

        return result


# ============================================================================
# Convenience functions
# ============================================================================

_default_defense: Optional[ProactiveDefense] = None


def get_defense() -> ProactiveDefense:
    global _default_defense
    if _default_defense is None:
        _default_defense = ProactiveDefense()
    return _default_defense


def analyze_proactive(
    text: str,
    user_id: Optional[str] = None,
    conversation: Optional[List[str]] = None,
    signature_score: float = 0.0,
) -> ProactiveResult:
    return get_defense().analyze(text, user_id, conversation, signature_score)
