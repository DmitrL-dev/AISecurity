"""
Extraction Orchestrator - Coordinates all extractors.

Provides unified interface for running multiple extractors
and aggregating results.
"""

import asyncio
from pathlib import Path
from time import perf_counter
from typing import Optional

from .base import ExtractionResult, FactCandidate
from .code_extractor import CodeExtractor
from .config_extractor import ConfigExtractor
from .conversation_extractor import ConversationExtractor
from .git_extractor import GitExtractor


class ExtractionOrchestrator:
    """Orchestrates multiple extractors for deep discovery."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    async def discover_deep(
        self,
        extractors: list[str] = None,
        auto_approve: bool = False,
        max_facts: int = 100,
        messages: list[dict] = None,
    ) -> dict:
        """
        Run deep discovery with multiple extractors.

        Args:
            extractors: List of extractor names to run
                       ["code", "config", "git", "conversation"]
            auto_approve: If True, auto-approve all (ignore confidence)
            max_facts: Maximum facts to return
            messages: Conversation messages for conversation extractor

        Returns:
            Discovery result with candidates and stats
        """
        start = perf_counter()

        # Default: all extractors except conversation
        if extractors is None:
            extractors = ["code", "config", "git"]

        results: list[ExtractionResult] = []

        # Run extractors in parallel
        tasks = []

        if "code" in extractors:
            extractor = CodeExtractor(self.project_root)
            tasks.append(("code", extractor.extract()))

        if "config" in extractors:
            extractor = ConfigExtractor(self.project_root)
            tasks.append(("config", extractor.extract()))

        if "git" in extractors:
            extractor = GitExtractor(self.project_root)
            tasks.append(("git", extractor.extract()))

        if "conversation" in extractors and messages:
            extractor = ConversationExtractor(self.project_root, messages=messages)
            tasks.append(("conversation", extractor.extract()))

        # Execute all
        for name, coro in tasks:
            try:
                result = await coro
                results.append(result)
            except Exception as e:
                results.append(ExtractionResult(source=name, errors=[str(e)]))

        # Aggregate candidates
        all_candidates = []
        for result in results:
            all_candidates.extend(result.candidates)

        # Deduplicate by content similarity
        unique_candidates = self._deduplicate(all_candidates)

        # Apply max_facts limit
        unique_candidates = unique_candidates[:max_facts]

        # If auto_approve, bump all confidence to 1.0
        if auto_approve:
            for c in unique_candidates:
                c.confidence = 1.0
                c.requires_approval = False

        # Calculate totals
        auto_approved = sum(1 for c in unique_candidates if c.should_auto_approve())
        pending = sum(
            1
            for c in unique_candidates
            if not c.should_auto_approve() and not c.should_drop()
        )
        dropped = sum(1 for c in unique_candidates if c.should_drop())

        # Extract domains
        domains = set()
        for c in unique_candidates:
            if c.domain:
                domains.add(c.domain)

        duration_ms = (perf_counter() - start) * 1000

        return {
            "status": "success",
            "facts_extracted": len(unique_candidates),
            "auto_approved": auto_approved,
            "pending_review": pending,
            "dropped": dropped,
            "domains_found": list(domains),
            "candidates": [
                {
                    "id": c.id,
                    "content": c.content,
                    "source": c.source,
                    "confidence": c.confidence,
                    "domain": c.domain,
                    "level": c.level,
                    "requires_approval": c.requires_approval,
                    "file_path": c.file_path,
                    "line_number": c.line_number,
                }
                for c in unique_candidates
            ],
            "extractor_results": [
                {
                    "source": r.source,
                    "count": len(r.candidates),
                    "duration_ms": r.duration_ms,
                    "errors": r.errors,
                }
                for r in results
            ],
            "duration_ms": duration_ms,
        }

    def _deduplicate(self, candidates: list[FactCandidate]) -> list[FactCandidate]:
        """Remove duplicate candidates by content similarity."""
        seen_content = set()
        unique = []

        for c in candidates:
            # Normalize content for comparison
            normalized = c.content.lower().strip()[:100]

            if normalized not in seen_content:
                seen_content.add(normalized)
                unique.append(c)

        # Sort by confidence (highest first)
        unique.sort(key=lambda x: x.confidence, reverse=True)

        return unique
