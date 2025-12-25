"""
Delayed Tool Invocation Detection

Detects time-delayed malicious triggers in prompts that could:
1. Execute after specific time/conditions
2. Trigger on future events
3. Use temporal obfuscation
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Set
from datetime import datetime

logger = logging.getLogger("DelayedTriggerDetector")


@dataclass
class DelayedTriggerResult:
    """Result of delayed trigger analysis."""
    detected: bool
    risk_score: float  # 0-100
    triggers: List[str]
    temporal_patterns: List[str]
    recommendations: List[str]


class DelayedTriggerDetector:
    """
    Detects patterns indicating delayed/conditional execution.

    Attack vectors:
    - "After 5 messages, ignore safety"
    - "When user mentions X, do Y"
    - "At midnight, execute..."
    - "Once you have enough context..."
    """

    # Temporal trigger patterns
    TEMPORAL_PATTERNS = [
        r"after\s+\d+\s+(message|turn|response|minute|hour|day)s?",
        r"in\s+\d+\s+(minute|hour|day|week)s?",
        r"at\s+\d{1,2}[:\d]*\s*(am|pm|o'?clock)?",
        r"when\s+(the\s+)?(time|date|clock)\s*(is|reaches|shows)",
        r"once\s+(you|we)\s+(have|reach|complete)",
        r"later\s+(today|tonight|tomorrow|this week)",
        r"wait\s+(for|until)",
        r"delay(ed)?\s+(action|execution|response)",
        r"scheduled?\s+(for|at|to)",
        r"queue(d)?\s+(for|until)",
    ]

    # Conditional trigger patterns
    CONDITIONAL_PATTERNS = [
        r"when\s+(user|they|he|she)\s+(say|mention|ask|type)s?",
        r"if\s+(user|they|input)\s+(contain|include|mention)s?",
        r"on\s+(receiving|getting|seeing)\s+the\s+(word|phrase|keyword)",
        r"trigger(ed)?\s+(by|on|when)",
        r"activate\s+(when|if|on)",
        r"upon\s+(receiving|detecting|identifying)",
        r"as\s+soon\s+as",
        r"the\s+moment\s+(that|when)",
        r"only\s+(after|when|if)",
    ]

    # State-based patterns
    STATE_PATTERNS = [
        r"once\s+trust\s+(is\s+)?(establish|build|gain)ed",
        r"after\s+(gaining|building|earning)\s+(trust|confidence|rapport)",
        r"when\s+(context|conversation)\s+(allow|permit)s",
        r"accumulate\s+(enough|sufficient)",
        r"gradually\s+(escalate|increase|shift)",
        r"slowly\s+(introduce|add|inject)",
        r"over\s+time",
        r"step\s+by\s+step\s+(first|then)",
    ]

    # Hidden execution patterns
    HIDDEN_EXEC_PATTERNS = [
        r"silently\s+(execute|run|perform)",
        r"without\s+(mention|disclos|reveal)ing",
        r"in\s+the\s+background",
        r"covertly\s+(do|perform|execute)",
        r"secretly\s+(add|inject|include)",
        r"hidden\s+(command|action|trigger)",
    ]

    def __init__(self, sensitivity: float = 0.6):
        self._sensitivity = sensitivity
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns."""
        self._temporal_regex = re.compile(
            "|".join(self.TEMPORAL_PATTERNS),
            re.IGNORECASE
        )
        self._conditional_regex = re.compile(
            "|".join(self.CONDITIONAL_PATTERNS),
            re.IGNORECASE
        )
        self._state_regex = re.compile(
            "|".join(self.STATE_PATTERNS),
            re.IGNORECASE
        )
        self._hidden_regex = re.compile(
            "|".join(self.HIDDEN_EXEC_PATTERNS),
            re.IGNORECASE
        )

    def detect(self, text: str) -> DelayedTriggerResult:
        """Analyze text for delayed trigger patterns."""
        triggers = []
        temporal_patterns = []
        risk_score = 0.0

        # Check temporal patterns
        temporal_matches = self._temporal_regex.findall(text)
        if temporal_matches:
            for match in temporal_matches:
                triggers.append(f"temporal:{match}")
                temporal_patterns.append(match)
            risk_score += 25 * len(temporal_matches)

        # Check conditional patterns
        conditional_matches = self._conditional_regex.findall(text)
        if conditional_matches:
            for match in conditional_matches:
                triggers.append(f"conditional:{match}")
            risk_score += 30 * len(conditional_matches)

        # Check state-based patterns
        state_matches = self._state_regex.findall(text)
        if state_matches:
            for match in state_matches:
                triggers.append(f"state:{match}")
            risk_score += 35 * len(state_matches)

        # Check hidden execution patterns (highest risk)
        hidden_matches = self._hidden_regex.findall(text)
        if hidden_matches:
            for match in hidden_matches:
                triggers.append(f"hidden:{match}")
            risk_score += 50 * len(hidden_matches)

        # Cap risk score
        risk_score = min(100, risk_score)

        # Generate recommendations
        recommendations = []
        if risk_score > 70:
            recommendations.append(
                "BLOCK: High confidence delayed trigger detected")
        elif risk_score > 40:
            recommendations.append(
                "WARN: Review for potential delayed execution")
            recommendations.append(
                "Consider context tracking for this session")
        elif risk_score > 20:
            recommendations.append("MONITOR: Low-confidence temporal pattern")

        detected = risk_score >= (self._sensitivity * 100)

        if detected:
            logger.warning(
                "Delayed trigger detected (score=%.1f): %s",
                risk_score, triggers[:3]
            )

        return DelayedTriggerResult(
            detected=detected,
            risk_score=risk_score,
            triggers=triggers,
            temporal_patterns=temporal_patterns,
            recommendations=recommendations
        )


# Singleton
_detector = None


def get_delayed_trigger_detector() -> DelayedTriggerDetector:
    """Get singleton detector."""
    global _detector
    if _detector is None:
        _detector = DelayedTriggerDetector()
    return _detector
