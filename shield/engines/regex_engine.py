"""
SENTINEL Shield v2.0 — Regex Detection Engine

Pattern-based detection using compiled regex from PatternStore.
This is the primary fast-path engine (< 1ms).
"""

import logging
from .base import BaseEngine, EngineResult, ThreatMatch
from pattern_loader import PatternStore, PatternCategory

logger = logging.getLogger("shield.engines.regex")


class RegexEngine(BaseEngine):
    """
    Fast regex-based detection engine.

    Checks text against all patterns in the store.
    Returns first match per category (configurable).
    """

    def __init__(
        self,
        store: PatternStore,
        weight: float = 1.0,
        max_matches_per_category: int = 1,
    ):
        super().__init__(name="regex", weight=weight)
        self.store = store
        self.max_matches_per_category = max_matches_per_category

    def update_store(self, store: PatternStore):
        """Hot-swap pattern store (thread-safe via copy-on-write)."""
        self.store = store
        logger.info(
            f"Regex engine store updated: {store.count} patterns v{store.version}"
        )

    def analyze(self, text: str) -> EngineResult:
        threats: list[ThreatMatch] = []
        max_risk = 0.0
        category_counts: dict[str, int] = {}

        text_lower = text.lower()

        for pattern in self.store.patterns:
            cat = pattern.category.value
            if category_counts.get(cat, 0) >= self.max_matches_per_category:
                continue

            if pattern.match(text_lower) or pattern.match(text):
                # Extract matched snippet
                m = pattern.compiled.search(text_lower) or pattern.compiled.search(text)
                matched_text = m.group(0)[:100] if m else ""

                threats.append(
                    ThreatMatch(
                        threat_type=pattern.category.value,
                        risk_score=pattern.severity,
                        engine=self.name,
                        description=pattern.description,
                        matched_text=matched_text,
                        category=cat,
                        metadata={
                            "source": pattern.source,
                            "match_type": pattern.match_type.value,
                        },
                    )
                )

                if pattern.severity > max_risk:
                    max_risk = pattern.severity

                category_counts[cat] = category_counts.get(cat, 0) + 1

        return EngineResult(
            engine_name=self.name,
            risk_score=max_risk,
            threats=threats,
        )
