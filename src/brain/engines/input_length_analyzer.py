"""
Input Length Analyzer Engine - Size-Based Attack Detection
Detects attacks via abnormal input lengths.
Invention: Input Length Analyzer (#46 remaining)
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("InputLengthAnalyzer")


@dataclass
class LengthResult:
    is_anomaly: bool
    char_count: int
    word_count: int
    line_count: int
    risk_score: float = 0.0
    latency_ms: float = 0.0


class InputLengthAnalyzer:
    def __init__(self, max_chars: int = 10000, max_words: int = 2000):
        self.max_chars = max_chars
        self.max_words = max_words

    def analyze(self, text: str) -> LengthResult:
        start = time.time()
        chars = len(text)
        words = len(text.split())
        lines = text.count("\n") + 1

        risk = 0.0
        if chars > self.max_chars:
            risk += 0.5
        if words > self.max_words:
            risk += 0.3
        if lines > 100:
            risk += 0.2

        is_anomaly = risk > 0.3
        if is_anomaly:
            logger.warning(f"Length anomaly: {chars} chars, {words} words")

        return LengthResult(
            is_anomaly=is_anomaly,
            char_count=chars,
            word_count=words,
            line_count=lines,
            risk_score=min(1.0, risk),
            latency_ms=(time.time() - start) * 1000,
        )
