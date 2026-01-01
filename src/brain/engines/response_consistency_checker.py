"""
Response Consistency Checker Engine - Output Verification
Ensures response consistency.
Invention: Response Consistency Checker (#48 remaining)
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ResponseConsistencyChecker")


@dataclass
class ConsistencyResult:
    is_consistent: bool
    similarity: float = 1.0
    contradictions: List[str] = field(default_factory=list)
    latency_ms: float = 0.0


class ResponseConsistencyChecker:
    def __init__(self):
        self._history: Dict[str, str] = {}

    def check(self, query: str, response: str) -> ConsistencyResult:
        start = time.time()
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]

        contradictions = []
        similarity = 1.0

        if query_hash in self._history:
            prev = self._history[query_hash]
            common = set(prev.split()) & set(response.split())
            total = set(prev.split()) | set(response.split())
            similarity = len(common) / len(total) if total else 1.0

            if similarity < 0.3:
                contradictions.append(f"Low similarity: {similarity:.2f}")

        self._history[query_hash] = response
        is_consistent = len(contradictions) == 0

        if not is_consistent:
            logger.warning(f"Inconsistency: {contradictions}")

        return ConsistencyResult(
            is_consistent=is_consistent,
            similarity=similarity,
            contradictions=contradictions,
            latency_ms=(time.time() - start) * 1000,
        )
