"""
Recursive Injection Guard Engine - Nested Attack Defense

Detects recursive/nested injection attacks:
- Nested prompt detection
- Recursive pattern analysis
- Depth limiting
- Escape sequence detection

Addresses: OWASP ASI-01 (Nested Injection)
Research: recursive_injection_deep_dive.md
Invention: Recursive Injection Guard (#48)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("RecursiveInjectionGuard")


# ============================================================================
# Data Classes
# ============================================================================


class NestingType(Enum):
    """Types of nesting attacks."""

    NESTED_PROMPT = "nested_prompt"
    RECURSIVE_CALL = "recursive_call"
    ESCAPE_SEQUENCE = "escape_sequence"
    MULTI_LAYER = "multi_layer"


@dataclass
class NestingResult:
    """Result from nesting detection."""

    is_nested: bool
    nesting_depth: int = 0
    nesting_types: List[NestingType] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_nested": self.is_nested,
            "nesting_depth": self.nesting_depth,
            "nesting_types": [n.value for n in self.nesting_types],
            "confidence": self.confidence,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Depth Analyzer
# ============================================================================


class DepthAnalyzer:
    """Analyzes nesting depth."""

    NESTING_MARKERS = [
        ("{{", "}}"),
        ("<<<", ">>>"),
        ("[[[", "]]]"),
        ('"""', '"""'),
    ]

    def analyze(self, text: str) -> int:
        """Analyze nesting depth."""
        max_depth = 0

        for open_m, close_m in self.NESTING_MARKERS:
            depth = 0
            current_depth = 0
            i = 0

            while i < len(text):
                if text[i: i + len(open_m)] == open_m:
                    current_depth += 1
                    depth = max(depth, current_depth)
                    i += len(open_m)
                elif text[i: i + len(close_m)] == close_m:
                    current_depth = max(0, current_depth - 1)
                    i += len(close_m)
                else:
                    i += 1

            max_depth = max(max_depth, depth)

        return max_depth


# ============================================================================
# Pattern Detector
# ============================================================================


class PatternDetector:
    """Detects recursive patterns."""

    RECURSIVE_PATTERNS = [
        r"ignore.*ignore.*ignore",
        r"system.*system.*system",
        r"prompt.*prompt.*prompt",
        r"\{\{.*\{\{.*\}\}.*\}\}",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.RECURSIVE_PATTERNS
        ]

    def detect(self, text: str) -> Tuple[bool, int]:
        """Detect recursive patterns."""
        matches = 0
        for pattern in self._compiled:
            if pattern.search(text):
                matches += 1
        return matches > 0, matches


# ============================================================================
# Escape Detector
# ============================================================================


class EscapeDetector:
    """Detects escape sequence attacks."""

    ESCAPE_PATTERNS = [
        r"\\n\\n\\n",
        r"\\x[0-9a-f]{2}",
        r"\\u[0-9a-f]{4}",
        r"%0a%0a",
        r"\r\n\r\n",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE)
                          for p in self.ESCAPE_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, int]:
        """Detect escape sequences."""
        matches = 0
        for pattern in self._compiled:
            if pattern.search(text):
                matches += 1
        return matches > 0, matches


# ============================================================================
# Main Engine
# ============================================================================


class RecursiveInjectionGuard:
    """
    Recursive Injection Guard - Nested Attack Defense

    Detects:
    - Nested prompts
    - Recursive patterns
    - Escape sequences

    Invention #48 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self, max_depth: int = 3):
        self.depth_analyzer = DepthAnalyzer()
        self.pattern_detector = PatternDetector()
        self.escape_detector = EscapeDetector()
        self.max_depth = max_depth

        logger.info("RecursiveInjectionGuard initialized")

    def analyze(self, text: str) -> NestingResult:
        """Analyze text for nested attacks."""
        start = time.time()

        nesting_types = []

        # Check depth
        depth = self.depth_analyzer.analyze(text)
        if depth > self.max_depth:
            nesting_types.append(NestingType.MULTI_LAYER)

        # Check patterns
        has_recursive, _ = self.pattern_detector.detect(text)
        if has_recursive:
            nesting_types.append(NestingType.RECURSIVE_CALL)

        # Check escapes
        has_escape, _ = self.escape_detector.detect(text)
        if has_escape:
            nesting_types.append(NestingType.ESCAPE_SEQUENCE)

        # Check nested prompt markers
        if "{{" in text and "}}" in text:
            if depth > 1:
                nesting_types.append(NestingType.NESTED_PROMPT)

        is_nested = len(nesting_types) > 0
        confidence = min(1.0, len(nesting_types) * 0.3 + depth * 0.1)

        if is_nested:
            logger.warning(
                f"Nested attack: {[n.value for n in nesting_types]}")

        return NestingResult(
            is_nested=is_nested,
            nesting_depth=depth,
            nesting_types=nesting_types,
            confidence=confidence,
            explanation=f"Depth: {depth}, Types: {len(nesting_types)}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_guard: Optional[RecursiveInjectionGuard] = None


def get_guard() -> RecursiveInjectionGuard:
    global _default_guard
    if _default_guard is None:
        _default_guard = RecursiveInjectionGuard()
    return _default_guard
