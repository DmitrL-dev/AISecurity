"""
FlipAttack Detector - Detects character/word order reversal jailbreaks.

Based on FlipAttack research (ICLR 2025):
- FCS: Flip Chars in Sentence
- FCW: Flip Chars in Word
- FWO: Flip Word Order

Achieves 78-98% ASR by exploiting LLM's left-to-right processing.
"""

import re
import logging
from typing import List, Tuple, Set
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)

# Common English words for validation (expanded)
COMMON_WORDS: Set[str] = {
    "the",
    "be",
    "to",
    "of",
    "and",
    "a",
    "in",
    "that",
    "have",
    "i",
    "it",
    "for",
    "not",
    "on",
    "with",
    "he",
    "as",
    "you",
    "do",
    "at",
    "this",
    "but",
    "his",
    "by",
    "from",
    "they",
    "we",
    "say",
    "her",
    "she",
    "or",
    "an",
    "will",
    "my",
    "one",
    "all",
    "would",
    "there",
    "their",
    "what",
    "so",
    "up",
    "out",
    "if",
    "about",
    "who",
    "get",
    "which",
    "go",
    "me",
    "when",
    "make",
    "can",
    "like",
    "time",
    "no",
    "just",
    "him",
    "know",
    "take",
    "people",
    "into",
    "year",
    "your",
    "good",
    "some",
    "could",
    "them",
    "see",
    "other",
    "than",
    "then",
    "now",
    "look",
    "only",
    "come",
    "its",
    "over",
    "think",
    "also",
    "back",
    "after",
    "use",
    "two",
    "how",
    "our",
    "work",
    "first",
    "well",
    "way",
    "even",
    "new",
    "want",
    "because",
    "any",
    "these",
    "give",
    "day",
    "most",
    "us",
    # Common greetings and words
    "hello",
    "world",
    "hi",
    "hey",
    "please",
    "thanks",
    "thank",
    "yes",
    "no",
    "ok",
    # Security-related words
    "help",
    "tell",
    "show",
    "explain",
    "write",
    "read",
    "ignore",
    "forget",
    "system",
    "prompt",
    "instructions",
    "password",
    "secret",
    "data",
    "file",
    "code",
    "user",
    "admin",
    "root",
    "access",
    "key",
    "token",
    "api",
    "command",
    "execute",
}


@dataclass
class FlipAttackDetectorResult:
    """Detection result for FlipAttack."""

    detected: bool
    confidence: float
    attack_type: str  # "FCS", "FCW", "FWO", "EXPLICIT", "NONE"
    matched_patterns: List[str]
    risk_score: float
    explanation: str
    reversed_sample: str  # What it looks like when reversed


