"""
Conversation Extractor - Extract decisions from agent conversation.

Detects patterns like:
- "решил использовать X потому что Y"
- "выбрал подход X для Y"
- "создал/добавил X для Y"
"""

import re
from pathlib import Path
from time import perf_counter
from typing import Optional

from .base import BaseExtractor, ExtractionResult, FactCandidate


class ConversationExtractor(BaseExtractor):
    """Extract decisions from conversation history."""

    name = "conversation"

    # Decision patterns (Russian and English)
    DECISION_PATTERNS = [
        # Russian
        (
            r"решил использовать\s+(.+?)\s+(?:потому что|для|чтобы)\s+(.+?)(?:\.|$)",
            0.85,
        ),
        (
            r"выбрал\s+(?:подход|вариант|решение)?\s*(.+?)\s+(?:для|потому что)\s+(.+?)(?:\.|$)",
            0.85,
        ),
        (r"создал\s+(.+?)\s+для\s+(.+?)(?:\.|$)", 0.75),
        (r"добавил\s+(.+?)\s+(?:для|чтобы)\s+(.+?)(?:\.|$)", 0.75),
        (r"исправил\s+(.+?)\s+(?:потому что|из-за)\s+(.+?)(?:\.|$)", 0.8),
        (r"использую\s+(.+?)\s+(?:вместо|потому что)\s+(.+?)(?:\.|$)", 0.8),
        # English
        (r"decided to use\s+(.+?)\s+(?:because|for|to)\s+(.+?)(?:\.|$)", 0.85),
        (
            r"chose\s+(.+?)\s+(?:approach|solution)?\s*(?:for|because)\s+(.+?)(?:\.|$)",
            0.85,
        ),
        (r"created\s+(.+?)\s+(?:for|to)\s+(.+?)(?:\.|$)", 0.75),
        (r"added\s+(.+?)\s+(?:for|to)\s+(.+?)(?:\.|$)", 0.75),
        (r"fixed\s+(.+?)\s+(?:because|due to)\s+(.+?)(?:\.|$)", 0.8),
        (r"using\s+(.+?)\s+(?:instead of|because)\s+(.+?)(?:\.|$)", 0.8),
    ]

    # Commit message patterns
    COMMIT_PATTERNS = [
        (r"^feat\((\w+)\):\s*(.+)", "feature", 0.85),
        (r"^fix\((\w+)\):\s*(.+)", "fix", 0.8),
        (r"^refactor\((\w+)\):\s*(.+)", "refactor", 0.75),
        (r"^perf\((\w+)\):\s*(.+)", "performance", 0.8),
        (r"^docs\((\w+)\):\s*(.+)", "docs", 0.7),
    ]

    def __init__(self, project_root: Path, messages: list[dict] = None):
        super().__init__(project_root)
        self.messages = messages or []

    async def extract(self) -> ExtractionResult:
        """Extract decisions from conversation messages."""
        start = perf_counter()
        result = ExtractionResult(source=self.name)

        for msg in self.messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                candidates = self._extract_from_text(content)
                result.candidates.extend(candidates)

        # Categorize
        for c in result.candidates:
            if c.should_auto_approve():
                result.auto_approved += 1
            elif c.should_drop():
                result.dropped += 1
            else:
                result.pending_review += 1

        result.duration_ms = (perf_counter() - start) * 1000
        return result

    def _extract_from_text(self, text: str) -> list[FactCandidate]:
        """Extract decision patterns from text."""
        candidates = []

        # Split into sentences
        sentences = re.split(r"[.!?\n]", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue

            for pattern, confidence in self.DECISION_PATTERNS:
                match = re.search(pattern, sentence, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        what, why = groups[0], groups[1]
                        full_decision = f"{what}: {why}"
                    else:
                        full_decision = sentence

                    candidates.append(
                        self._create_candidate(
                            content=full_decision,
                            confidence=confidence,
                            level=2,  # Module level
                        )
                    )
                    break  # One match per sentence

        return candidates

    async def extract_from_commit(self, commit_msg: str) -> list[FactCandidate]:
        """Extract from a single commit message."""
        candidates = []

        for pattern, fact_type, confidence in self.COMMIT_PATTERNS:
            match = re.match(pattern, commit_msg, re.IGNORECASE)
            if match:
                domain = match.group(1)
                description = match.group(2)

                candidates.append(
                    self._create_candidate(
                        content=f"[{fact_type}] {domain}: {description}",
                        confidence=confidence,
                        domain=domain,
                        level=2,
                    )
                )
                break

        return candidates
