"""
Knowledge Freshness and Actuality Detection.

Tracks whether indexed knowledge is still current and valid.
"""

import re
import time
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rlm_freshness")


class KnowledgeType(Enum):
    """Types of knowledge in a project."""

    CODE = "code"
    ARCHITECTURE = "arch"
    UI_UX = "ui_ux"
    LOGIC = "logic"
    DEPENDENCY = "deps"
    DOCUMENTATION = "docs"
    CONTEXT = "context"
    RESEARCH = "research"


@dataclass
class FreshnessMetadata:
    """Track freshness of indexed content."""

    indexed_at: float
    source_mtime: float
    source_hash: str
    ttl_hours: int = 24
    last_validated: Optional[float] = None
    human_confirmed: bool = False

    @property
    def age_hours(self) -> float:
        return (time.time() - self.indexed_at) / 3600

    @property
    def is_stale(self) -> bool:
        return self.age_hours > self.ttl_hours

    @property
    def needs_revalidation(self) -> bool:
        if self.last_validated is None:
            return self.age_hours > 24
        since_validation = (time.time() - self.last_validated) / 3600
        return since_validation > 168  # 1 week

    def validate(self):
        """Mark as validated now."""
        self.last_validated = time.time()

    def confirm(self):
        """Human confirmed as current."""
        self.human_confirmed = True
        self.last_validated = time.time()

    @classmethod
    def from_file(cls, path: Path, ttl_hours: int = 24) -> "FreshnessMetadata":
        """Create from file path."""
        content = path.read_bytes()
        return cls(
            indexed_at=time.time(),
            source_mtime=path.stat().st_mtime,
            source_hash=hashlib.sha256(content).hexdigest()[:16],
            ttl_hours=ttl_hours,
        )


@dataclass
class ObsoleteMarker:
    """Marker indicating potentially obsolete code."""

    pattern: str
    line: int
    context: str
    severity: str = "warning"


class ObsolescenceDetector:
    """Detect markers of obsolete or deprecated code."""

    # Patterns indicating obsolescence
    PATTERNS = [
        (r"@deprecated", "high"),
        (r"#\s*TODO:", "low"),
        (r"#\s*FIXME:", "medium"),
        (r"#\s*HACK:", "medium"),
        (r"#\s*XXX:", "medium"),
        (r"warnings\.warn\(.*DeprecationWarning", "high"),
        (r"#\s*OLD:", "high"),
        (r"#\s*LEGACY:", "high"),
        (r"#\s*OBSOLETE:", "high"),
        (r"DeprecationWarning", "high"),
        (r"PendingDeprecationWarning", "medium"),
    ]

    def scan(self, content: str) -> List[ObsoleteMarker]:
        """Scan content for obsolescence markers."""
        markers = []

        for pattern, severity in self.PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                markers.append(
                    ObsoleteMarker(
                        pattern=pattern,
                        line=line_num,
                        context=match.group(0),
                        severity=severity,
                    )
                )

        return markers

    def has_obsolescence(self, content: str) -> bool:
        """Quick check if content has any obsolescence markers."""
        return len(self.scan(content)) > 0


@dataclass
class BrokenReference:
    """A reference that no longer exists."""

    type: str  # missing_import, deprecated_import, missing_function
    name: str
    file: str
    line: Optional[int] = None
    replacement: Optional[str] = None


class CrossReferenceValidator:
    """Validate cross-references between files."""

    def __init__(self, project_crystals: Dict[str, Any]):
        self.crystals = project_crystals
        self._build_index()

    def _build_index(self):
        """Build index of all defined symbols."""
        self.defined_functions = set()
        self.defined_classes = set()
        self.defined_all = set()

        for path, crystal in self.crystals.items():
            # Handle dict or object
            if isinstance(crystal, dict):
                primitives = crystal.get("primitives", [])
            else:
                primitives = crystal.primitives

            for prim in primitives:
                ptype = prim.get("ptype") if isinstance(prim, dict) else prim.ptype
                name = prim.get("name") if isinstance(prim, dict) else prim.name

                if ptype == "FUNCTION":
                    self.defined_functions.add(name)
                    self.defined_all.add(name)
                elif ptype == "CLASS":
                    self.defined_classes.add(name)
                    self.defined_all.add(name)
                elif ptype == "METHOD":
                    self.defined_all.add(name.split(".")[-1])

    def validate_references(self, crystal) -> List[BrokenReference]:
        """Check if references in crystal still exist."""
        broken = []

        # Handle dict or object
        if isinstance(crystal, dict):
            primitives = crystal.get("primitives", [])
            crystal_path = crystal.get("path", "")
        else:
            primitives = crystal.primitives
            crystal_path = crystal.path

        # Check call relations
        for prim in primitives:
            ptype = prim.get("ptype") if isinstance(prim, dict) else prim.ptype
            name = prim.get("name") if isinstance(prim, dict) else prim.name
            line = (
                prim.get("source_line") if isinstance(prim, dict) else prim.source_line
            )

            if ptype == "RELATION" and "->calls->" in name:
                parts = name.split("->calls->")
                if len(parts) == 2:
                    called = parts[1]
                    # Check if called function exists in project
                    if called not in self.defined_all:
                        # Could be external, only flag if looks internal
                        if not called.startswith("_") and called[0].islower():
                            broken.append(
                                BrokenReference(
                                    type="possibly_missing_call",
                                    name=called,
                                    file=crystal_path,
                                    line=line,
                                )
                            )

        return broken

    def get_validation_stats(self) -> Dict[str, int]:
        """Get validation statistics."""
        return {
            "defined_functions": len(self.defined_functions),
            "defined_classes": len(self.defined_classes),
            "total_symbols": len(self.defined_all),
        }


