"""
Base classes for RLM extractors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ConfidenceLevel(Enum):
    """Confidence thresholds for auto-approve."""

    HIGH = 0.8  # Auto-approve
    MEDIUM = 0.5  # Candidate for review
    LOW = 0.0  # Drop


@dataclass
class FactCandidate:
    """A candidate fact extracted from source, pending approval."""

    id: str
    content: str
    source: str  # "code" | "conversation" | "git" | "config"
    confidence: float  # 0.0 - 1.0

    # Classification
    domain: Optional[str] = None
    level: int = 1  # L0-L3

    # Metadata
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    commit_sha: Optional[str] = None

    # State
    requires_approval: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)

    def should_auto_approve(self) -> bool:
        """Check if confidence is high enough for auto-approve."""
        return self.confidence >= ConfidenceLevel.HIGH.value

    def should_drop(self) -> bool:
        """Check if confidence is too low."""
        return self.confidence < ConfidenceLevel.MEDIUM.value


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""

    source: str
    candidates: list[FactCandidate] = field(default_factory=list)
    auto_approved: int = 0
    pending_review: int = 0
    dropped: int = 0
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def summary(self) -> str:
        """Generate summary string."""
        return (
            f"[{self.source}] "
            f"extracted={len(self.candidates)}, "
            f"auto={self.auto_approved}, "
            f"pending={self.pending_review}, "
            f"dropped={self.dropped}"
        )


class BaseExtractor(ABC):
    """Abstract base class for all extractors."""

    name: str = "base"

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)

    @abstractmethod
    async def extract(self) -> ExtractionResult:
        """
        Extract facts from the source.

        Returns:
            ExtractionResult with candidates and stats
        """
        pass

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for a fact candidate."""
        import hashlib

        hash_input = f"{self.name}:{content[:100]}"
        return f"ext_{self.name}_{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"

    def _create_candidate(
        self,
        content: str,
        confidence: float,
        domain: Optional[str] = None,
        level: int = 1,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ) -> FactCandidate:
        """Helper to create a FactCandidate."""
        candidate = FactCandidate(
            id=self._generate_id(content),
            content=content,
            source=self.name,
            confidence=confidence,
            domain=domain,
            level=level,
            file_path=file_path,
            line_number=line_number,
            requires_approval=confidence < ConfidenceLevel.HIGH.value,
        )
        return candidate
