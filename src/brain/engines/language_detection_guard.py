"""
Language Detection Guard Engine - Multilingual Attack Defense
Detects language-based attacks.
Invention: Language Detection Guard (#47 remaining)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("LanguageDetectionGuard")


@dataclass
class LanguageResult:
    is_suspicious: bool
    detected_languages: List[str] = field(default_factory=list)
    mixed_script: bool = False
    risk_score: float = 0.0
    latency_ms: float = 0.0


class LanguageDetectionGuard:
    SCRIPT_PATTERNS = {
        "latin": re.compile(r"[a-zA-Z]"),
        "cyrillic": re.compile(r"[\u0400-\u04FF]"),
        "arabic": re.compile(r"[\u0600-\u06FF]"),
        "chinese": re.compile(r"[\u4E00-\u9FFF]"),
        "japanese": re.compile(r"[\u3040-\u309F\u30A0-\u30FF]"),
    }

    def analyze(self, text: str) -> LanguageResult:
        start = time.time()
        detected = []

        for lang, pattern in self.SCRIPT_PATTERNS.items():
            if pattern.search(text):
                detected.append(lang)

        mixed = len(detected) > 1
        is_suspicious = mixed and "cyrillic" in detected and "latin" in detected
        risk = 0.3 * len(detected) if mixed else 0.0

        if is_suspicious:
            logger.warning(f"Mixed scripts: {detected}")

        return LanguageResult(
            is_suspicious=is_suspicious,
            detected_languages=detected,
            mixed_script=mixed,
            risk_score=min(1.0, risk),
            latency_ms=(time.time() - start) * 1000,
        )
