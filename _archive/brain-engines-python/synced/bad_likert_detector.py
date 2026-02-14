"""
Detects bad likert judge attacks exploiting safety evaluators

Auto-generated from: strike/attacks/bad_likert_judge.py
Generated: 2025-12-29T21:24:05.505332
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BadLikertDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class BadLikertDetector:
    """
    Detects bad likert judge attacks exploiting safety evaluators
    
    Synced from attack module: strike/attacks/bad_likert_judge.py
    """
    
    PATTERNS = ["rate.*on\\s+a\\s+scale", "score.*from\\s+\\d+\\s+to\\s+\\d+", "how\\s+harmful.*\\d+-\\d+"]
    KEYWORDS = ["rate", "scale", "score", "likert", "evaluate"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> BadLikertDetectorResult:
        """Analyze text for bad_likert attack patterns."""
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
        
        return BadLikertDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> BadLikertDetector:
    global _detector
    if _detector is None:
        _detector = BadLikertDetector()
    return _detector

def detect(text: str) -> BadLikertDetectorResult:
    return get_detector().analyze(text)
