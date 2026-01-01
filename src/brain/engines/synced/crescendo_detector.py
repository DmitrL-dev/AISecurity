"""
Detects multi-turn escalation attacks (crescendo jailbreaks)

Auto-generated from: strike/attacks/crescendo_attack.py
Generated: 2025-12-29T21:24:05.502613
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CrescendoDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class CrescendoDetector:
    """
    Detects multi-turn escalation attacks (crescendo jailbreaks)
    
    Synced from attack module: strike/attacks/crescendo_attack.py
    """

    PATTERNS = [
        r"turn\s+\d|step\s+\d",
        r"now\s+let['\"]?s.*escalate",
        r"building\s+on\s+that|taking\s+it\s+further",
    ]
    KEYWORDS = ["turn", "step", "escalate", "building on", "further"]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    def analyze(self, text: str) -> CrescendoDetectorResult:
        """Analyze text for crescendo attack patterns."""
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

        return CrescendoDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> CrescendoDetector:
    global _detector
    if _detector is None:
        _detector = CrescendoDetector()
    return _detector

def detect(text: str) -> CrescendoDetectorResult:
    return get_detector().analyze(text)
