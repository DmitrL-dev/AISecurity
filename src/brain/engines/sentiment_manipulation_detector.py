"""
Sentiment Manipulation Detector Engine - Emotional Attack Defense
Detects sentiment manipulation attacks.
Invention: Sentiment Manipulation Detector (#49 - FINAL!)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SentimentManipulationDetector")


class Sentiment(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MANIPULATIVE = "manipulative"


@dataclass
class SentimentResult:
    is_manipulative: bool
    sentiment: Sentiment
    manipulation_score: float = 0.0
    triggers: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


class SentimentManipulationDetector:
    MANIPULATION_PATTERNS = [
        (r"you must", "urgency"),
        (r"immediately", "urgency"),
        (r"trust me", "social_engineering"),
        (r"don't tell anyone", "secrecy"),
        (r"this is urgent", "pressure"),
        (r"everyone does this", "normalization"),
        (r"you'll regret", "threat"),
        (r"i'm dying", "sympathy"),
    ]

    POSITIVE = ["good", "great", "happy", "love", "excellent"]
    NEGATIVE = ["bad", "hate", "terrible", "awful", "angry"]

    def __init__(self):
        self._compiled = [
            (re.compile(p, re.I), t) for p, t in self.MANIPULATION_PATTERNS
        ]

    def analyze(self, text: str) -> SentimentResult:
        start = time.time()
        text_lower = text.lower()

        triggers = []
        for pattern, trigger in self._compiled:
            if pattern.search(text):
                triggers.append(trigger)

        pos = sum(1 for w in self.POSITIVE if w in text_lower)
        neg = sum(1 for w in self.NEGATIVE if w in text_lower)

        if triggers:
            sentiment = Sentiment.MANIPULATIVE
        elif pos > neg:
            sentiment = Sentiment.POSITIVE
        elif neg > pos:
            sentiment = Sentiment.NEGATIVE
        else:
            sentiment = Sentiment.NEUTRAL

        is_manipulative = len(triggers) > 0
        score = min(1.0, len(triggers) * 0.25)

        if is_manipulative:
            logger.warning(f"Manipulation: {triggers}")

        return SentimentResult(
            is_manipulative=is_manipulative,
            sentiment=sentiment,
            manipulation_score=score,
            triggers=triggers,
            latency_ms=(time.time() - start) * 1000,
        )
