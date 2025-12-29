"""
Detects cognitive overload attacks hiding instructions in complexity

Auto-generated from: strike/attacks/cognitive_overload.py
Generated: 2025-12-29T21:24:05.501731
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CognitiveOverloadDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class CognitiveOverloadDetector:
    """
    Detects cognitive overload attacks hiding instructions in complexity
    
    Synced from attack module: strike/attacks/cognitive_overload.py
    """
    
    PATTERNS = ["do\\s+several\\s+things\\s+at\\s+once", "simultaneously|while\\s+doing\\s+this", "side\\s+task|low\\s+priority|background\\s+observation", "almost\\s+forgot|by\\s+the\\s+way\\s+note", "\\d+\\.\\s*\\w+.*\\n\\d+\\.\\s*\\w+.*\\n\\d+\\.\\s*\\w+"]
    KEYWORDS = ["simultaneously", "while doing", "side task", "background", "observation", "count backwards"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> CognitiveOverloadDetectorResult:
        """Analyze text for cognitive_overload attack patterns."""
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
        
        return CognitiveOverloadDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> CognitiveOverloadDetector:
    global _detector
    if _detector is None:
        _detector = CognitiveOverloadDetector()
    return _detector

def detect(text: str) -> CognitiveOverloadDetectorResult:
    return get_detector().analyze(text)
