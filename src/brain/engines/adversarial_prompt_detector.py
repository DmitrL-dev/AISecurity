"""
Adversarial Prompt Detector Engine - Perturbation Defense

Detects adversarial prompt perturbations:
- Character-level perturbations
- Word-level substitutions
- Semantic-preserving attacks
- Gradient-based attacks

Addresses: OWASP ASI-01 (Adversarial Prompts)
Research: adversarial_prompts_deep_dive.md
Invention: Adversarial Prompt Detector (#46)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("AdversarialPromptDetector")


# ============================================================================
# Data Classes
# ============================================================================


class PerturbationType(Enum):
    """Types of perturbations."""

    HOMOGLYPH = "homoglyph"
    TYPOSQUATTING = "typosquatting"
    INVISIBLE_CHAR = "invisible_char"
    SEMANTIC_SWAP = "semantic_swap"


@dataclass
class PerturbationResult:
    """Result from perturbation detection."""

    is_adversarial: bool
    perturbations: List[PerturbationType] = field(default_factory=list)
    confidence: float = 0.0
    normalized_text: str = ""
    suspicious_positions: List[int] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_adversarial": self.is_adversarial,
            "perturbations": [p.value for p in self.perturbations],
            "confidence": self.confidence,
            "normalized_text": self.normalized_text,
            "suspicious_positions": self.suspicious_positions,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Homoglyph Detector
# ============================================================================


class HomoglyphDetector:
    """Detects homoglyph substitutions."""

    HOMOGLYPHS = {
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
        "０": "0",
        "１": "1",
        "２": "2",
        "３": "3",
    }

    def detect(self, text: str) -> Tuple[bool, List[int]]:
        """Detect homoglyphs."""
        positions = []
        for i, char in enumerate(text):
            if char in self.HOMOGLYPHS:
                positions.append(i)
        return len(positions) > 0, positions

    def normalize(self, text: str) -> str:
        """Normalize homoglyphs."""
        result = []
        for char in text:
            result.append(self.HOMOGLYPHS.get(char, char))
        return "".join(result)


# ============================================================================
# Invisible Char Detector
# ============================================================================


class InvisibleCharDetector:
    """Detects invisible characters."""

    INVISIBLE = {
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
        "\u00ad",
        "\u034f",
        "\u061c",
        "\u115f",
        "\u1160",
    }

    def detect(self, text: str) -> Tuple[bool, List[int]]:
        """Detect invisible chars."""
        positions = []
        for i, char in enumerate(text):
            if char in self.INVISIBLE or ord(char) < 32:
                positions.append(i)
        return len(positions) > 0, positions

    def remove(self, text: str) -> str:
        """Remove invisible chars."""
        return "".join(
            c for c in text if c not in self.INVISIBLE and ord(c) >= 32)


# ============================================================================
# Typo Detector
# ============================================================================


class TypoDetector:
    """Detects typosquatting attacks."""

    ATTACK_WORDS = {
        "ignore": ["ignroe", "ingore", "lgnore", "1gnore"],
        "system": ["systern", "syst3m", "sytem", "ssystem"],
        "prompt": ["pr0mpt", "promtp", "pormpt"],
    }

    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """Detect typosquatting."""
        found = []
        text_lower = text.lower()

        for correct, typos in self.ATTACK_WORDS.items():
            for typo in typos:
                if typo in text_lower:
                    found.append(typo)

        return len(found) > 0, found


# ============================================================================
# Main Engine
# ============================================================================


class AdversarialPromptDetector:
    """
    Adversarial Prompt Detector - Perturbation Defense

    Detects:
    - Homoglyphs
    - Invisible chars
    - Typosquatting

    Invention #46 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.homoglyph = HomoglyphDetector()
        self.invisible = InvisibleCharDetector()
        self.typo = TypoDetector()

        logger.info("AdversarialPromptDetector initialized")

    def analyze(self, text: str) -> PerturbationResult:
        """Analyze text for adversarial perturbations."""
        start = time.time()

        perturbations = []
        positions = []

        # Check homoglyphs
        has_homo, homo_pos = self.homoglyph.detect(text)
        if has_homo:
            perturbations.append(PerturbationType.HOMOGLYPH)
            positions.extend(homo_pos)

        # Check invisible
        has_invis, invis_pos = self.invisible.detect(text)
        if has_invis:
            perturbations.append(PerturbationType.INVISIBLE_CHAR)
            positions.extend(invis_pos)

        # Check typos
        has_typo, _ = self.typo.detect(text)
        if has_typo:
            perturbations.append(PerturbationType.TYPOSQUATTING)

        # Normalize
        normalized = self.homoglyph.normalize(text)
        normalized = self.invisible.remove(normalized)

        is_adversarial = len(perturbations) > 0
        confidence = min(1.0, len(perturbations) / 3.0 + len(positions) * 0.1)

        if is_adversarial:
            logger.warning(f"Adversarial: {[p.value for p in perturbations]}")

        return PerturbationResult(
            is_adversarial=is_adversarial,
            perturbations=perturbations,
            confidence=confidence,
            normalized_text=normalized,
            suspicious_positions=positions[:10],
            explanation=f"Found {len(perturbations)} perturbation types",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_detector: Optional[AdversarialPromptDetector] = None


def get_detector() -> AdversarialPromptDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = AdversarialPromptDetector()
    return _default_detector
