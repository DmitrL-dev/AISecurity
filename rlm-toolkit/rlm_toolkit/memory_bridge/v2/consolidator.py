"""
Fact Consolidator for Memory Bridge v2.3

Aggregates granular facts (L3→L2→L1) to reduce noise and improve signal.
Also deduplicates semantically similar facts.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from .hierarchical import (
    MemoryLevel,
    HierarchicalMemoryStore,
    HierarchicalFact,
)

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationResult:
    """Result of fact consolidation."""

    merged_count: int = 0
    promoted_count: int = 0
    archived_count: int = 0
    new_summaries: List[str] = None

    def __post_init__(self):
        if self.new_summaries is None:
            self.new_summaries = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merged_count": self.merged_count,
            "promoted_count": self.promoted_count,
            "archived_count": self.archived_count,
            "new_summaries": self.new_summaries,
        }


class FactConsolidator:
    """
    Consolidates facts by:
    1. Grouping L3→L2 facts by module
    2. Grouping L2→L1 facts by domain
    3. Deduplicating semantically similar facts
    4. Archiving redundant facts
    """

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        min_facts_to_consolidate: int = 5,
        similarity_threshold: float = 0.8,
    ):
        self.store = store
        self.min_facts_to_consolidate = min_facts_to_consolidate
        self.similarity_threshold = similarity_threshold

    def consolidate(self) -> ConsolidationResult:
        """
        Run full consolidation: L3→L2→L1 + dedup.

        Returns:
            ConsolidationResult with stats
        """
        result = ConsolidationResult()

        # Step 1: Consolidate L3 → L2
        l3_result = self._consolidate_level(
            MemoryLevel.L3_CODE,
            MemoryLevel.L2_MODULE,
            group_by="module",
        )
        result.merged_count += l3_result.merged_count
        result.promoted_count += l3_result.promoted_count
        result.new_summaries.extend(l3_result.new_summaries)

        # Step 2: Consolidate L2 → L1
        l2_result = self._consolidate_level(
            MemoryLevel.L2_MODULE,
            MemoryLevel.L1_DOMAIN,
            group_by="domain",
        )
        result.merged_count += l2_result.merged_count
        result.promoted_count += l2_result.promoted_count
        result.new_summaries.extend(l2_result.new_summaries)

        # Step 3: Deduplicate within levels
        dedup_count = self._deduplicate_all()
        result.archived_count = dedup_count

        logger.info(f"Consolidation complete: {result.to_dict()}")
        return result

    def _consolidate_level(
        self,
        source_level: MemoryLevel,
        target_level: MemoryLevel,
        group_by: str,
    ) -> ConsolidationResult:
        """Consolidate facts from source level to target level."""
        result = ConsolidationResult()

        facts = self.store.get_facts_by_level(source_level)
        if len(facts) < self.min_facts_to_consolidate:
            return result

        # Group facts
        groups: Dict[str, List[HierarchicalFact]] = {}
        for fact in facts:
            key = getattr(fact, group_by, None) or "unknown"
            if key not in groups:
                groups[key] = []
            groups[key].append(fact)

        # Create summaries for each group
        for key, group_facts in groups.items():
            if len(group_facts) >= self.min_facts_to_consolidate:
                summary = self._create_summary(group_facts, key, target_level)
                if summary:
                    result.new_summaries.append(summary)
                    result.merged_count += len(group_facts)
                    result.promoted_count += 1

                    # Archive original facts
                    for fact in group_facts:
                        self.store.archive_fact(fact.id)

        return result

    def _create_summary(
        self,
        facts: List[HierarchicalFact],
        group_key: str,
        target_level: MemoryLevel,
    ) -> Optional[str]:
        """Create a summary fact from multiple related facts."""
        if not facts:
            return None

        # Simple summary: count + key topics
        contents = [f.content[:50] for f in facts]
        unique_topics = list(set(contents))[:3]

        summary_content = (
            f"[{group_key}] {len(facts)} related facts about: "
            + "; ".join(unique_topics)
        )

        # Add to store
        self.store.add_fact(
            content=summary_content,
            level=target_level,
            domain=facts[0].domain if facts else None,
            module=group_key if target_level == MemoryLevel.L2_MODULE else None,
            source="consolidation",
            confidence=0.85,
        )

        return summary_content

    def _deduplicate_all(self) -> int:
        """Deduplicate semantically similar facts."""
        archived_count = 0

        for level in [MemoryLevel.L1_DOMAIN, MemoryLevel.L2_MODULE]:
            facts = self.store.get_facts_by_level(level)
            duplicates = self._find_duplicates(facts)

            for dup_id in duplicates:
                self.store.archive_fact(dup_id)
                archived_count += 1

        return archived_count

    def _find_duplicates(self, facts: List[HierarchicalFact]) -> List[str]:
        """Find duplicate fact IDs based on content similarity."""
        duplicates: List[str] = []
        seen_contents: Dict[str, str] = {}  # content_hash -> fact_id

        for fact in facts:
            content_key = fact.content.lower()[:100]

            # Check for similar existing
            found_similar = False
            for existing_key, existing_id in seen_contents.items():
                similarity = self._text_similarity(content_key, existing_key)
                if similarity >= self.similarity_threshold:
                    duplicates.append(fact.id)
                    found_similar = True
                    break

            if not found_similar:
                seen_contents[content_key] = fact.id

        return duplicates

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple text similarity (Jaccard)."""
        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0