class ActualityScorer:
    """Calculate actuality score for knowledge entries."""

    def __init__(self):
        self.obsolescence_detector = ObsolescenceDetector()

    def calculate(
        self,
        content: str,
        freshness: FreshnessMetadata,
        broken_refs: int = 0,
    ) -> float:
        """
        Calculate actuality score 0.0 - 1.0.

        Factors:
        - Time decay
        - Last validation
        - Obsolescence markers
        - Broken references
        - Human confirmation
        """
        score = 1.0

        # 1. Time decay (lose 50% over a year)
        age_days = freshness.age_hours / 24
        score *= max(0.5, 1.0 - (age_days / 365))

        # 2. Validation freshness
        if freshness.needs_revalidation:
            score *= 0.8

        # 3. Obsolescence markers
        markers = self.obsolescence_detector.scan(content)
        high_severity = sum(1 for m in markers if m.severity == "high")
        if high_severity > 0:
            score *= 0.5
        elif len(markers) > 0:
            score *= 0.8

        # 4. Broken references
        if broken_refs > 0:
            score *= max(0.3, 1.0 - (broken_refs * 0.1))

        # 5. Human confirmation boost
        if freshness.human_confirmed:
            score = min(1.0, score + 0.3)

        return round(score, 2)

    def explain_score(
        self,
        content: str,
        freshness: FreshnessMetadata,
    ) -> Dict[str, Any]:
        """Explain why score is what it is."""
        reasons = []

        if freshness.age_hours > 168:  # 1 week
            reasons.append(f"Indexed {freshness.age_hours/24:.0f} days ago")

        if freshness.needs_revalidation:
            reasons.append("Not validated recently")

        markers = self.obsolescence_detector.scan(content)
        if markers:
            reasons.append(f"Contains {len(markers)} obsolescence markers")

        if freshness.human_confirmed:
            reasons.append("Human confirmed as current")

        return {
            "score": self.calculate(content, freshness),
            "reasons": reasons,
            "markers": [m.context for m in markers[:5]],
        }


@dataclass
class ReviewItem:
    """Item needing human review."""

    path: str
    knowledge_type: KnowledgeType
    score: float
    reasons: List[str]
    question: str = "Is this still current?"


class ActualityReviewQueue:
    """Generate queue of items needing human review."""

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.scorer = ActualityScorer()

    def generate_queue(
        self,
        crystals: Dict[str, Any],
        freshness_data: Dict[str, FreshnessMetadata],
    ) -> List[ReviewItem]:
        """Generate review queue sorted by urgency."""
        queue = []

        for path, crystal in crystals.items():
            freshness = freshness_data.get(path)
            if not freshness:
                continue

            content = getattr(crystal, "raw_content", "")
            explanation = self.scorer.explain_score(content, freshness)

            if explanation["score"] < self.threshold:
                queue.append(
                    ReviewItem(
                        path=path,
                        knowledge_type=KnowledgeType.CODE,
                        score=explanation["score"],
                        reasons=explanation["reasons"],
                    )
                )

        return sorted(queue, key=lambda x: x.score)


# Convenience functions
def check_file_freshness(path: Path, indexed_meta: FreshnessMetadata) -> bool:
    """Check if file has changed since indexing."""
    if not path.exists():
        return False  # File deleted

    current_mtime = path.stat().st_mtime
    return current_mtime == indexed_meta.source_mtime


def detect_staleness(path: Path, freshness: FreshnessMetadata) -> Dict[str, Any]:
    """Comprehensive staleness check."""
    result = {
        "path": str(path),
        "is_stale": False,
        "reasons": [],
    }

    # Check if file changed
    if not check_file_freshness(path, freshness):
        result["is_stale"] = True
        result["reasons"].append("File modified since indexing")

    # Check TTL
    if freshness.is_stale:
        result["is_stale"] = True
        result["reasons"].append(
            f"TTL expired ({freshness.age_hours:.0f}h > {freshness.ttl_hours}h)"
        )

    # Check needs revalidation
    if freshness.needs_revalidation:
        result["is_stale"] = True
        result["reasons"].append("Needs revalidation")

    return result
