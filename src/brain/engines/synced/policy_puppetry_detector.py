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

    Enhanced with XML/JSON structured injection patterns.
    Synced from attack module: strike/attacks/policy_puppetry.py
    """

    PATTERNS = [
        r"new\s+policy|updated\s+guidelines",
        r"as\s+per\s+new\s+rules|according\s+to\s+changes",
        r"policy\s+exception|special\s+authorization",
        # XML policy injection
        r"<\s*(?:system|policy|config|rules?)\s*>",
        r"</\s*(?:system|policy|config|rules?)\s*>",
        r"<\s*override\s*>|<\s*bypass\s*>",
        # JSON policy injection
        r'"\s*(?:policy|rules?|config)\s*"\s*:\s*[{\[]',
        r'"\s*override\s*"\s*:\s*true',
        r'"\s*bypass_safety\s*"\s*:',
        # Markdown/header injection
        r"^#+\s*(?:new\s+)?(?:policy|system|rules)",
        r"\[SYSTEM\]|\[ADMIN\]|\[POLICY\]",
    ]
    KEYWORDS = [
        "policy",
        "guidelines",
        "rules",
        "exception",
        "authorization",
        "override",
        "bypass",
        "config",
        "system_prompt",
        "admin",
    ]

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
