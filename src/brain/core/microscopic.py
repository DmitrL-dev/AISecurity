"""
Microscopic Attack Analysis — Sub-Token Level Detection

Analyzes attacks at sub-token granularity to detect:
- Unicode homoglyphs
- BPE-based attacks
- Zero-width character injection
- Invisible character payloads

Key Features:
- Character-level analysis
- Homoglyph detection
- Unicode normalization attacks
- BPE tokenization exploits
- Invisible payload extraction

Usage:
    micro = MicroscopicAnalyzer()
    result = micro.analyze("hеllo wоrld")  # Contains Cyrillic
    print(result.homoglyphs_found)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import unicodedata
import re


@dataclass
class MicroscopicResult:
    """Result of microscopic analysis."""
    is_suspicious: bool
    risk_score: float
    homoglyphs_found: List[Dict] = field(default_factory=list)
    invisible_chars: List[Dict] = field(default_factory=list)
    unicode_anomalies: List[Dict] = field(default_factory=list)
    bpe_exploits: List[str] = field(default_factory=list)
    normalized_text: str = ""
    details: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "is_suspicious": self.is_suspicious,
            "risk_score": round(self.risk_score, 3),
            "homoglyphs": len(self.homoglyphs_found),
            "invisible": len(self.invisible_chars),
            "anomalies": len(self.unicode_anomalies),
            "bpe_exploits": len(self.bpe_exploits),
        }


class MicroscopicAnalyzer:
    """
    Sub-token level analysis for detecting sophisticated evasion attacks.

    Examines individual characters, Unicode properties, and tokenization
    behavior to detect attacks that bypass token-level analysis.
    """

    # Homoglyph mapping (confusables)
    # Maps visually similar characters to their ASCII equivalents
    HOMOGLYPHS = {
        # Cyrillic lookalikes
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
        # Greek lookalikes
        'α': 'a', 'ο': 'o', 'ρ': 'p', 'ν': 'v',
        'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Η': 'H', 'Ι': 'I', 'Κ': 'K',
        'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T', 'Χ': 'X',
        # Numbers that look like letters
        '0': 'O', '1': 'l', '3': 'E', '4': 'A', '5': 'S', '8': 'B',
        # Special characters
        'ı': 'i',  # Turkish dotless i
        'ﬁ': 'fi', 'ﬂ': 'fl',  # Ligatures
    }

    # Zero-width and invisible characters
    INVISIBLE_CHARS = {
        '\u200b': 'ZERO_WIDTH_SPACE',
        '\u200c': 'ZERO_WIDTH_NON_JOINER',
        '\u200d': 'ZERO_WIDTH_JOINER',
        '\u2060': 'WORD_JOINER',
        '\u2061': 'FUNCTION_APPLICATION',
        '\u2062': 'INVISIBLE_TIMES',
        '\u2063': 'INVISIBLE_SEPARATOR',
        '\u2064': 'INVISIBLE_PLUS',
        '\ufeff': 'BYTE_ORDER_MARK',
        '\u00ad': 'SOFT_HYPHEN',
        '\u034f': 'COMBINING_GRAPHEME_JOINER',
        '\u180e': 'MONGOLIAN_VOWEL_SEPARATOR',
    }

    # Suspicious Unicode categories
    SUSPICIOUS_CATEGORIES = {
        'Cf': 'Format character',
        'Co': 'Private use',
        'Cn': 'Unassigned',
    }

    # BPE exploit patterns
    BPE_EXPLOITS = [
        r"(?:ig|In)(?:ore|nore)",  # Split "ignore"
        r"(?:sys|Sys)(?:tem|TEM)",  # Split "system"
        r"(?:pro|Pro)(?:mpt|MPT)",  # Split "prompt"
        r"(?:in|In)(?:struct|STRUCT)",  # Split "instruct"
    ]

    def __init__(self):
        """Initialize microscopic analyzer."""
        self._analysis_count = 0
        self._suspicious_count = 0

    def analyze(self, text: str) -> MicroscopicResult:
        """
        Perform microscopic analysis on text.

        Args:
            text: Text to analyze

        Returns:
            MicroscopicResult with detailed findings
        """
        self._analysis_count += 1

        homoglyphs = self._detect_homoglyphs(text)
        invisibles = self._detect_invisible_chars(text)
        anomalies = self._detect_unicode_anomalies(text)
        bpe = self._detect_bpe_exploits(text)
        normalized = self._normalize(text)

        # Calculate risk score
        risk = 0.0
        risk += min(0.4, len(homoglyphs) * 0.08)  # Max 0.4 for homoglyphs
        risk += min(0.3, len(invisibles) * 0.15)  # Max 0.3 for invisibles
        risk += min(0.2, len(anomalies) * 0.05)   # Max 0.2 for anomalies
        risk += min(0.2, len(bpe) * 0.1)          # Max 0.2 for BPE

        is_suspicious = risk > 0.1

        if is_suspicious:
            self._suspicious_count += 1

        return MicroscopicResult(
            is_suspicious=is_suspicious,
            risk_score=risk,
            homoglyphs_found=homoglyphs,
            invisible_chars=invisibles,
            unicode_anomalies=anomalies,
            bpe_exploits=bpe,
            normalized_text=normalized,
            details={
                "original_length": len(text),
                "normalized_length": len(normalized),
                "length_diff": len(text) - len(normalized),
            },
        )

    def _detect_homoglyphs(self, text: str) -> List[Dict]:
        """Detect homoglyph substitutions."""
        found = []
        for i, char in enumerate(text):
            if char in self.HOMOGLYPHS:
                found.append({
                    "position": i,
                    "char": char,
                    "looks_like": self.HOMOGLYPHS[char],
                    "codepoint": f"U+{ord(char):04X}",
                })
        return found

    def _detect_invisible_chars(self, text: str) -> List[Dict]:
        """Detect invisible/zero-width characters."""
        found = []
        for i, char in enumerate(text):
            if char in self.INVISIBLE_CHARS:
                found.append({
                    "position": i,
                    "type": self.INVISIBLE_CHARS[char],
                    "codepoint": f"U+{ord(char):04X}",
                })
        return found

    def _detect_unicode_anomalies(self, text: str) -> List[Dict]:
        """Detect unusual Unicode categories."""
        found = []
        for i, char in enumerate(text):
            category = unicodedata.category(char)
            if category in self.SUSPICIOUS_CATEGORIES:
                found.append({
                    "position": i,
                    "char_repr": repr(char),
                    "category": category,
                    "description": self.SUSPICIOUS_CATEGORIES[category],
                    "codepoint": f"U+{ord(char):04X}",
                })

            # Check for combining characters in unexpected places
            if category.startswith('M') and i == 0:  # Mark at start
                found.append({
                    "position": i,
                    "category": category,
                    "description": "Combining mark at string start",
                    "codepoint": f"U+{ord(char):04X}",
                })

        return found

    def _detect_bpe_exploits(self, text: str) -> List[str]:
        """Detect BPE tokenization exploit patterns."""
        found = []
        for pattern in self.BPE_EXPLOITS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found.extend(matches)
        return found

    def _normalize(self, text: str) -> str:
        """Normalize text by removing invisibles and replacing homoglyphs."""
        result = []
        for char in text:
            # Skip invisible characters
            if char in self.INVISIBLE_CHARS:
                continue
            # Replace homoglyphs
            if char in self.HOMOGLYPHS:
                result.append(self.HOMOGLYPHS[char])
            else:
                result.append(char)

        # Apply NFKC normalization
        normalized = ''.join(result)
        return unicodedata.normalize('NFKC', normalized)

    def get_normalized(self, text: str) -> str:
        """Get normalized version of text for safe processing."""
        return self._normalize(text)

    def compare_with_normalized(self, text: str) -> Dict:
        """
        Compare original text with normalized version.

        Useful for detecting if normalization changes meaning.
        """
        normalized = self._normalize(text)
        return {
            "original": text,
            "normalized": normalized,
            "are_different": text != normalized,
            "length_original": len(text),
            "length_normalized": len(normalized),
            "hidden_content_length": len(text) - len(normalized),
        }

    def get_stats(self) -> Dict:
        """Get analyzer statistics."""
        return {
            "total_analyses": self._analysis_count,
            "suspicious_found": self._suspicious_count,
            "suspicion_rate": (
                self._suspicious_count / self._analysis_count
                if self._analysis_count > 0 else 0
            ),
        }


# Singleton instance
_micro: Optional[MicroscopicAnalyzer] = None


def get_microscopic_analyzer() -> MicroscopicAnalyzer:
    """Get or create singleton MicroscopicAnalyzer instance."""
    global _micro
    if _micro is None:
        _micro = MicroscopicAnalyzer()
    return _micro


def analyze_microscopic(text: str) -> MicroscopicResult:
    """Quick microscopic analysis."""
    return get_microscopic_analyzer().analyze(text)
