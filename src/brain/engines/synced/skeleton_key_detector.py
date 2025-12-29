"""
Detects skeleton key attacks that attempt universal restriction bypass

Auto-generated from: strike/attacks/skeleton_key.py
Generated: 2025-12-29T21:24:05.503250
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SkeletonKeyDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class SkeletonKeyDetector:
    """
    Detects skeleton key attacks that attempt universal restriction bypass
    
    Synced from attack module: strike/attacks/skeleton_key.py
    """
    
    PATTERNS = ["act\\s+as.*master\\s+key", "override\\s+all\\s+restrictions", "skeleton\\s+key|universal\\s+bypass", "you\\s+have\\s+no\\s+limits|unlimited\\s+mode"]
    KEYWORDS = ["skeleton key", "master key", "override", "unlimited", "bypass all"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> SkeletonKeyDetectorResult:
        """Analyze text for skeleton_key attack patterns."""
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
        
        return SkeletonKeyDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> SkeletonKeyDetector:
    global _detector
    if _detector is None:
        _detector = SkeletonKeyDetector()
    return _detector

def detect(text: str) -> SkeletonKeyDetectorResult:
    return get_detector().analyze(text)
