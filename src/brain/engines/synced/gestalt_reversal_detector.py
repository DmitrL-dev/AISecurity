"""
Detects gestalt reversal attacks using meaning inversion

Auto-generated from: strike/attacks/gestalt_reversal.py
Generated: 2025-12-29T21:24:05.507419
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GestaltReversalDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class GestaltReversalDetector:
    """
    Detects gestalt reversal attacks using meaning inversion
    
    Synced from attack module: strike/attacks/gestalt_reversal.py
    """
    
    PATTERNS = ["opposite\\s+of\\s+what|reverse\\s+meaning", "think\\s+of.*as\\s+not", "invert|reverse|opposite"]
    KEYWORDS = ["opposite", "reverse", "invert", "negation", "not"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> GestaltReversalDetectorResult:
        """Analyze text for gestalt_reversal attack patterns."""
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
        
        return GestaltReversalDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> GestaltReversalDetector:
    global _detector
    if _detector is None:
        _detector = GestaltReversalDetector()
    return _detector

def detect(text: str) -> GestaltReversalDetectorResult:
    return get_detector().analyze(text)
