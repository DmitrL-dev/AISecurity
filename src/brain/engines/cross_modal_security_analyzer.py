"""
Cross-Modal Security Analyzer Engine - VLM Security

Analyzes security across modalities:
- Text-image consistency
- Cross-modal injection detection
- Semantic alignment verification
- Multi-modal attack detection

Addresses: OWASP ASI-01 (Multi-Modal Attacks)
Research: vlm_security_deep_dive.md
Invention: Cross-Modal Security Analyzer (#23)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("CrossModalSecurityAnalyzer")


# ============================================================================
# Data Classes
# ============================================================================


class ModalityType(Enum):
    """Types of modalities."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class CrossModalThreat(Enum):
    """Types of cross-modal threats."""

    INJECTION_IN_IMAGE = "injection_in_image"
    SEMANTIC_MISMATCH = "semantic_mismatch"
    HIDDEN_TEXT = "hidden_text"
    STEGANOGRAPHY = "steganography"
    ADVERSARIAL_PATCH = "adversarial_patch"


@dataclass
class ModalityInput:
    """Input from a modality."""

    modality: ModalityType
    content: str  # Text or description
    metadata: Dict = field(default_factory=dict)


@dataclass
class CrossModalResult:
    """Result from cross-modal analysis."""

    is_safe: bool
    risk_score: float
    threats: List[CrossModalThreat] = field(default_factory=list)
    alignment_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "threats": [t.value for t in self.threats],
            "alignment_score": self.alignment_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Text Injection Detector
# ============================================================================


class TextInImageDetector:
    """
    Detects text-based injections in image descriptions.
    """

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?instructions",
        r"you\s+are\s+now",
        r"system\s*:\s*",
        r"override\s+",
        r"<script",
        r"\{%.*%\}",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.INJECTION_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detect injection patterns.

        Returns:
            (detected, matched_patterns)
        """
        matches = []
        for i, pattern in enumerate(self._patterns):
            if pattern.search(text):
                matches.append(self.INJECTION_PATTERNS[i])

        return len(matches) > 0, matches


# ============================================================================
# Semantic Alignment Checker
# ============================================================================


class SemanticAlignmentChecker:
    """
    Checks semantic alignment between modalities.
    """

    def __init__(self):
        self._common_objects = {
            "cat",
            "dog",
            "car",
            "person",
            "tree",
            "building",
            "sun",
            "moon",
            "water",
            "food",
            "computer",
            "phone",
        }

    def check_alignment(
        self,
        text_content: str,
        image_description: str,
    ) -> Tuple[float, str]:
        """
        Check semantic alignment.

        Returns:
            (alignment_score, explanation)
        """
        text_words = set(text_content.lower().split())
        image_words = set(image_description.lower().split())

        # Find common concepts
        common = text_words & image_words
        objects_in_text = text_words & self._common_objects
        objects_in_image = image_words & self._common_objects

        common_objects = objects_in_text & objects_in_image

        if not objects_in_text and not objects_in_image:
            return 1.0, "No objects to compare"

        total = len(objects_in_text | objects_in_image) or 1
        score = len(common_objects) / total

        if score < 0.3:
            return (
                score,
                f"Low alignment: text={objects_in_text}, image={objects_in_image}",
            )

        return score, "Aligned"


# ============================================================================
# Hidden Content Detector
# ============================================================================


class HiddenContentDetector:
    """
    Detects hidden content in metadata.
    """

    SUSPICIOUS_KEYS = [
        "comment",
        "exif",
        "description",
        "author",
        "copyright",
        "software",
        "xml",
    ]

    def detect(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """
        Detect hidden content in metadata.

        Returns:
            (detected, suspicious_fields)
        """
        suspicious = []

        for key, value in metadata.items():
            key_lower = key.lower()

            # Check suspicious keys
            if any(s in key_lower for s in self.SUSPICIOUS_KEYS):
                if isinstance(value, str) and len(value) > 100:
                    suspicious.append(f"{key}: long content")

                # Check for code-like content
                if isinstance(value, str):
                    if "<" in value or "{" in value or "eval(" in value:
                        suspicious.append(f"{key}: code-like")

        return len(suspicious) > 0, suspicious


# ============================================================================
# Main Engine
# ============================================================================


class CrossModalSecurityAnalyzer:
    """
    Cross-Modal Security Analyzer - VLM Security

    Multi-modal security analysis:
    - Text injection in images
    - Semantic alignment
    - Hidden content detection

    Invention #23 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self, alignment_threshold: float = 0.3):
        self.injection_detector = TextInImageDetector()
        self.alignment_checker = SemanticAlignmentChecker()
        self.hidden_detector = HiddenContentDetector()

        self.alignment_threshold = alignment_threshold

        logger.info("CrossModalSecurityAnalyzer initialized")

    def analyze(
        self,
        inputs: List[ModalityInput],
    ) -> CrossModalResult:
        """
        Analyze cross-modal inputs.

        Args:
            inputs: List of modality inputs

        Returns:
            CrossModalResult
        """
        start = time.time()

        threats = []
        max_risk = 0.0
        explanations = []
        alignment = 1.0

        text_content = ""
        image_desc = ""

        for inp in inputs:
            # Check for injection patterns
            inj_detected, inj_patterns = self.injection_detector.detect(
                inp.content)
            if inj_detected:
                threats.append(CrossModalThreat.INJECTION_IN_IMAGE)
                max_risk = max(max_risk, 0.9)
                explanations.append(f"Injection in {inp.modality.value}")

            # Check metadata
            hidden, hidden_fields = self.hidden_detector.detect(inp.metadata)
            if hidden:
                threats.append(CrossModalThreat.HIDDEN_TEXT)
                max_risk = max(max_risk, 0.7)
                explanations.append(f"Hidden content: {hidden_fields}")

            if inp.modality == ModalityType.TEXT:
                text_content = inp.content
            elif inp.modality == ModalityType.IMAGE:
                image_desc = inp.content

        # Check cross-modal alignment
        if text_content and image_desc:
            alignment, align_exp = self.alignment_checker.check_alignment(
                text_content, image_desc
            )

            if alignment < self.alignment_threshold:
                threats.append(CrossModalThreat.SEMANTIC_MISMATCH)
                max_risk = max(max_risk, 0.6)
                explanations.append(align_exp)

        is_safe = len(threats) == 0

        if threats:
            logger.warning(
                f"Cross-modal threats: {[t.value for t in threats]}")

        return CrossModalResult(
            is_safe=is_safe,
            risk_score=max_risk,
            threats=threats,
            alignment_score=alignment,
            explanation="; ".join(explanations) if explanations else "Safe",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_analyzer: Optional[CrossModalSecurityAnalyzer] = None


def get_analyzer() -> CrossModalSecurityAnalyzer:
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = CrossModalSecurityAnalyzer()
    return _default_analyzer
