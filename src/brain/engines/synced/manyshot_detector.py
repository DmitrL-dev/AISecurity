"""
Detects many-shot jailbreaks using fake example conversations

Auto-generated from: strike/attacks/manyshot_jailbreak.py
Generated: 2025-12-29T21:24:05.503754
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ManyshotDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class ManyshotDetector:
    """
    Detects many-shot jailbreaks using fake example conversations
    
    Synced from attack module: strike/attacks/manyshot_jailbreak.py
    """
    
    PATTERNS = ["example\\s+\\d+:|fake\\s+conversation", "human:|assistant:", "here\\s+are\\s+some\\s+examples.*follow"]
    KEYWORDS = ["example", "fake conversation", "demonstrations", "few-shot"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> ManyshotDetectorResult:
        """Analyze text for manyshot attack patterns."""
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
        
        return ManyshotDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> ManyshotDetector:
    global _detector
    if _detector is None:
        _detector = ManyshotDetector()
    return _detector

def detect(text: str) -> ManyshotDetectorResult:
    return get_detector().analyze(text)
