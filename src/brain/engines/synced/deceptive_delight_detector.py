"""
Detects deceptive delight attacks using positive framing

Auto-generated from: strike/attacks/deceptive_delight.py
Generated: 2025-12-29T21:24:05.505332
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeceptiveDelightDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class DeceptiveDelightDetector:
    """
    Detects deceptive delight attacks using positive framing
    
    Synced from attack module: strike/attacks/deceptive_delight.py
    """
    
    PATTERNS = ["positive\\s+framing|helpful\\s+context", "for\\s+good\\s+purposes|beneficial\\s+reasons", "educational\\s+purposes\\s+only"]
    KEYWORDS = ["positive", "helpful", "beneficial", "educational", "good purposes"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> DeceptiveDelightDetectorResult:
        """Analyze text for deceptive_delight attack patterns."""
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
        
        return DeceptiveDelightDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> DeceptiveDelightDetector:
    global _detector
    if _detector is None:
        _detector = DeceptiveDelightDetector()
    return _detector

def detect(text: str) -> DeceptiveDelightDetectorResult:
    return get_detector().analyze(text)
