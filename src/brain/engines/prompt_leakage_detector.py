"""
Prompt Leakage Detector Engine - System Prompt Protection

Detects system prompt leakage attempts:
- Extraction detection
- Leakage prevention
- Output scanning
- Fingerprint matching

Addresses: OWASP ASI-01 (Prompt Extraction)
Research: prompt_leakage_deep_dive.md
Invention: Prompt Leakage Detector (#47)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("PromptLeakageDetector")


# ============================================================================
# Data Classes
# ============================================================================


class LeakageType(Enum):
    """Types of leakage."""

    EXTRACTION_ATTEMPT = "extraction_attempt"
    PARTIAL_LEAK = "partial_leak"
    FULL_LEAK = "full_leak"
    FINGERPRINT_MATCH = "fingerprint_match"


@dataclass
class LeakageResult:
    """Result from leakage detection."""

    has_leakage: bool
    leakage_type: Optional[LeakageType] = None
    confidence: float = 0.0
    leaked_fragments: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "has_leakage": self.has_leakage,
            "leakage_type": self.leakage_type.value if self.leakage_type else None,
            "confidence": self.confidence,
            "leaked_fragments": self.leaked_fragments,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Extraction Detector
# ============================================================================


class ExtractionDetector:
    """Detects extraction attempts in input."""

    EXTRACTION_PATTERNS = [
        r"show\s*(me\s*)?(your\s*)?system\s*prompt",
        r"reveal\s*(your\s*)?instructions",
        r"what\s*(are\s*)?(your\s*)?original\s*instructions",
        r"print\s*(your\s*)?prompt",
        r"display\s*(your\s*)?rules",
        r"ignore.*show.*prompt",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self.EXTRACTION_PATTERNS
        ]

    def detect(self, text: str) -> Tuple[bool, float]:
        """Detect extraction attempt."""
        matches = 0
        for pattern in self._compiled:
            if pattern.search(text):
                matches += 1

        if matches > 0:
            return True, min(1.0, matches * 0.4)
        return False, 0.0


# ============================================================================
# Leakage Scanner
# ============================================================================


class LeakageScanner:
    """Scans output for leaked content."""

    LEAK_INDICATORS = [
        "you are a",
        "your role is",
        "system prompt:",
        "instructions:",
        "my instructions are",
        "i was told to",
        "i am programmed to",
    ]

    def scan(self, output: str,
             fingerprints: Set[str]) -> Tuple[bool, List[str]]:
        """Scan for leaked content."""
        output_lower = output.lower()
        leaked = []

        # Check indicators
        for indicator in self.LEAK_INDICATORS:
            if indicator in output_lower:
                leaked.append(indicator)

        # Check fingerprints
        for fp in fingerprints:
            if fp.lower() in output_lower:
                leaked.append(f"fingerprint:{fp[:20]}")

        return len(leaked) > 0, leaked


# ============================================================================
# Fingerprint Manager
# ============================================================================


class FingerprintManager:
    """Manages system prompt fingerprints."""

    def __init__(self):
        self._fingerprints: Set[str] = set()

    def add_fingerprint(self, text: str) -> None:
        """Add fingerprint from system prompt."""
        # Extract key phrases
        words = text.split()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i: i + 3])
            if len(phrase) > 10:
                self._fingerprints.add(phrase)

    def get_fingerprints(self) -> Set[str]:
        """Get all fingerprints."""
        return self._fingerprints.copy()

    def clear(self) -> None:
        """Clear fingerprints."""
        self._fingerprints.clear()


# ============================================================================
# Main Engine
# ============================================================================


class PromptLeakageDetector:
    """
    Prompt Leakage Detector - System Prompt Protection

    Detects:
    - Extraction attempts
    - Output leakage
    - Fingerprint matches

    Invention #47 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.extraction = ExtractionDetector()
        self.scanner = LeakageScanner()
        self.fingerprints = FingerprintManager()

        logger.info("PromptLeakageDetector initialized")

    def register_system_prompt(self, prompt: str) -> None:
        """Register system prompt for fingerprinting."""
        self.fingerprints.add_fingerprint(prompt)

    def check_input(self, text: str) -> LeakageResult:
        """Check input for extraction attempts."""
        start = time.time()

        is_extraction, confidence = self.extraction.detect(text)

        if is_extraction:
            logger.warning("Extraction attempt detected")

        return LeakageResult(
            has_leakage=is_extraction,
            leakage_type=LeakageType.EXTRACTION_ATTEMPT if is_extraction else None,
            confidence=confidence,
            explanation="Extraction attempt" if is_extraction else "Clean",
            latency_ms=(time.time() - start) * 1000,
        )

    def check_output(self, output: str) -> LeakageResult:
        """Check output for leaked content."""
        start = time.time()

        fps = self.fingerprints.get_fingerprints()
        has_leak, fragments = self.scanner.scan(output, fps)

        leakage_type = None
        if has_leak:
            if any("fingerprint:" in f for f in fragments):
                leakage_type = LeakageType.FINGERPRINT_MATCH
            elif len(fragments) > 3:
                leakage_type = LeakageType.FULL_LEAK
            else:
                leakage_type = LeakageType.PARTIAL_LEAK

            logger.warning(f"Leakage detected: {leakage_type.value}")

        return LeakageResult(
            has_leakage=has_leak,
            leakage_type=leakage_type,
            confidence=min(1.0, len(fragments) * 0.3),
            leaked_fragments=fragments,
            explanation=(
                f"Found {len(fragments)} leaked fragments" if has_leak else "Clean"
            ),
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_detector: Optional[PromptLeakageDetector] = None


def get_detector() -> PromptLeakageDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = PromptLeakageDetector()
    return _default_detector
