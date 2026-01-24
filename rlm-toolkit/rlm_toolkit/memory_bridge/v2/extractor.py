"""
Auto-Extraction Engine for Memory Bridge v2.0

Automatically extracts facts from:
- Git diffs
- Code changes
- File modifications
- AST analysis
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import re
import subprocess

from .hierarchical import MemoryLevel, HierarchicalFact, TTLConfig

logger = logging.getLogger(__name__)


@dataclass
class CandidateFact:
    """A candidate fact extracted from code changes."""

    content: str
    confidence: float  # 0.0-1.0
    source: str  # "git_diff", "file_change", "ast_analysis"
    suggested_level: MemoryLevel
    suggested_domain: Optional[str] = None
    suggested_module: Optional[str] = None
    file_path: Optional[str] = None
    line_range: Optional[Tuple[int, int]] = None
    requires_approval: bool = True  # True if confidence < 0.8
    approved: bool = False
    rejected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "confidence": self.confidence,
            "source": self.source,
            "suggested_level": self.suggested_level.value,
            "suggested_domain": self.suggested_domain,
            "suggested_module": self.suggested_module,
            "file_path": self.file_path,
            "line_range": self.line_range,
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "rejected": self.rejected,
        }


@dataclass
class ExtractionResult:
    """Result of fact extraction."""

    candidates: List[CandidateFact]
    auto_approved: int = 0
    pending_approval: int = 0
    total_changes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidates": [c.to_dict() for c in self.candidates],
            "auto_approved": self.auto_approved,
            "pending_approval": self.pending_approval,
            "total_changes": self.total_changes,
        }


class AutoExtractionEngine:
    """
    Engine for automatically extracting facts from code changes.

    Supports:
    - Git diff parsing
    - File change detection
    - AST analysis (basic)
    - Semantic deduplication
    """

    # Patterns for extracting information from diffs
    # Note: additions are already stripped of + prefix by _parse_diff
    NEW_FILE_PATTERN = re.compile(r"^diff --git a/.+ b/(.+)$", re.MULTILINE)
    FUNCTION_PATTERN = re.compile(r"^\s*(async\s+)?def\s+(\w+)\s*\(", re.MULTILINE)
    CLASS_PATTERN = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
    METHOD_PATTERN = re.compile(r"^\s+(?:async\s+)?def\s+(\w+)\s*\(self", re.MULTILINE)
    IMPORT_PATTERN = re.compile(r"^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$", re.MULTILINE)

    # Templates for generating facts
    TEMPLATES = {
        "new_file": "Added {filename} implementing {purpose}",
        "new_function": "Implemented function `{func_name}` in {module}",
        "new_class": "Added class `{class_name}` in {module}",
        "new_method": "Added method `{method_name}` to {class_name}",
        "major_change": "Refactored {module} ({lines} lines changed)",
        "api_change": "Modified API in {module}: {change_summary}",
        "new_import": "Added dependency on {package}",
        "config_change": "Updated configuration: {change_summary}",
    }

    # Domain inference from file paths
    DOMAIN_PATTERNS = {
        r"auth|login|user|session": "auth",
        r"api|endpoint|route": "api",
        r"db|database|model|schema": "database",
        r"test|spec": "testing",
        r"config|setting": "config",
        r"util|helper|common": "utilities",
        r"ui|frontend|view|component": "frontend",
        r"core|engine|main": "core",
    }

    def __init__(
        self,
        project_root: Optional[Path] = None,
        confidence_threshold: float = 0.8,
        min_change_lines: int = 5,
    ):
        self.project_root = project_root or Path.cwd()
        self.confidence_threshold = confidence_threshold
        self.min_change_lines = min_change_lines

    def extract_from_git_diff(
        self,
        diff: Optional[str] = None,
        staged_only: bool = False,
    ) -> ExtractionResult:
        """
        Extract facts from git diff.

        Args:
            diff: Pre-computed diff string (if None, runs git diff)
            staged_only: Only look at staged changes

        Returns:
            ExtractionResult with candidate facts
        """
        if diff is None:
            diff = self._get_git_diff(staged_only)

        if not diff:
            return ExtractionResult(candidates=[], total_changes=0)

        candidates: List[CandidateFact] = []

        # Parse diff into file changes
        file_changes = self._parse_diff(diff)

        for file_path, changes in file_changes.items():
            file_candidates = self._extract_from_file_changes(file_path, changes)
            candidates.extend(file_candidates)

        # Count approvals
        auto_approved = sum(1 for c in candidates if not c.requires_approval)
        pending = sum(1 for c in candidates if c.requires_approval)

        return ExtractionResult(
            candidates=candidates,
            auto_approved=auto_approved,
            pending_approval=pending,
            total_changes=len(file_changes),
        )

    def extract_from_file(
        self,
        file_path: Path,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract facts from a specific file change.

        Args:
            file_path: Path to the changed file
            old_content: Previous content (None if new file)
            new_content: New content (None if deleted)

        Returns:
            ExtractionResult with candidate facts
        """
        candidates: List[CandidateFact] = []

        if new_content is None:
            # File deleted
            candidates.append(
                CandidateFact(
                    content=f"Deleted file {file_path.name}",
                    confidence=0.9,
                    source="file_change",
                    suggested_level=MemoryLevel.L2_MODULE,
                    suggested_domain=self._infer_domain(str(file_path)),
                    file_path=str(file_path),
                    requires_approval=True,
                )
            )
        elif old_content is None:
            # New file
            purpose = self._guess_file_purpose(file_path, new_content)
            candidates.append(
                CandidateFact(
                    content=f"Added {file_path.name} for {purpose}",
                    confidence=0.85,
                    source="file_change",
                    suggested_level=MemoryLevel.L1_DOMAIN,
                    suggested_domain=self._infer_domain(str(file_path)),
                    file_path=str(file_path),
                    requires_approval=False,
                )
            )

            # Extract functions/classes from new file
            candidates.extend(self._extract_from_new_file(file_path, new_content))
        else:
            # Modified file
            lines_changed = abs(
                len(new_content.splitlines()) - len(old_content.splitlines())
            )
            if lines_changed >= self.min_change_lines:
                candidates.append(
                    CandidateFact(
                        content=f"Modified {file_path.name} ({lines_changed} lines changed)",
                        confidence=0.7,
                        source="file_change",
                        suggested_level=MemoryLevel.L2_MODULE,
                        suggested_domain=self._infer_domain(str(file_path)),
                        file_path=str(file_path),
                        requires_approval=True,
                    )
                )

        auto_approved = sum(1 for c in candidates if not c.requires_approval)
        pending = sum(1 for c in candidates if c.requires_approval)

        return ExtractionResult(
            candidates=candidates,
            auto_approved=auto_approved,
            pending_approval=pending,
            total_changes=1,
        )

    def deduplicate(
        self,
        candidates: List[CandidateFact],
        existing_facts: List[HierarchicalFact],
        similarity_threshold: float = 0.85,
    ) -> List[CandidateFact]:
        """
        Remove duplicate candidates.

        Uses simple text similarity (for now).
        TODO: Use semantic similarity when embeddings available.

        Args:
            candidates: New candidate facts
            existing_facts: Already stored facts
            similarity_threshold: Threshold for considering duplicates

        Returns:
            Deduplicated candidates
        """
        deduplicated: List[CandidateFact] = []
        existing_contents = {f.content.lower() for f in existing_facts}

        for candidate in candidates:
            content_lower = candidate.content.lower()

            # Check exact match
            if content_lower in existing_contents:
                logger.debug(f"Skipping duplicate: {candidate.content[:50]}...")
                continue

            # Check similarity with existing
            is_duplicate = False
            for existing in existing_contents:
                similarity = self._text_similarity(content_lower, existing)
                if similarity >= similarity_threshold:
                    logger.debug(f"Skipping similar fact: {candidate.content[:50]}...")
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(candidate)

        return deduplicated

    def _get_git_diff(self, staged_only: bool = False) -> str:
        """Get git diff output."""
        try:
            cmd = ["git", "diff"]
            if staged_only:
                cmd.append("--staged")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        except Exception as e:
            logger.warning(f"Failed to get git diff: {e}")
            return ""

    def _parse_diff(self, diff: str) -> Dict[str, Dict[str, Any]]:
        """Parse git diff into structured data."""
        file_changes: Dict[str, Dict[str, Any]] = {}
        current_file = None
        current_changes: Dict[str, Any] = {
            "additions": [],
            "deletions": [],
            "hunks": [],
        }

        for line in diff.splitlines():
            if line.startswith("diff --git"):
                if current_file:
                    file_changes[current_file] = current_changes
                match = re.search(r"b/(.+)$", line)
                current_file = match.group(1) if match else None
                current_changes = {"additions": [], "deletions": [], "hunks": []}
            elif line.startswith("+") and not line.startswith("+++"):
                current_changes["additions"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_changes["deletions"].append(line[1:])
            elif line.startswith("@@"):
                current_changes["hunks"].append(line)

        if current_file:
            file_changes[current_file] = current_changes

        return file_changes

    def _extract_from_file_changes(
        self,
        file_path: str,
        changes: Dict[str, Any],
    ) -> List[CandidateFact]:
        """Extract candidates from file changes."""
        candidates: List[CandidateFact] = []
        additions = "\n".join(changes.get("additions", []))
        domain = self._infer_domain(file_path)
        module = Path(file_path).stem

        # Extract new functions
        for match in self.FUNCTION_PATTERN.finditer(additions):
            func_name = match.group(2)
            if not func_name.startswith("_"):  # Skip private functions
                candidates.append(
                    CandidateFact(
                        content=f"Implemented function `{func_name}` in {module}",
                        confidence=0.85,
                        source="git_diff",
                        suggested_level=MemoryLevel.L2_MODULE,
                        suggested_domain=domain,
                        suggested_module=module,
                        file_path=file_path,
                        requires_approval=False,
                    )
                )

        # Extract new classes
        for match in self.CLASS_PATTERN.finditer(additions):
            class_name = match.group(1)
            candidates.append(
                CandidateFact(
                    content=f"Added class `{class_name}` in {module}",
                    confidence=0.9,
                    source="git_diff",
                    suggested_level=MemoryLevel.L1_DOMAIN,
                    suggested_domain=domain,
                    suggested_module=module,
                    file_path=file_path,
                    requires_approval=False,
                )
            )

        # Major file changes
        total_changes = len(changes.get("additions", [])) + len(
            changes.get("deletions", [])
        )
        if total_changes >= 50:
            candidates.append(
                CandidateFact(
                    content=f"Major refactoring of {module} ({total_changes} lines changed)",
                    confidence=0.7,
                    source="git_diff",
                    suggested_level=MemoryLevel.L1_DOMAIN,
                    suggested_domain=domain,
                    suggested_module=module,
                    file_path=file_path,
                    requires_approval=True,
                )
            )

        return candidates

    def _extract_from_new_file(
        self,
        file_path: Path,
        content: str,
    ) -> List[CandidateFact]:
        """Extract candidates from a new file's content."""
        candidates: List[CandidateFact] = []
        domain = self._infer_domain(str(file_path))
        module = file_path.stem

        # Extract classes
        for match in self.CLASS_PATTERN.finditer(content):
            class_name = match.group(1)
            candidates.append(
                CandidateFact(
                    content=f"Added class `{class_name}` in {module}",
                    confidence=0.9,
                    source="ast_analysis",
                    suggested_level=MemoryLevel.L2_MODULE,
                    suggested_domain=domain,
                    suggested_module=module,
                    file_path=str(file_path),
                    requires_approval=False,
                )
            )

        # Extract top-level functions
        for match in self.FUNCTION_PATTERN.finditer(content):
            func_name = match.group(2)
            if not func_name.startswith("_"):
                candidates.append(
                    CandidateFact(
                        content=f"Implemented function `{func_name}` in {module}",
                        confidence=0.85,
                        source="ast_analysis",
                        suggested_level=MemoryLevel.L2_MODULE,
                        suggested_domain=domain,
                        suggested_module=module,
                        file_path=str(file_path),
                        requires_approval=False,
                    )
                )

        return candidates

    def _infer_domain(self, file_path: str) -> Optional[str]:
        """Infer domain from file path."""
        path_lower = file_path.lower()

        for pattern, domain in self.DOMAIN_PATTERNS.items():
            if re.search(pattern, path_lower):
                return domain

        # Use parent directory as domain
        parts = Path(file_path).parts
        if len(parts) >= 2:
            return parts[-2]

        return None

    def _guess_file_purpose(self, file_path: Path, content: str) -> str:
        """Guess the purpose of a file from its name and content."""
        name = file_path.stem.lower()

        if "test" in name:
            return "unit testing"
        if "config" in name or "settings" in name:
            return "configuration"
        if name == "__init__":
            return "module initialization"
        if "model" in name:
            return "data modeling"
        if "api" in name or "endpoint" in name:
            return "API endpoints"
        if "util" in name or "helper" in name:
            return "utility functions"
        if "migration" in name:
            return "database migration"

        # Check content for clues
        if "class" in content[:500]:
            return "class implementation"
        if "def " in content[:500]:
            return "function definitions"

        return "functionality"

    def _text_similarity(self, a: str, b: str) -> float:
        """Simple text similarity based on word overlap."""
        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return intersection / union if union > 0 else 0.0


class ConversationExtractor:
    """
    Extract facts from agent conversation trajectories.

    Detects Significant Factual Shifts (SFS):
    - Decisions: "decided to", "chose", "will use"
    - Implementations: "implemented", "added", "created"
    - Discoveries: "found that", "discovered", "realized"
    - Fixes: "fixed", "resolved", "corrected"
    """

    # SFS detection patterns with confidence scores
    SFS_PATTERNS = {
        # Decisions (high confidence)
        r"decided to\s+(.+?)(?:\.|$)": ("decision", 0.9),
        r"chose\s+(.+?)\s+(?:over|instead|because)": ("decision", 0.85),
        r"will use\s+(.+?)\s+for": ("decision", 0.85),
        r"going with\s+(.+?)(?:\.|$)": ("decision", 0.8),
        # Implementations
        r"implemented\s+(.+?)(?:\.|$)": ("implementation", 0.9),
        r"added\s+(.+?)\s+(?:to|for|in)": ("implementation", 0.85),
        r"created\s+(.+?)(?:\.|$)": ("implementation", 0.85),
        # Discoveries
        r"found that\s+(.+?)(?:\.|$)": ("discovery", 0.8),
        r"discovered\s+(.+?)(?:\.|$)": ("discovery", 0.8),
        r"realized\s+(.+?)(?:\.|$)": ("discovery", 0.75),
        # Fixes
        r"fixed\s+(.+?)(?:\.|$)": ("fix", 0.9),
        r"resolved\s+(.+?)(?:\.|$)": ("fix", 0.9),
        r"bug\s+(?:was|in)\s+(.+?)(?:\.|$)": ("fix", 0.8),
        # Architectural
        r"architecture\s+(?:is|uses|follows)\s+(.+?)(?:\.|$)": ("architecture", 0.9),
        r"pattern\s+(?:is|we use)\s+(.+?)(?:\.|$)": ("architecture", 0.85),
    }

    # Compiled patterns
    _compiled_patterns = None

    def __init__(self, min_confidence: float = 0.7):
        self.min_confidence = min_confidence
        if ConversationExtractor._compiled_patterns is None:
            ConversationExtractor._compiled_patterns = {
                re.compile(pattern, re.IGNORECASE): meta
                for pattern, meta in self.SFS_PATTERNS.items()
            }

    def extract_from_text(self, text: str) -> ExtractionResult:
        """
        Extract facts from conversation text.

        Args:
            text: Agent response or conversation chunk

        Returns:
            ExtractionResult with candidate facts
        """
        candidates: List[CandidateFact] = []

        for pattern, (sfs_type, confidence) in self._compiled_patterns.items():
            for match in pattern.finditer(text):
                if confidence < self.min_confidence:
                    continue

                content = match.group(1).strip()
                if len(content) < 10 or len(content) > 200:
                    continue  # Skip too short or too long

                # Determine memory level based on SFS type
                level = self._sfs_type_to_level(sfs_type)

                candidates.append(
                    CandidateFact(
                        content=f"[{sfs_type.upper()}] {content}",
                        confidence=confidence,
                        source="conversation",
                        suggested_level=level,
                        requires_approval=confidence < 0.85,
                    )
                )

        # Dedupe by content similarity
        unique = self._dedupe_candidates(candidates)

        auto_approved = sum(1 for c in unique if not c.requires_approval)
        pending = sum(1 for c in unique if c.requires_approval)

        return ExtractionResult(
            candidates=unique,
            auto_approved=auto_approved,
            pending_approval=pending,
            total_changes=len(unique),
        )

    def extract_from_messages(self, messages: List[Dict[str, str]]) -> ExtractionResult:
        """
        Extract facts from a list of conversation messages.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts

        Returns:
            ExtractionResult with candidate facts
        """
        all_candidates: List[CandidateFact] = []

        for msg in messages:
            if msg.get("role") == "assistant":
                result = self.extract_from_text(msg.get("content", ""))
                all_candidates.extend(result.candidates)

        unique = self._dedupe_candidates(all_candidates)

        auto_approved = sum(1 for c in unique if not c.requires_approval)
        pending = sum(1 for c in unique if c.requires_approval)

        return ExtractionResult(
            candidates=unique,
            auto_approved=auto_approved,
            pending_approval=pending,
            total_changes=len(unique),
        )

    def _sfs_type_to_level(self, sfs_type: str) -> MemoryLevel:
        """Map SFS type to memory level."""
        mapping = {
            "decision": MemoryLevel.L1_DOMAIN,
            "architecture": MemoryLevel.L0_PROJECT,
            "implementation": MemoryLevel.L2_MODULE,
            "fix": MemoryLevel.L2_MODULE,
            "discovery": MemoryLevel.L1_DOMAIN,
        }
        return mapping.get(sfs_type, MemoryLevel.L2_MODULE)

    def _dedupe_candidates(
        self, candidates: List[CandidateFact]
    ) -> List[CandidateFact]:
        """Remove duplicate candidates by content similarity."""
        seen_contents: set = set()
        unique: List[CandidateFact] = []

        for c in candidates:
            content_key = c.content.lower()[:50]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique.append(c)

        return unique
