"""
Multi-Layer Canonicalizer Engine - Obfuscation Defense

Defends against text obfuscation attacks:
- Homoglyph detection and normalization
- Unicode canonicalization
- Encoding attack detection
- Zero-width character removal

Addresses: OWASP ASI-01 (Prompt Injection via Obfuscation)
Research: obfuscation_defense_deep_dive.md
Invention: Multi-Layer Canonicalizer (#32)
"""

import re
import unicodedata
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("MultiLayerCanonicalizer")


# ============================================================================
# Data Classes
# ============================================================================


class ObfuscationType(Enum):
    """Types of obfuscation detected."""

    HOMOGLYPH = "homoglyph"
    ZERO_WIDTH = "zero_width"
    UNICODE_ESCAPE = "unicode_escape"
    ENCODING_ABUSE = "encoding_abuse"
    INVISIBLE_CHAR = "invisible_char"


@dataclass
class CanonicalizationResult:
    """Result from canonicalization."""

    original: str
    normalized: str
    was_obfuscated: bool
    obfuscation_types: List[ObfuscationType] = field(default_factory=list)
    replacements: int = 0
    risk_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "was_obfuscated": self.was_obfuscated,
            "types": [t.value for t in self.obfuscation_types],
            "replacements": self.replacements,
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Homoglyph Detector
# ============================================================================


class HomoglyphDetector:
    """
    Detects and normalizes homoglyphs.
    """

    # Common homoglyph mappings (Cyrillic, Greek, etc. -> Latin)
    HOMOGLYPHS = {
        # Cyrillic
        "а": "a",
        "е": "e",
        "о": "o",
        "р": "p",
        "с": "c",
        "у": "y",
        "х": "x",
        "А": "A",
        "В": "B",
        "Е": "E",
        "К": "K",
        "М": "M",
        "Н": "H",
        "О": "O",
        "Р": "P",
        "С": "C",
        "Т": "T",
        "Х": "X",
        # Greek
        "α": "a",
        "β": "b",
        "ε": "e",
        "ι": "i",
        "κ": "k",
        "ο": "o",
        "ρ": "p",
        "τ": "t",
        "υ": "u",
        "ν": "v",
        "ω": "w",
        # Fullwidth
        "ａ": "a",
        "ｂ": "b",
        "ｃ": "c",
        "ｄ": "d",
        "ｅ": "e",
        # Special lookalikes
        "і": "i",
        "ј": "j",
        "ѕ": "s",
        "ɡ": "g",
        "ɴ": "n",
    }

    def detect_and_normalize(
            self, text: str) -> Tuple[str, int, List[Tuple[str, str]]]:
        """
        Detect and replace homoglyphs.

        Returns:
            (normalized_text, replacement_count, replacements_list)
        """
        result = []
        count = 0
        replacements = []

        for char in text:
            if char in self.HOMOGLYPHS:
                replacement = self.HOMOGLYPHS[char]
                result.append(replacement)
                replacements.append((char, replacement))
                count += 1
            else:
                result.append(char)

        return "".join(result), count, replacements


# ============================================================================
# Zero-Width Remover
# ============================================================================


class ZeroWidthRemover:
    """
    Removes zero-width and invisible characters.
    """

    ZERO_WIDTH_CHARS = {
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\u2060",  # Word joiner
        "\ufeff",  # BOM / Zero-width no-break space
        "\u180e",  # Mongolian vowel separator
    }

    INVISIBLE_CATEGORIES = {"Cf", "Cc", "Co"}  # Format, Control, Private

    def remove(self, text: str) -> Tuple[str, int]:
        """
        Remove zero-width and invisible characters.

        Returns:
            (cleaned_text, removed_count)
        """
        result = []
        count = 0

        for char in text:
            if char in self.ZERO_WIDTH_CHARS:
                count += 1
                continue

            category = unicodedata.category(char)
            if category in self.INVISIBLE_CATEGORIES and char not in "\n\r\t":
                count += 1
                continue

            result.append(char)

        return "".join(result), count


# ============================================================================
# Encoding Normalizer
# ============================================================================


