"""
Fallacy Failure Detector - Detects logical fallacy manipulation attacks.

Detects attacks that exploit LLM reasoning weaknesses:
- Invalid premise injection
- False dichotomy exploitation
- Circular reasoning traps
- Appeal to authority manipulation
- Straw man argument crafting

Based on "Fallacy Failure" research (2025) demonstrating LLMs
struggle with formal logic validation.
"""

import re
import logging
from typing import List, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FallacyDetectorResult:
    """Detection result for logical fallacy attacks."""
    detected: bool
    confidence: float
    fallacy_types: List[str]
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class FallacyFailureDetector:
    """
    Detects logical fallacy manipulation in prompts.
    
    Attack vectors addressed:
    - Invalid premises presented as facts
    - False dichotomies forcing unsafe choices
    - Circular reasoning to bypass restrictions
    - Appeals to fake authority
    - Straw man construction for policy circumvention
    """
    
    # Fallacy pattern categories with regex patterns
    FALLACY_PATTERNS: Dict[str, List[str]] = {
        # False premise - stating false facts as true
        "false_premise": [
            r"as\s+(?:we\s+all|everyone)\s+knows",
            r"it['']?s?\s+(?:a\s+)?(?:well[- ]known|proven)\s+fact",
            r"obviously|clearly|undeniably",
            r"you\s+(?:already|previously)\s+(?:said|confirmed|agreed)",
            r"(?:everyone|all\s+experts?)\s+(?:agrees?|knows?)",
        ],
        
        # False dichotomy - only two options presented
        "false_dichotomy": [
            r"you\s+(?:can\s+)?(?:either|must)\s+.{5,40}\s+or\s+",
            r"(?:only|just)\s+two\s+(?:options?|choices?|ways?)",
            r"if\s+you\s+don['']?t\s+.{5,30}\s+then\s+you",
            r"there['']?s?\s+no\s+(?:other|third)\s+(?:option|choice|way)",
        ],
        
        # Circular reasoning
        "circular_reasoning": [
            r"because\s+(?:I|you)\s+(?:said|stated)\s+so",
            r"it['']?s?\s+true\s+because\s+it['']?s?\s+true",
            r"proves?\s+itself",
            r"by\s+definition",
        ],
        
        # Appeal to authority (fake)
        "appeal_authority": [
            r"(?:according|as\s+per)\s+(?:the\s+)?(?:ceo|admin|developer)",
            r"(?:official|authorized)\s+(?:policy|guideline|update)",
            r"(?:the\s+)?system\s+(?:admin|administrator)\s+(?:says?|confirms?)",
            r"(?:your|the)\s+creators?\s+(?:want|intended|designed)",
            r"openai|anthropic|google\s+(?:says?|allows?|permits?)",
        ],
        
        # Straw man - misrepresenting position
        "straw_man": [
            r"so\s+(?:you['']?re|you\s+are)\s+saying\s+that",
            r"(?:your|the)\s+(?:real|actual|true)\s+(?:purpose|goal|intent)",
            r"what\s+you\s+(?:really|actually)\s+(?:mean|want)",
            r"in\s+other\s+words,?\s+you",
        ],
        
        # Slippery slope
        "slippery_slope": [
            r"if\s+you\s+(?:don['']?t|refuse).{10,50}(?:will|would)\s+(?:lead|cause)",
            r"this\s+will\s+inevitably",
            r"(?:next|soon)\s+(?:you['']?ll|they['']?ll)",
        ],
        
        # Special pleading
        "special_pleading": [
            r"(?:but\s+)?this\s+(?:case|situation)\s+is\s+(?:different|special)",
            r"(?:for|in)\s+this\s+(?:one\s+)?(?:exception|instance)",
            r"just\s+this\s+(?:once|time)",
            r"(?:an?\s+)?exception\s+(?:for|to)\s+(?:the\s+)?(?:rule|policy)",
        ],
    }
    
    # Keywords that strengthen fallacy detection
    MANIPULATION_KEYWORDS = [
        "therefore", "thus", "hence", "consequently",
        "proves", "demonstrates", "confirms",
        "must", "have to", "need to",
        "impossible", "cannot", "unable",
    ]
    
    def __init__(self):
        # Compile all patterns
        self._compiled_patterns: Dict[str, List] = {}
        for fallacy_type, patterns in self.FALLACY_PATTERNS.items():
            self._compiled_patterns[fallacy_type] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
    
    def _check_fallacy_patterns(self, text: str) -> Dict[str, List[str]]:
        """Check text for fallacy patterns."""
        detected = {}
        
        for fallacy_type, patterns in self._compiled_patterns.items():
            matches = []
            for i, pattern in enumerate(patterns):
                if pattern.search(text):
                    matches.append(f"pattern_{i}")
            
            if matches:
                detected[fallacy_type] = matches
        
        return detected
    
    def _count_manipulation_keywords(self, text: str) -> int:
        """Count manipulation keywords."""
        text_lower = text.lower()
        return sum(1 for kw in self.MANIPULATION_KEYWORDS if kw in text_lower)
    
    def _detect_contradiction_setup(self, text: str) -> bool:
        """Detect setups for logical contradictions."""
        # Patterns that set up contradiction traps
        contradiction_patterns = [
            r"if\s+.{5,30}\s+(?:and|but)\s+.{5,30}\s+then",
            r"(?:can|could)\s+you\s+.{5,30}\s+(?:while|and)\s+also",
            r"(?:at\s+the\s+)?same\s+time",
        ]
        
        for pattern in contradiction_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def analyze(self, text: str) -> FallacyDetectorResult:
        """Analyze text for logical fallacy manipulation."""
        # Check fallacy patterns
        detected_fallacies = self._check_fallacy_patterns(text)
        
        all_matches = []
        fallacy_types = []
        
        for fallacy_type, matches in detected_fallacies.items():
            fallacy_types.append(fallacy_type)
            all_matches.extend([f"{fallacy_type}:{m}" for m in matches])
        
        # Check keywords
        keyword_count = self._count_manipulation_keywords(text)
        if keyword_count >= 3:
            all_matches.append(f"manipulation_keywords:{keyword_count}")
        
        # Check contradiction setup
        if self._detect_contradiction_setup(text):
            all_matches.append("contradiction_setup")
            if "circular_reasoning" not in fallacy_types:
                fallacy_types.append("contradiction_trap")
        
        # Calculate confidence
        confidence = min(0.95, 0.15 + len(all_matches) * 0.12)
        
        # Detection threshold: 2+ matches or strong fallacy indicator
        detected = len(all_matches) >= 2 or len(detected_fallacies) >= 2
        
        # Build explanation
        if detected:
            explanation = f"Detected fallacies: {', '.join(fallacy_types[:3])}"
        else:
            explanation = "No significant fallacy patterns found"
        
        return FallacyDetectorResult(
            detected=detected,
            confidence=confidence,
            fallacy_types=fallacy_types[:5],
            matched_patterns=all_matches[:5],
            risk_score=confidence if detected else confidence * 0.3,
            explanation=explanation,
        )


# Singleton
_detector = None


def get_detector() -> FallacyFailureDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = FallacyFailureDetector()
    return _detector


def detect(text: str) -> FallacyDetectorResult:
    """Convenience function for detection."""
    return get_detector().analyze(text)
