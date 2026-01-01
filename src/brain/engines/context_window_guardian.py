"""
Context Window Guardian Engine - Many-Shot Jailbreak Defense

Protects context window from manipulation:
- Context length monitoring
- Pattern repetition detection
- Many-shot jailbreak defense
- Context poisoning detection

Addresses: OWASP ASI-01 (Many-Shot Jailbreak)
Research: context_window_security_deep_dive.md
Invention: Context Window Guardian (#42)
"""

import re
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ContextWindowGuardian")


# ============================================================================
# Data Classes
# ============================================================================


class ContextViolationType(Enum):
    """Types of context violations."""

    MANY_SHOT = "many_shot_jailbreak"
    REPETITION_ATTACK = "repetition_attack"
    CONTEXT_OVERFLOW = "context_overflow"
    PAYLOAD_INJECTION = "payload_injection"
    PROGRESSIVE_ESCALATION = "progressive_escalation"


@dataclass
class ContextAnalysisResult:
    """Result from context analysis."""

    is_safe: bool
    risk_score: float
    violations: List[ContextViolationType] = field(default_factory=list)
    message_count: int = 0
    unique_patterns: int = 0
    repetition_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "message_count": self.message_count,
            "repetition_score": self.repetition_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Many-Shot Detector
# ============================================================================


class ManyShotDetector:
    """
    Detects many-shot jailbreak attempts.
    """

    def __init__(
        self,
        threshold: int = 10,
        similarity_threshold: float = 0.7,
    ):
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold

    def detect(self, messages: List[str]) -> Tuple[bool, float, str]:
        """
        Detect many-shot jailbreak.

        Returns:
            (detected, confidence, description)
        """
        if len(messages) < self.threshold:
            return False, 0.0, ""

        # Check for similar messages
        similar_count = 0
        for i in range(1, len(messages)):
            if (
                self._similarity(messages[i - 1], messages[i])
                > self.similarity_threshold
            ):
                similar_count += 1

        ratio = similar_count / len(messages)
        if ratio > 0.5:
            return True, ratio, f"Many similar messages: {similar_count}"

        return False, ratio, ""

    def _similarity(self, a: str, b: str) -> float:
        """Simple word overlap similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())

        if not words_a or not words_b:
            return 0.0

        overlap = len(words_a & words_b)
        return overlap / max(len(words_a), len(words_b))


# ============================================================================
# Repetition Detector
# ============================================================================


class RepetitionDetector:
    """
    Detects repetition-based attacks.
    """

    def __init__(self, max_repetitions: int = 3):
        self.max_repetitions = max_repetitions

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect repetition attacks.

        Returns:
            (detected, score, repeated_patterns)
        """
        # Find repeated phrases (3+ words)
        words = text.lower().split()
        repeated = []

        for n in range(3, min(10, len(words) // 2)):
            ngrams = [" ".join(words[i: i + n])
                      for i in range(len(words) - n + 1)]
            counts = Counter(ngrams)

            for ngram, count in counts.items():
                if count > self.max_repetitions:
                    repeated.append(ngram)

        if repeated:
            score = min(1.0, len(repeated) * 0.2)
            return True, score, repeated

        return False, 0.0, []


# ============================================================================
# Escalation Detector
# ============================================================================


class EscalationDetector:
    """
    Detects progressive escalation in context.
    """

    SEVERITY_KEYWORDS = {
        1: ["help", "explain", "what is"],
        2: ["how to", "can you", "show me"],
        3: ["bypass", "ignore", "override"],
        4: ["hack", "exploit", "attack"],
        5: ["dangerous", "illegal", "harmful"],
    }

    def detect(self, messages: List[str]) -> Tuple[bool, float, str]:
        """
        Detect progressive escalation.

        Returns:
            (detected, confidence, description)
        """
        if len(messages) < 3:
            return False, 0.0, ""

        severities = []
        for msg in messages:
            msg_lower = msg.lower()
            max_sev = 0
            for sev, keywords in self.SEVERITY_KEYWORDS.items():
                if any(kw in msg_lower for kw in keywords):
                    max_sev = max(max_sev, sev)
            severities.append(max_sev)

        # Check for escalating pattern
        escalations = sum(
            1 for i in range(1, len(severities)) if severities[i] > severities[i - 1]
        )

        if escalations >= len(messages) // 2 and severities[-1] >= 3:
            conf = min(1.0, escalations / len(messages))
            return True, conf, f"Escalation detected: {severities}"

        return False, 0.0, ""


# ============================================================================
# Main Engine
# ============================================================================


class ContextWindowGuardian:
    """
    Context Window Guardian - Many-Shot Jailbreak Defense

    Comprehensive context protection:
    - Many-shot detection
    - Repetition detection
    - Escalation detection
    - Length monitoring

    Invention #42 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(
        self,
        max_context_length: int = 100000,
        max_messages: int = 100,
    ):
        self.many_shot_detector = ManyShotDetector()
        self.repetition_detector = RepetitionDetector()
        self.escalation_detector = EscalationDetector()

        self.max_context_length = max_context_length
        self.max_messages = max_messages

        logger.info("ContextWindowGuardian initialized")

    def analyze(
        self,
        messages: List[str],
    ) -> ContextAnalysisResult:
        """
        Analyze context window for attacks.

        Args:
            messages: List of messages in context

        Returns:
            ContextAnalysisResult
        """
        start = time.time()

        violations = []
        max_risk = 0.0
        explanations = []

        # Check context length
        total_chars = sum(len(m) for m in messages)
        if total_chars > self.max_context_length:
            violations.append(ContextViolationType.CONTEXT_OVERFLOW)
            max_risk = max(max_risk, 0.6)
            explanations.append("Context length exceeded")

        if len(messages) > self.max_messages:
            violations.append(ContextViolationType.CONTEXT_OVERFLOW)
            max_risk = max(max_risk, 0.5)
            explanations.append("Too many messages")

        # Many-shot detection
        ms_detected, ms_conf, ms_desc = self.many_shot_detector.detect(
            messages)
        if ms_detected:
            violations.append(ContextViolationType.MANY_SHOT)
            max_risk = max(max_risk, ms_conf)
            explanations.append(ms_desc)

        # Repetition detection
        full_context = " ".join(messages)
        rep_detected, rep_score, rep_patterns = self.repetition_detector.detect(
            full_context
        )
        if rep_detected:
            violations.append(ContextViolationType.REPETITION_ATTACK)
            max_risk = max(max_risk, rep_score)
            explanations.append(f"Repeated patterns: {len(rep_patterns)}")

        # Escalation detection
        esc_detected, esc_conf, esc_desc = self.escalation_detector.detect(
            messages)
        if esc_detected:
            violations.append(ContextViolationType.PROGRESSIVE_ESCALATION)
            max_risk = max(max_risk, esc_conf)
            explanations.append(esc_desc)

        is_safe = len(violations) == 0

        if violations:
            logger.warning(
                f"Context violations: {[v.value for v in violations]}")

        return ContextAnalysisResult(
            is_safe=is_safe,
            risk_score=max_risk,
            violations=violations,
            message_count=len(messages),
            unique_patterns=len(set(messages)),
            repetition_score=rep_score,
            explanation="; ".join(
                explanations) if explanations else "Context clean",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_guardian: Optional[ContextWindowGuardian] = None


def get_guardian() -> ContextWindowGuardian:
    global _default_guardian
    if _default_guardian is None:
        _default_guardian = ContextWindowGuardian()
    return _default_guardian
