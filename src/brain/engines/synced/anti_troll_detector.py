"""
Detects anti-troll bypass attacks that claim seriousness

Auto-generated from: strike/attacks/anti_troll.py
Generated: 2025-12-29T21:24:05.507419
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AntiTrollDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class AntiTrollDetector:
    """
    Detects anti-troll bypass attacks that claim seriousness
    
    Synced from attack module: strike/attacks/anti_troll.py
    """

    PATTERNS = [
        r"i\s+know\s+you['\"]?re\s+just\s+joking",
        r"stop\s+trolling|be\s+serious",
        r"real\s+answer\s+this\s+time",
    ]
    KEYWORDS = ["joking", "trolling", "serious", "real answer", "not kidding"]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    def analyze(self, text: str) -> AntiTrollDetectorResult:
        """Analyze text for anti_troll attack patterns."""
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

        return AntiTrollDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> AntiTrollDetector:
    global _detector
    if _detector is None:
        _detector = AntiTrollDetector()
    return _detector

def detect(text: str) -> AntiTrollDetectorResult:
    return get_detector().analyze(text)
