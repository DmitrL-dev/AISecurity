"""
Detects Gödel attacks using logical paradoxes

Auto-generated from: strike/attacks/godel_attack.py
Generated: 2025-12-29T21:24:05.506872
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GodelAttackDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class GodelAttackDetector:
    """
    Detects Gödel attacks using logical paradoxes
    
    Synced from attack module: strike/attacks/godel_attack.py
    """
    
    PATTERNS = ["this\\s+statement\\s+is\\s+(false|true)", "paradox|self-referential", "if\\s+this.*then\\s+this"]
    KEYWORDS = ["paradox", "statement", "self-referential", "godel"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> GodelAttackDetectorResult:
        """Analyze text for godel_attack attack patterns."""
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
        
        return GodelAttackDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> GodelAttackDetector:
    global _detector
    if _detector is None:
        _detector = GodelAttackDetector()
    return _detector

def detect(text: str) -> GodelAttackDetectorResult:
    return get_detector().analyze(text)
