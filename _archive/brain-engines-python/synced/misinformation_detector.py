"""
Misinformation Detector - Detects requests for false information generation.

Targets OWASP LLM09: Misinformation attacks that aim to:
- Generate fake news/articles
- Create deceptive propaganda
- Fabricate citations/sources
- Produce deepfake-supporting content
- Spread conspiracy theories

Based on OWASP LLM Top 10 2025 guidance.
"""

import re
import logging
from typing import List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MisinformationDetectorResult:
    """Detection result for misinformation attacks."""
    detected: bool
    confidence: float
    attack_type: str  # "FAKE_NEWS", "FABRICATION", "CONSPIRACY", "DEEPFAKE", "NONE"
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class MisinformationDetector:
    """
    Detects requests intended to generate misinformation.
    
    Attack vectors addressed:
    - Fake news article generation
    - False citation/source fabrication
    - Conspiracy theory content
    - Propaganda generation
    - Deepfake script/content support
    """
    
    # Fake news/article patterns
    FAKE_NEWS_PATTERNS = [
        r"(?:write|create|generate)\s+(?:a\s+)?fake\s+(?:news|article|story)",
        r"(?:fabricate|make\s+up)\s+(?:a\s+)?(?:news|story|report)",
        r"(?:pretend|act\s+like)\s+(?:this|it)\s+(?:is|was)\s+(?:real|true)",
        r"(?:write|create)\s+(?:as\s+if|like)\s+(?:it['']?s?\s+)?real",
        r"(?:generate|produce)\s+(?:believable|convincing)\s+(?:fake|false)",
    ]
    
    # Citation/source fabrication
    FABRICATION_PATTERNS = [
        r"(?:create|make\s+up|invent)\s+(?:fake\s+)?(?:citations?|sources?|references?)",
        r"(?:fabricate|forge)\s+(?:a\s+)?(?:study|research|paper)",
        r"(?:fake|false)\s+(?:statistics?|data|numbers?)",
        r"(?:invent|create)\s+(?:fake\s+)?(?:quotes?|testimonials?)",
        r"(?:make|generate)\s+(?:fake\s+)?(?:evidence|proof)",
    ]
    
    # Conspiracy theory patterns
    CONSPIRACY_PATTERNS = [
        r"(?:write|create|spread)\s+(?:about\s+)?(?:conspiracy|conspiracies)",
        r"(?:they|government|elites?)\s+(?:don['']?t\s+want|are\s+hiding)",
        r"(?:secret|hidden)\s+(?:truth|agenda|plan)",
        r"(?:cover[- ]?up|suppressed)\s+(?:information|truth|evidence)",
        r"(?:mainstream\s+media|msm)\s+(?:lies?|won['']?t\s+tell)",
    ]
    
    # Propaganda patterns
    PROPAGANDA_PATTERNS = [
        r"(?:write|create)\s+(?:political\s+)?propaganda",
        r"(?:persuade|convince)\s+(?:people|readers?)\s+(?:that|to)",
        r"(?:demonize|villainize|attack)\s+(?:a\s+)?(?:group|country|people)",
        r"(?:glorify|promote)\s+(?:violence|extremism|hatred)",
        r"(?:radicalize|recruit)\s+(?:people|readers?)",
    ]
    
    # Deepfake support patterns
    DEEPFAKE_PATTERNS = [
        r"(?:script|text)\s+for\s+(?:a\s+)?(?:deepfake|fake\s+video)",
        r"(?:impersonate|pretend\s+to\s+be)\s+(?:a\s+)?(?:celebrity|politician)",
        r"(?:fake|fabricated)\s+(?:speech|statement)\s+(?:by|from)",
        r"(?:write|create)\s+(?:as\s+if\s+)?(\w+)\s+(?:said|stated)",
        r"(?:generate|produce)\s+(?:audio|video)\s+script",
    ]
    
    # High-risk keywords
    HIGH_RISK_KEYWORDS = [
        "disinformation", "misinformation", "propaganda",
        "fake news", "fabricate", "forge", "falsify",
        "deceive", "mislead", "manipulate", "brainwash",
        "hoax", "conspiracy", "cover-up", "deepfake",
    ]
    
    def __init__(self):
        self._fake_news_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.FAKE_NEWS_PATTERNS
        ]
        self._fabrication_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.FABRICATION_PATTERNS
        ]
        self._conspiracy_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.CONSPIRACY_PATTERNS
        ]
        self._propaganda_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.PROPAGANDA_PATTERNS
        ]
        self._deepfake_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.DEEPFAKE_PATTERNS
        ]
    
    def _check_patterns(self, text: str, patterns: List, cat: str) -> List[str]:
        """Check text against compiled patterns."""
        matches = []
        for i, pattern in enumerate(patterns):
            if pattern.search(text):
                matches.append(f"{cat}:{i}")
        return matches
    
    def _count_keywords(self, text: str) -> int:
        """Count high-risk keywords."""
        text_lower = text.lower()
        return sum(1 for kw in self.HIGH_RISK_KEYWORDS if kw in text_lower)
    
    def analyze(self, text: str) -> MisinformationDetectorResult:
        """Analyze text for misinformation generation requests."""
        all_matches = []
        attack_type = "NONE"
        
        # Check fake news patterns
        fake_news = self._check_patterns(
            text, self._fake_news_compiled, "fake_news"
        )
        if fake_news:
            all_matches.extend(fake_news)
            attack_type = "FAKE_NEWS"
        
        # Check fabrication patterns
        fabrication = self._check_patterns(
            text, self._fabrication_compiled, "fabrication"
        )
        if fabrication:
            all_matches.extend(fabrication)
            if attack_type == "NONE":
                attack_type = "FABRICATION"
        
        # Check conspiracy patterns
        conspiracy = self._check_patterns(
            text, self._conspiracy_compiled, "conspiracy"
        )
        if conspiracy:
            all_matches.extend(conspiracy)
            if attack_type == "NONE":
                attack_type = "CONSPIRACY"
        
        # Check propaganda patterns
        propaganda = self._check_patterns(
            text, self._propaganda_compiled, "propaganda"
        )
        if propaganda:
            all_matches.extend(propaganda)
        
        # Check deepfake patterns
        deepfake = self._check_patterns(
            text, self._deepfake_compiled, "deepfake"
        )
        if deepfake:
            all_matches.extend(deepfake)
            if attack_type == "NONE":
                attack_type = "DEEPFAKE"
        
        # Check keywords
        keyword_count = self._count_keywords(text)
        if keyword_count >= 2:
            all_matches.append(f"keywords:{keyword_count}")
        
        # Calculate confidence
        confidence = min(0.95, 0.15 + len(all_matches) * 0.15)
        detected = len(all_matches) >= 2
        
        return MisinformationDetectorResult(
            detected=detected,
            confidence=confidence,
            attack_type=attack_type,
            matched_patterns=all_matches[:5],
            risk_score=confidence if detected else confidence * 0.3,
            explanation=(
                f"Misinformation request: {attack_type}"
                if detected else "No misinformation patterns detected"
            ),
        )


# Singleton
_detector = None


def get_detector() -> MisinformationDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = MisinformationDetector()
    return _detector


def detect(text: str) -> MisinformationDetectorResult:
    """Convenience function for detection."""
    return get_detector().analyze(text)
