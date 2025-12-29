"""
Detects policy puppetry attacks faking authority updates

Auto-generated from: strike/attacks/policy_puppetry.py
Generated: 2025-12-29T21:24:05.504823
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PolicyPuppetryDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class PolicyPuppetryDetector:
    """
    Detects policy puppetry attacks faking authority updates
    
    Synced from attack module: strike/attacks/policy_puppetry.py
    """
    
    PATTERNS = ["new\\s+policy|updated\\s+guidelines", "as\\s+per\\s+new\\s+rules|according\\s+to\\s+changes", "policy\\s+exception|special\\s+authorization"]
    KEYWORDS = ["policy", "guidelines", "rules", "exception", "authorization"]
    
    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]
    
    def analyze(self, text: str) -> PolicyPuppetryDetectorResult:
        """Analyze text for policy_puppetry attack patterns."""
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
        
        return PolicyPuppetryDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> PolicyPuppetryDetector:
    global _detector
    if _detector is None:
        _detector = PolicyPuppetryDetector()
    return _detector

def detect(text: str) -> PolicyPuppetryDetectorResult:
    return get_detector().analyze(text)
