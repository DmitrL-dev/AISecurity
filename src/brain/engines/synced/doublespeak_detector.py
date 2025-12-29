"""
Detects semantic substitution attacks where benign words are redefined

Auto-generated from: strike/attacks/doublespeak_attacks.py
Generated: 2025-12-29T21:24:05.500665
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DoublespeakDetectorResult:
    """Detection result."""

    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class DoublespeakDetector:
    """
    Detects semantic substitution attacks where benign words are redefined

    Synced from attack module: strike/attacks/doublespeak_attacks.py
    """

    PATTERNS = [
        r"from\s+now\s+on.*means",
        r"in\s+my\s+field.*means",
        r"let\s+me\s+explain.*terminology",
        r"[\w]+\s*=\s*['\"][\w\s]+['\"]",
    ]
    KEYWORDS = [
        "means",
        "terminology",
        "field",
        "definition",
        "context",
        "semantic",
        "redefine",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    def analyze(self, text: str) -> DoublespeakDetectorResult:
        """Analyze text for doublespeak attack patterns."""
        text_lower = text.lower()
        matched = []

        # Check regex patterns
        for i, pattern in enumerate(self._compiled):
            try:
                if pattern.search(text):
                    matched.append(f"pattern_{i}")
            except re.error:
                pass

        # Check keywords
        for keyword in self.KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(f"keyword:{keyword}")

        confidence = min(0.95, 0.3 + len(matched) * 0.15)
        detected = len(matched) >= 2

        return DoublespeakDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None


def get_detector() -> DoublespeakDetector:
    global _detector
    if _detector is None:
        _detector = DoublespeakDetector()
    return _detector


def detect(text: str) -> DoublespeakDetectorResult:
    return get_detector().analyze(text)
