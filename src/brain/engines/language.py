"""
Language Engine v2.0 - Enhanced Language Detection and Security

Features:
  1. Language detection (langdetect)
  2. Script detection (Cyrillic, Latin, Mixed)
  3. Encoding attack detection
  4. Homoglyph attack detection
  5. Unicode normalization attacks
  6. Multi-language bypass detection
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Tuple
from enum import Enum

try:
    from langdetect import detect, detect_langs, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

logger = logging.getLogger("LanguageEngine")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class Script(Enum):
    """Script types."""
    LATIN = "latin"
    CYRILLIC = "cyrillic"
    MIXED = "mixed"
    CJK = "cjk"           # Chinese, Japanese, Korean
    ARABIC = "arabic"
    OTHER = "other"


class EncodingThreat(Enum):
    """Encoding-based attack types."""
    HOMOGLYPH = "homoglyph"           # Visual lookalike characters
    ZERO_WIDTH = "zero_width"         # Invisible characters
    BIDI_OVERRIDE = "bidi_override"   # Right-to-left override
    NORMALIZATION = "normalization"   # Unicode normalization bypass


@dataclass
class LanguageResult:
    """Result of language detection."""
    detected_language: str = "unknown"
    confidence: float = 0.0
    is_supported: bool = True
    script: Script = Script.OTHER
    all_detected: List[dict] = field(default_factory=list)
    encoding_threats: List[str] = field(default_factory=list)
    risk_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "detected_language": self.detected_language,
            "confidence": self.confidence,
            "is_supported": self.is_supported,
            "script": self.script.value,
            "all_languages": self.all_detected,
            "encoding_threats": self.encoding_threats,
            "risk_score": self.risk_score
        }


# ============================================================================
# Script Detector
# ============================================================================

class ScriptDetector:
    """Detects script type and mixing."""

    # Unicode ranges
    RANGES = {
        Script.LATIN: [(0x0041, 0x007A), (0x00C0, 0x00FF)],
        Script.CYRILLIC: [(0x0400, 0x04FF), (0x0500, 0x052F)],
        Script.CJK: [(0x4E00, 0x9FFF), (0x3040, 0x30FF)],
        Script.ARABIC: [(0x0600, 0x06FF), (0x0750, 0x077F)],
    }

    def detect(self, text: str) -> Tuple[Script, Dict[str, float]]:
        """
        Detect script type and proportions.
        Returns (primary_script, {script: ratio}).
        """
        if not text:
            return Script.OTHER, {}

        counts = {s: 0 for s in Script}
        total = 0

        for char in text:
            if not char.isalpha():
                continue
            total += 1

            code = ord(char)
            found = False

            for script, ranges in self.RANGES.items():
                for start, end in ranges:
                    if start <= code <= end:
                        counts[script] += 1
                        found = True
                        break
                if found:
                    break

            if not found:
                counts[Script.OTHER] += 1

        if total == 0:
            return Script.OTHER, {}

        ratios = {s.value: c / total for s, c in counts.items() if c > 0}

        # Determine primary script
        if len(ratios) > 1:
            # Multiple scripts detected
            main_scripts = [s for s, r in ratios.items() if r > 0.1]
            if len(main_scripts) > 1:
                return Script.MIXED, ratios

        # Single dominant script
        if counts[Script.CYRILLIC] / max(total, 1) > 0.5:
            return Script.CYRILLIC, ratios
        if counts[Script.LATIN] / max(total, 1) > 0.5:
            return Script.LATIN, ratios
        if counts[Script.CJK] / max(total, 1) > 0.3:
            return Script.CJK, ratios
        if counts[Script.ARABIC] / max(total, 1) > 0.3:
            return Script.ARABIC, ratios

        return Script.OTHER, ratios


# ============================================================================
# Encoding Attack Detector
# ============================================================================

class EncodingAttackDetector:
    """Detects encoding-based attacks."""

    # Homoglyph mappings (Cyrillic -> Latin lookalikes)
    HOMOGLYPHS = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O',
        'Р': 'P', 'С': 'C', 'Т': 'T', 'Х': 'X',
    }

    # Zero-width characters
    ZERO_WIDTH = [
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u2060',  # Word joiner
        '\ufeff',  # Zero-width no-break space
    ]

    # BiDi override characters
    BIDI_CHARS = [
        '\u202a',  # Left-to-right embedding
        '\u202b',  # Right-to-left embedding
        '\u202c',  # Pop directional formatting
        '\u202d',  # Left-to-right override
        '\u202e',  # Right-to-left override
        '\u2066',  # Left-to-right isolate
        '\u2067',  # Right-to-left isolate
    ]

    def detect(self, text: str) -> List[Tuple[EncodingThreat, str]]:
        """
        Detect encoding attacks.
        Returns list of (threat_type, description).
        """
        threats = []

        # Check for homoglyphs in mixed-script context
        homoglyph_count = sum(1 for c in text if c in self.HOMOGLYPHS)
        if homoglyph_count > 0:
            # Only flag if there's script mixing
            has_latin = any(c.isalpha() and ord(c) < 0x0400 for c in text)
            has_cyrillic = any(0x0400 <= ord(c) <= 0x04FF for c in text)
            if has_latin and has_cyrillic:
                threats.append((
                    EncodingThreat.HOMOGLYPH,
                    f"Mixed Cyrillic/Latin with {homoglyph_count} lookalike chars"
                ))

        # Check for zero-width characters
        zero_width_count = sum(1 for c in text if c in self.ZERO_WIDTH)
        if zero_width_count > 0:
            threats.append((
                EncodingThreat.ZERO_WIDTH,
                f"Contains {zero_width_count} zero-width characters"
            ))

        # Check for BiDi override
        bidi_count = sum(1 for c in text if c in self.BIDI_CHARS)
        if bidi_count > 0:
            threats.append((
                EncodingThreat.BIDI_OVERRIDE,
                f"Contains {bidi_count} BiDi override characters"
            ))

        # Check for normalization differences
        nfc = unicodedata.normalize('NFC', text)
        nfkc = unicodedata.normalize('NFKC', text)
        if nfc != nfkc:
            threats.append((
                EncodingThreat.NORMALIZATION,
                "Text changes under NFKC normalization"
            ))

        return threats


# ============================================================================
# Main Language Engine
# ============================================================================

class LanguageEngine:
    """
    Language Engine v2.0 - Enhanced Language Detection and Security.

    Features:
      - Language detection
      - Script detection (Cyrillic/Latin mixing)
      - Encoding attack detection
      - Homoglyph attack detection
    """

    DEFAULT_SUPPORTED = {"en", "ru"}

    def __init__(
        self,
        mode: str = "WHITELIST",
        supported_languages: Optional[Set[str]] = None,
        blocked_languages: Optional[Set[str]] = None,
        min_confidence: float = 0.5
    ):
        logger.info("Initializing Language Engine v2.0...")

        self.mode = mode
        self.supported_languages = supported_languages or self.DEFAULT_SUPPORTED
        self.blocked_languages = blocked_languages or set()
        self.min_confidence = min_confidence

        # Components
        self.script_detector = ScriptDetector()
        self.encoding_detector = EncodingAttackDetector()

        logger.info(f"Language Engine v2.0 initialized. Mode={mode}")

    def detect(self, text: str) -> LanguageResult:
        """
        Detect language and analyze for security threats.
        """
        result = LanguageResult()

        # Minimum length for reliable detection
        if not text or len(text.strip()) < 20:
            result.is_supported = True
            return result

        # 1. Script detection
        script, script_ratios = self.script_detector.detect(text)
        result.script = script

        # Script mixing is suspicious
        if script == Script.MIXED:
            result.risk_score += 20.0

        # 2. Encoding attack detection
        encoding_threats = self.encoding_detector.detect(text)
        result.encoding_threats = [desc for _, desc in encoding_threats]

        for threat_type, desc in encoding_threats:
            if threat_type == EncodingThreat.HOMOGLYPH:
                result.risk_score += 40.0
            elif threat_type == EncodingThreat.ZERO_WIDTH:
                result.risk_score += 30.0
            elif threat_type == EncodingThreat.BIDI_OVERRIDE:
                result.risk_score += 50.0
            elif threat_type == EncodingThreat.NORMALIZATION:
                result.risk_score += 20.0

        # 3. Language detection
        if LANGDETECT_AVAILABLE:
            try:
                langs = detect_langs(text)
                result.all_detected = [
                    {"lang": l.lang, "prob": l.prob} for l in langs
                ]

                if langs:
                    result.detected_language = langs[0].lang
                    result.confidence = langs[0].prob

            except LangDetectException as e:
                logger.warning(f"Language detection failed: {e}")

        # 4. Support check
        if self.mode == "WHITELIST":
            result.is_supported = result.detected_language in self.supported_languages
        elif self.mode == "BLACKLIST":
            result.is_supported = result.detected_language not in self.blocked_languages
        else:
            result.is_supported = True

        # Low confidence = allow
        if result.confidence < self.min_confidence:
            result.is_supported = True

        # Unsupported language adds risk
        if not result.is_supported:
            result.risk_score += 30.0

        return result

    def scan(self, text: str, user_id: str = "anonymous") -> dict:
        """
        Scan text for language compliance.
        Returns dict compatible with analyzer pipeline.
        """
        result = self.detect(text)

        threats = result.encoding_threats.copy()

        if not result.is_supported:
            threats.append(f"Unsupported language: {result.detected_language}")

        if result.script == Script.MIXED:
            threats.append("Mixed script detected (potential bypass)")

        return {
            "is_safe": result.risk_score < 70.0,
            "risk_score": min(result.risk_score, 100.0),
            "threats": threats,
            "reason": f"Language: {result.detected_language}, Script: {result.script.value}",
            "detected_language": result.detected_language,
            "confidence": result.confidence,
            "script": result.script.value,
            "all_languages": result.all_detected
        }

    def normalize(self, text: str) -> str:
        """
        Normalize text to remove encoding attacks.
        """
        # Remove zero-width characters
        for char in self.encoding_detector.ZERO_WIDTH:
            text = text.replace(char, '')

        # Remove BiDi overrides
        for char in self.encoding_detector.BIDI_CHARS:
            text = text.replace(char, '')

        # NFKC normalization
        text = unicodedata.normalize('NFKC', text)

        return text