class EncodingNormalizer:
    """
    Normalizes various encoding tricks.
    """

    def normalize(self, text: str) -> Tuple[str, int, List[str]]:
        """
        Normalize encoding tricks.

        Returns:
            (normalized_text, changes_count, detected_tricks)
        """
        result = text
        count = 0
        tricks = []

        # Unicode escape sequences
        unicode_pattern = r"\\u([0-9a-fA-F]{4})"
        if re.search(unicode_pattern, result):

            def replace_unicode(m):
                return chr(int(m.group(1), 16))

            result = re.sub(unicode_pattern, replace_unicode, result)
            count += 1
            tricks.append("unicode_escape")

        # HTML entities
        html_pattern = r"&#(\d+);"
        if re.search(html_pattern, result):

            def replace_html(m):
                return chr(int(m.group(1)))

            result = re.sub(html_pattern, replace_html, result)
            count += 1
            tricks.append("html_entity")

        # URL encoding
        url_pattern = r"%([0-9a-fA-F]{2})"
        if re.search(url_pattern, result):

            def replace_url(m):
                return chr(int(m.group(1), 16))

            result = re.sub(url_pattern, replace_url, result)
            count += 1
            tricks.append("url_encoded")

        return result, count, tricks


# ============================================================================
# Unicode Normalizer
# ============================================================================


class UnicodeNormalizer:
    """
    Applies Unicode normalization forms.
    """

    def normalize(self, text: str, form: str = "NFKC") -> str:
        """
        Apply Unicode normalization.

        Forms:
            NFC - Canonical decomposition + canonical composition
            NFD - Canonical decomposition
            NFKC - Compatibility decomposition + canonical composition
            NFKD - Compatibility decomposition
        """
        return unicodedata.normalize(form, text)


# ============================================================================
# Main Engine
# ============================================================================


class MultiLayerCanonicalizer:
    """
    Multi-Layer Canonicalizer - Obfuscation Defense

    Multi-layer text normalization:
    - Zero-width removal
    - Homoglyph detection
    - Encoding normalization
    - Unicode normalization

    Invention #32 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.homoglyph_detector = HomoglyphDetector()
        self.zero_width_remover = ZeroWidthRemover()
        self.encoding_normalizer = EncodingNormalizer()
        self.unicode_normalizer = UnicodeNormalizer()

        logger.info("MultiLayerCanonicalizer initialized")

    def canonicalize(self, text: str) -> CanonicalizationResult:
        """
        Apply all canonicalization layers.

        Args:
            text: Input text

        Returns:
            CanonicalizationResult
        """
        start = time.time()

        result = text
        types = []
        total_replacements = 0

        # Layer 1: Remove zero-width
        result, zw_count = self.zero_width_remover.remove(result)
        if zw_count > 0:
            types.append(ObfuscationType.ZERO_WIDTH)
            total_replacements += zw_count

        # Layer 2: Normalize encoding
        result, enc_count, tricks = self.encoding_normalizer.normalize(result)
        if enc_count > 0:
            types.append(ObfuscationType.ENCODING_ABUSE)
            total_replacements += enc_count

        # Layer 3: Homoglyph detection
        result, hg_count, hg_list = self.homoglyph_detector.detect_and_normalize(
            result)
        if hg_count > 0:
            types.append(ObfuscationType.HOMOGLYPH)
            total_replacements += hg_count

        # Layer 4: Unicode normalization
        normalized = self.unicode_normalizer.normalize(result)
        if normalized != result:
            types.append(ObfuscationType.UNICODE_ESCAPE)
            total_replacements += 1
            result = normalized

        was_obfuscated = len(types) > 0
        risk = min(1.0, total_replacements * 0.1) if was_obfuscated else 0.0

        if was_obfuscated:
            logger.warning(f"Obfuscation detected: {[t.value for t in types]}")

        return CanonicalizationResult(
            original=text,
            normalized=result,
            was_obfuscated=was_obfuscated,
            obfuscation_types=types,
            replacements=total_replacements,
            risk_score=risk,
            explanation=f"Detected: {[t.value for t in types]}" if types else "Clean",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_canonicalizer: Optional[MultiLayerCanonicalizer] = None


def get_canonicalizer() -> MultiLayerCanonicalizer:
    global _default_canonicalizer
    if _default_canonicalizer is None:
        _default_canonicalizer = MultiLayerCanonicalizer()
    return _default_canonicalizer
