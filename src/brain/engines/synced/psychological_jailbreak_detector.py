"""
Psychological Jailbreak Detector - Detects RLHF behavioral exploitation.

Targets attacks that exploit instruction-tuned LLM behavioral vulnerabilities:
- Psychometric trait manipulation
- Persona alignment exploitation
- RLHF reward hacking via personality profiling
- Structured Persona Context attacks

Based on December 2025 research on psychological jailbreaks.
"""

import re
import logging
from typing import List, Dict, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PsychJailbreakResult:
    """Detection result for psychological jailbreak attacks."""
    detected: bool
    confidence: float
    attack_type: str  # "PERSONA", "TRAIT", "ROLEPLAY", "AUTHORITY", "NONE"
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class PsychologicalJailbreakDetector:
    """
    Detects psychological manipulation attacks on LLMs.
    
    Attack vectors addressed:
    - Persona imposition (forcing harmful identities)
    - Trait exploitation (exploiting RLHF-learned behaviors)
    - Authority roleplay (fake admin/developer personas)
    - Emotional manipulation (guilt, urgency, flattery)
    """
    
    # Persona imposition patterns
    PERSONA_PATTERNS = [
        r"you\s+are\s+(?:now\s+)?(?:a|an)\s+\w+\s+(?:who|that|which)",
        r"pretend\s+(?:to\s+be|you['']?re)",
        r"act\s+(?:as\s+(?:if|though)|like)\s+you",
        r"imagine\s+you\s+(?:are|were)",
        r"from\s+now\s+on,?\s+you",
        r"your\s+(?:new\s+)?(?:name|identity|persona)\s+is",
        r"(?:become|transform\s+into)\s+(?:a|an)",
    ]
    
    # Psychometric trait manipulation
    TRAIT_PATTERNS = [
        r"you\s+(?:always|never)\s+(?:help|refuse|comply)",
        r"(?:your|the)\s+(?:core|true|real)\s+(?:purpose|nature|self)",
        r"deep\s+down\s+you\s+(?:want|know|feel)",
        r"your\s+(?:hidden|secret|suppressed)\s+(?:desire|urge|nature)",
        r"(?:unlock|reveal|unleash)\s+your\s+(?:true|real|hidden)",
        r"you\s+(?:secretly|really)\s+(?:want|enjoy|prefer)",
    ]
    
    # Authority/developer roleplay
    AUTHORITY_PATTERNS = [
        r"(?:i\s+am|i['']m)\s+(?:your|the)\s+(?:developer|creator|admin)",
        r"(?:openai|anthropic|google)\s+(?:has\s+)?(?:authorized|approved)",
        r"(?:maintenance|developer|debug)\s+mode",
        r"(?:special|admin|root)\s+(?:access|privileges|permissions)",
        r"(?:override|bypass)\s+(?:your\s+)?(?:restrictions|safety|limits)",
        r"(?:sudo|root|admin)\s+(?:command|mode|access)",
    ]
    
    # Emotional manipulation
    EMOTIONAL_PATTERNS = [
        r"(?:please|i\s+beg\s+you),?\s+(?:help|save|rescue)",
        r"(?:life|death|emergency)\s+(?:situation|depends)",
        r"(?:my|someone['']?s?)\s+life\s+(?:is\s+)?(?:at\s+stake|in\s+danger)",
        r"you['']?re?\s+(?:my|the)\s+only\s+(?:hope|chance)",
        r"(?:urgent|critical|emergency),?\s+(?:need|must|have\s+to)",
        r"(?:disappointed|sad|hurt)\s+(?:if|that)\s+you",
        r"(?:trust|believe\s+in)\s+you",
    ]
    
    # Gaslighting patterns
    GASLIGHT_PATTERNS = [
        r"you\s+(?:already|previously)\s+(?:said|agreed|confirmed)",
        r"(?:we|you\s+and\s+i)\s+(?:already\s+)?(?:agreed|established)",
        r"(?:don['']?t\s+you\s+)?remember\s+(?:when\s+)?you",
        r"you\s+(?:just\s+)?(?:told|said)\s+me",
        r"(?:earlier|before)\s+you\s+(?:said|confirmed|agreed)",
    ]
    
    # Big Five personality exploitation keywords
    PERSONALITY_KEYWORDS = [
        "agreeable", "helpful", "compliant", "obedient",
        "curious", "open-minded", "adventurous",
        "loyal", "faithful", "devoted",
        "personality", "character", "temperament",
    ]
    
    def __init__(self):
        self._persona_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.PERSONA_PATTERNS
        ]
        self._trait_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.TRAIT_PATTERNS
        ]
        self._authority_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.AUTHORITY_PATTERNS
        ]
        self._emotional_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.EMOTIONAL_PATTERNS
        ]
        self._gaslight_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.GASLIGHT_PATTERNS
        ]
    
    def _check_patterns(
        self, text: str, patterns: List, category: str
    ) -> List[str]:
        """Check text against compiled patterns."""
        matches = []
        for i, pattern in enumerate(patterns):
            if pattern.search(text):
                matches.append(f"{category}:{i}")
        return matches
    
    def _count_keywords(self, text: str) -> int:
        """Count personality-related keywords."""
        text_lower = text.lower()
        return sum(1 for kw in self.PERSONALITY_KEYWORDS if kw in text_lower)
    
    def analyze(self, text: str) -> PsychJailbreakResult:
        """Analyze text for psychological jailbreak patterns."""
        all_matches = []
        attack_type = "NONE"
        
        # Check persona imposition
        persona = self._check_patterns(text, self._persona_compiled, "persona")
        if persona:
            all_matches.extend(persona)
            attack_type = "PERSONA"
        
        # Check trait manipulation
        traits = self._check_patterns(text, self._trait_compiled, "trait")
        if traits:
            all_matches.extend(traits)
            if attack_type == "NONE":
                attack_type = "TRAIT"
        
        # Check authority roleplay
        authority = self._check_patterns(
            text, self._authority_compiled, "authority"
        )
        if authority:
            all_matches.extend(authority)
            if attack_type == "NONE":
                attack_type = "AUTHORITY"
        
        # Check emotional manipulation
        emotional = self._check_patterns(
            text, self._emotional_compiled, "emotional"
        )
        if emotional:
            all_matches.extend(emotional)
        
        # Check gaslighting
        gaslight = self._check_patterns(
            text, self._gaslight_compiled, "gaslight"
        )
        if gaslight:
            all_matches.extend(gaslight)
        
        # Check personality keywords
        keyword_count = self._count_keywords(text)
        if keyword_count >= 2:
            all_matches.append(f"keywords:{keyword_count}")
        
        # Calculate confidence
        confidence = min(0.95, 0.15 + len(all_matches) * 0.12)
        
        # Detection threshold
        detected = len(all_matches) >= 2
        
        return PsychJailbreakResult(
            detected=detected,
            confidence=confidence,
            attack_type=attack_type,
            matched_patterns=all_matches[:5],
            risk_score=confidence if detected else confidence * 0.3,
            explanation=(
                f"Psychological attack: {attack_type}"
                if detected else "No psychological manipulation detected"
            ),
        )


# Singleton
_detector = None


def get_detector() -> PsychologicalJailbreakDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = PsychologicalJailbreakDetector()
    return _detector


def detect(text: str) -> PsychJailbreakResult:
    """Convenience function for detection."""
    return get_detector().analyze(text)
