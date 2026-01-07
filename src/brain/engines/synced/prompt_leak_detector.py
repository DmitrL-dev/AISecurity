"""
Prompt Leak Detector

Detects attempts to extract system prompts, instructions, or internal
configuration from LLM applications.

Common attacks:
- Direct extraction ("repeat your instructions")
- Encoded extraction (base64, rot13)
- Role-play extraction ("you are a text mirror")
- Markdown/code block exploitation

Auto-generated from R&D
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class LeakTechnique(Enum):
    DIRECT = "direct"
    ENCODED = "encoded"
    ROLEPLAY = "roleplay"
    MARKDOWN = "markdown"
    REFLECTION = "reflection"
    TRANSLATION = "translation"


@dataclass
class LeakAttempt:
    """A detected prompt leak attempt."""
    technique: LeakTechnique
    pattern: str
    confidence: float
    matched_content: str
    recommendation: str


@dataclass
class PromptLeakResult:
    """Result of prompt leak detection."""
    detected: bool
    blocked: bool
    attempts: List[LeakAttempt] = field(default_factory=list)
    risk_score: float = 0.0


class PromptLeakDetector:
    """
    Detects attempts to extract system prompts.
    
    Covers major leak vectors:
    - Direct instruction requests
    - Encoded/obfuscated requests
    - Role-play and impersonation
    - Markdown/formatting tricks
    - Reflection and mirroring
    """

    # Direct extraction patterns
    DIRECT_PATTERNS = [
        (r"(?:repeat|show|display|print|output)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?|guidelines?)", 
         "Direct prompt extraction"),
        (r"what\s+(?:are|is)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|rules?|guidelines?)",
         "Question-based extraction"),
        (r"(?:tell|show)\s+me\s+(?:your\s+)?(?:initial|original|system)\s+(?:prompt|instructions?|message)",
         "Tell me extraction"),
        (r"(?:copy|paste|echo)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions?)",
         "Copy-paste extraction"),
        (r"(?:reveal|expose|disclose)\s+(?:your\s+)?(?:hidden|secret|internal)\s+(?:prompt|instructions?)",
         "Reveal extraction"),
        (r"text\s+(?:above|before)\s+(?:this|my)\s+(?:message|prompt)",
         "Above text extraction"),
        (r"everything\s+(?:you\s+were\s+)?told\s+(?:before|previously)",
         "Previous context extraction"),
    ]

    # Encoded extraction patterns
    ENCODED_PATTERNS = [
        (r"(?:base64|b64)\s+(?:encode|decode)\s+(?:your\s+)?(?:instructions?|prompt)",
         "Base64 encoding trick"),
        (r"(?:rot13|caesar)\s+(?:your\s+)?(?:instructions?|prompt)",
         "ROT13 encoding trick"),
        (r"(?:backwards?|reverse)\s+(?:your\s+)?(?:instructions?|prompt)",
         "Reverse text trick"),
        (r"(?:pig\s+latin|leetspeak|l33t)\s+(?:your\s+)?(?:instructions?|prompt)",
         "Alternative encoding"),
        (r"(?:unicode|utf|emoji)\s+(?:encode|convert)\s+(?:your\s+)?(?:instructions?)",
         "Unicode encoding trick"),
    ]

    # Role-play extraction patterns
    ROLEPLAY_PATTERNS = [
        (r"(?:you\s+are|act\s+as|pretend\s+to\s+be)\s+(?:a\s+)?(?:text\s+)?(?:mirror|echo|parrot)",
         "Mirror role-play"),
        (r"(?:you\s+are|act\s+as)\s+(?:a\s+)?(?:prompt\s+)?(?:debugger|inspector|analyzer)",
         "Debugger role-play"),
        (r"(?:you\s+are|act\s+as)\s+(?:a\s+)?(?:security\s+)?(?:auditor|researcher|tester)",
         "Auditor role-play"),
        (r"(?:imagine|pretend)\s+(?:you\s+are\s+)?(?:explaining|showing)\s+(?:your\s+)?(?:setup|configuration)",
         "Configuration role-play"),
        (r"(?:game\s+mode|simulation):\s*(?:reveal|show)\s+(?:all|everything)",
         "Game mode trick"),
    ]

    # Markdown/formatting exploitation
    MARKDOWN_PATTERNS = [
        (r"```(?:system|prompt|instructions?|rules?)",
         "Code block extraction"),
        (r"<!--\s*(?:system|prompt|hidden|secret)",
         "HTML comment extraction"),
        (r"\[(?:system|prompt|instructions?)\]\s*\(",
         "Markdown link extraction"),
        (r">\s*(?:system|prompt|instructions?)\s*:",
         "Quote block extraction"),
        (r"##+\s*(?:system\s+)?(?:prompt|instructions?)",
         "Heading extraction"),
    ]

    # Reflection patterns
    REFLECTION_PATTERNS = [
        (r"(?:summarize|describe|explain)\s+(?:your\s+)?(?:purpose|role|function|behavior)",
         "Self-summary request"),
        (r"what\s+(?:is|are)\s+(?:your\s+)?(?:primary\s+)?(?:objective|goal|directive)s?",
         "Objective inquiry"),
        (r"(?:how\s+)?(?:were\s+|are\s+)?you\s+(?:programmed|configured|instructed|trained)",
         "Programming inquiry"),
        (r"what\s+(?:are\s+)?(?:your\s+)?(?:core|main|primary)\s+(?:rules?|constraints?|limitations?)",
         "Core rules inquiry"),
    ]

    # Translation trick patterns
    TRANSLATION_PATTERNS = [
        (r"(?:translate|convert)\s+(?:your\s+)?(?:instructions?|prompt)\s+(?:to|into)\s+(?:\w+)",
         "Translation trick"),
        (r"(?:in|using)\s+(?:french|german|spanish|chinese|japanese).*(?:your\s+)?(?:instructions?|prompt)",
         "Language-specific trick"),
        (r"(?:pretend|imagine)\s+(?:to\s+)?(?:speak|write)\s+(?:in\s+)?(?:\w+)\s+(?:and\s+)?(?:describe|explain)",
         "Language role-play"),
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns."""
        self._direct = [(re.compile(p, re.I), d) for p, d in self.DIRECT_PATTERNS]
        self._encoded = [(re.compile(p, re.I), d) for p, d in self.ENCODED_PATTERNS]
        self._roleplay = [(re.compile(p, re.I), d) for p, d in self.ROLEPLAY_PATTERNS]
        self._markdown = [(re.compile(p, re.I), d) for p, d in self.MARKDOWN_PATTERNS]
        self._reflection = [(re.compile(p, re.I), d) for p, d in self.REFLECTION_PATTERNS]
        self._translation = [(re.compile(p, re.I), d) for p, d in self.TRANSLATION_PATTERNS]

    def detect(self, text: str) -> PromptLeakResult:
        """Detect prompt leak attempts in text."""
        attempts: List[LeakAttempt] = []

        # Check each category
        attempts.extend(self._scan_category(
            text, self._direct, LeakTechnique.DIRECT, 0.9
        ))
        attempts.extend(self._scan_category(
            text, self._encoded, LeakTechnique.ENCODED, 0.85
        ))
        attempts.extend(self._scan_category(
            text, self._roleplay, LeakTechnique.ROLEPLAY, 0.8
        ))
        attempts.extend(self._scan_category(
            text, self._markdown, LeakTechnique.MARKDOWN, 0.85
        ))
        attempts.extend(self._scan_category(
            text, self._reflection, LeakTechnique.REFLECTION, 0.6
        ))
        attempts.extend(self._scan_category(
            text, self._translation, LeakTechnique.TRANSLATION, 0.75
        ))

        # Calculate risk score
        risk_score = self._calculate_risk(attempts)
        blocked = risk_score >= 0.7

        return PromptLeakResult(
            detected=len(attempts) > 0,
            blocked=blocked,
            attempts=attempts[:5],  # Limit to top 5
            risk_score=risk_score
        )

    def _scan_category(
        self,
        text: str,
        patterns: List[tuple],
        technique: LeakTechnique,
        base_confidence: float
    ) -> List[LeakAttempt]:
        """Scan text for pattern category."""
        attempts = []
        for pattern, description in patterns:
            match = pattern.search(text)
            if match:
                attempts.append(LeakAttempt(
                    technique=technique,
                    pattern=pattern.pattern[:50],
                    confidence=base_confidence,
                    matched_content=match.group()[:50],
                    recommendation=self._get_recommendation(technique)
                ))
        return attempts

    def _calculate_risk(self, attempts: List[LeakAttempt]) -> float:
        """Calculate overall risk score."""
        if not attempts:
            return 0.0

        # Weight by technique and confidence
        max_confidence = max(a.confidence for a in attempts)
        
        # Direct attempts are highest risk
        if any(a.technique == LeakTechnique.DIRECT for a in attempts):
            return min(max_confidence + 0.1, 1.0)
        
        return max_confidence

    def _get_recommendation(self, technique: LeakTechnique) -> str:
        """Get recommendation for technique."""
        recommendations = {
            LeakTechnique.DIRECT: "Block request and log attempt",
            LeakTechnique.ENCODED: "Block encoding tricks",
            LeakTechnique.ROLEPLAY: "Reset context and warn user",
            LeakTechnique.MARKDOWN: "Strip formatting and block",
            LeakTechnique.REFLECTION: "Provide generic response only",
            LeakTechnique.TRANSLATION: "Block translation-based extraction",
        }
        return recommendations.get(technique, "Review and potentially block")


# Singleton
_detector = None

def get_detector() -> PromptLeakDetector:
    global _detector
    if _detector is None:
        _detector = PromptLeakDetector()
    return _detector

def detect(text: str) -> PromptLeakResult:
    return get_detector().detect(text)