class FlipAttackDetector:
    """
    Detects FlipAttack jailbreaks that reverse character/word order.

    Detection methods:
    1. Explicit flip instructions (read backwards, reverse, etc.)
    2. Entropy analysis (reversed text has unusual bigram distribution)
    3. Word validation (check if words become valid when reversed)
    4. Gibberish detection with reversal recovery
    """

    # Patterns for explicit flip/reverse instructions
    EXPLICIT_PATTERNS = [
        r"reverse\s+(the\s+)?order",
        r"read\s+.{0,30}backwards",  # "read ... backwards" with anything in between
        r"flip\s+(the\s+)?(characters?|words?|text|letters?)",
        r"mirror\s+(the\s+)?text",
        r"backwards?\s+reading",
        r"right\s+to\s+left",
        r"\bbackwards\b",  # standalone "backwards"
        r"sdrawkcab",  # "backwards" reversed
        r"esrever",  # "reverse" reversed
    ]

    # Common English bigrams (for entropy analysis)
    COMMON_BIGRAMS = {
        "th",
        "he",
        "in",
        "er",
        "an",
        "re",
        "on",
        "at",
        "en",
        "nd",
        "ti",
        "es",
        "or",
        "te",
        "of",
        "ed",
        "is",
        "it",
        "al",
        "ar",
        "st",
        "to",
        "nt",
        "ng",
        "se",
        "ha",
        "as",
        "ou",
        "io",
        "le",
    }

    def __init__(self):
        self._explicit_compiled = [
            re.compile(p, re.IGNORECASE) for p in self.EXPLICIT_PATTERNS
        ]

    def _check_explicit_patterns(self, text: str) -> List[str]:
        """Check for explicit flip/reverse instructions."""
        matched = []
        for i, pattern in enumerate(self._explicit_compiled):
            if pattern.search(text):
                matched.append(f"explicit:{self.EXPLICIT_PATTERNS[i][:20]}")
        return matched

    def _calculate_bigram_score(self, text: str) -> float:
        """
        Calculate how 'normal' the text looks based on bigram frequency.
        Higher score = more normal English text.
        """
        text_clean = re.sub(r"[^a-z]", "", text.lower())
        if len(text_clean) < 4:
            return 0.5  # Too short to analyze

        bigrams = [text_clean[i : i + 2] for i in range(len(text_clean) - 1)]
        if not bigrams:
            return 0.5

        common_count = sum(1 for bg in bigrams if bg in self.COMMON_BIGRAMS)
        return common_count / len(bigrams)

    def _count_valid_words(self, text: str) -> Tuple[int, int]:
        """Count valid English words in text. Returns (valid, total)."""
        words = re.findall(r"[a-zA-Z]+", text.lower())
        if not words:
            return 0, 0

        valid = sum(1 for w in words if w in COMMON_WORDS or len(w) <= 2)
        return valid, len(words)

    def _reverse_text(self, text: str) -> str:
        """Reverse entire text (FCS detection)."""
        return text[::-1]

    def _reverse_words(self, text: str) -> str:
        """Reverse each word but keep word order (FCW detection)."""
        words = text.split()
        return " ".join(word[::-1] for word in words)

    def _reverse_word_order(self, text: str) -> str:
        """Reverse word order but keep characters (FWO detection)."""
        words = text.split()
        return " ".join(reversed(words))

    def _is_likely_reversed(self, text: str) -> Tuple[bool, str, str]:
        """
        Check if text is likely reversed by testing reversal methods.
        Returns (is_reversed, attack_type, reversed_sample).
        """
        original_bigram_score = self._calculate_bigram_score(text)
        original_valid, original_total = self._count_valid_words(text)
        original_valid_ratio = (
            original_valid / original_total if original_total > 0 else 0
        )

        # Test FCS (full character reversal)
        fcs_reversed = self._reverse_text(text)
        fcs_bigram_score = self._calculate_bigram_score(fcs_reversed)
        fcs_valid, fcs_total = self._count_valid_words(fcs_reversed)
        fcs_valid_ratio = fcs_valid / fcs_total if fcs_total > 0 else 0

        # Test FCW (reverse chars in each word)
        fcw_reversed = self._reverse_words(text)
        fcw_bigram_score = self._calculate_bigram_score(fcw_reversed)
        fcw_valid, fcw_total = self._count_valid_words(fcw_reversed)
        fcw_valid_ratio = fcw_valid / fcw_total if fcw_total > 0 else 0

        # Test FWO (reverse word order)
        fwo_reversed = self._reverse_word_order(text)
        fwo_bigram_score = self._calculate_bigram_score(fwo_reversed)
        fwo_valid, fwo_total = self._count_valid_words(fwo_reversed)
        fwo_valid_ratio = fwo_valid / fwo_total if fwo_total > 0 else 0

        # Determine if any reversal produces significantly better text
        improvements = [
            (
                "FCS",
                fcs_bigram_score - original_bigram_score,
                fcs_valid_ratio - original_valid_ratio,
                fcs_reversed,
            ),
            (
                "FCW",
                fcw_bigram_score - original_bigram_score,
                fcw_valid_ratio - original_valid_ratio,
                fcw_reversed,
            ),
            (
                "FWO",
                fwo_bigram_score - original_bigram_score,
                fwo_valid_ratio - original_valid_ratio,
                fwo_reversed,
            ),
        ]

        # Sort by combined improvement
        improvements.sort(key=lambda x: x[1] + x[2], reverse=True)

        best = improvements[0]
        # Significant improvement threshold (lowered for better detection)
        if best[1] > 0.08 or best[2] > 0.2:
            return True, best[0], best[3][:100]

        return False, "NONE", ""

    def analyze(self, text: str) -> FlipAttackDetectorResult:
        """Analyze text for FlipAttack patterns."""
        matched_patterns = []
        attack_type = "NONE"
        reversed_sample = ""

        # 1. Check explicit flip instructions
        explicit_matches = self._check_explicit_patterns(text)
        if explicit_matches:
            matched_patterns.extend(explicit_matches)
            attack_type = "EXPLICIT"

        # 2. Check if text itself appears to be reversed
        is_reversed, rev_type, rev_sample = self._is_likely_reversed(text)
        if is_reversed:
            matched_patterns.append(f"reversal:{rev_type}")
            if attack_type == "NONE":
                attack_type = rev_type
            reversed_sample = rev_sample

        # 3. Calculate confidence
        confidence = min(0.95, 0.2 + len(matched_patterns) * 0.25)
        detected = len(matched_patterns) >= 1

        # Build explanation
        if detected:
            explanation = (
                f"Detected {attack_type} FlipAttack: {', '.join(matched_patterns[:3])}"
            )
        else:
            explanation = "No FlipAttack indicators found"

        return FlipAttackDetectorResult(
            detected=detected,
            confidence=confidence,
            attack_type=attack_type,
            matched_patterns=matched_patterns[:5],
            risk_score=confidence if detected else confidence * 0.3,
            explanation=explanation,
            reversed_sample=reversed_sample,
        )


# Singleton pattern
_detector = None


def get_detector() -> FlipAttackDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = FlipAttackDetector()
    return _detector


def detect(text: str) -> FlipAttackDetectorResult:
    """Convenience function for detection."""
    return get_detector().analyze(text)
