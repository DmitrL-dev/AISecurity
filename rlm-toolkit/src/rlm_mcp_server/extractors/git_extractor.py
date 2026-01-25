"""
Git Extractor - Extract facts from Git history.

Extracts from:
- Conventional commits (feat, fix, refactor, etc.)
- Commit messages with decision context
- Branch names
"""

import re
import subprocess
from pathlib import Path
from time import perf_counter
from typing import Optional

from .base import BaseExtractor, ExtractionResult, FactCandidate


class GitExtractor(BaseExtractor):
    """Extract facts from Git history."""

    name = "git"

    # Conventional commit patterns
    COMMIT_PATTERNS = [
        (r"^feat\((\w+)\):\s*(.+)", "feature", 0.85),
        (r"^fix\((\w+)\):\s*(.+)", "fix", 0.8),
        (r"^refactor\((\w+)\):\s*(.+)", "refactor", 0.75),
        (r"^perf\((\w+)\):\s*(.+)", "performance", 0.8),
        (r"^docs\((\w+)\):\s*(.+)", "documentation", 0.7),
        (r"^chore\((\w+)\):\s*(.+)", "chore", 0.6),
        (r"^test\((\w+)\):\s*(.+)", "testing", 0.7),
        (r"^style\((\w+)\):\s*(.+)", "style", 0.5),
        (r"^ci\((\w+)\):\s*(.+)", "ci", 0.7),
        # Without scope
        (r"^feat:\s*(.+)", "feature", 0.75),
        (r"^fix:\s*(.+)", "fix", 0.7),
    ]

    def __init__(self, project_root: Path, max_commits: int = 50):
        super().__init__(project_root)
        self.max_commits = max_commits

    async def extract(self) -> ExtractionResult:
        """Extract facts from Git history."""
        start = perf_counter()
        result = ExtractionResult(source=self.name)

        # Check if git repo
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            result.errors.append("Not a git repository")
            return result

        # Get recent commits
        commits = self._get_commits()

        for commit_msg, sha in commits:
            candidates = self._extract_from_commit(commit_msg, sha)
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

    def _get_commits(self) -> list[tuple[str, str]]:
        """Get recent commit messages."""
        commits = []

        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    f"-n{self.max_commits}",
                    "--pretty=format:%s|||%H",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if "|||" in line:
                        msg, sha = line.split("|||", 1)
                        commits.append((msg.strip(), sha.strip()))
        except Exception:
            pass

        return commits

    def _extract_from_commit(self, commit_msg: str, sha: str) -> list[FactCandidate]:
        """Extract facts from a commit message."""
        candidates = []

        for pattern, fact_type, confidence in self.COMMIT_PATTERNS:
            match = re.match(pattern, commit_msg, re.IGNORECASE)
            if match:
                groups = match.groups()

                if len(groups) == 2:
                    domain, description = groups
                else:
                    domain = None
                    description = groups[0]

                candidates.append(
                    self._create_candidate(
                        content=f"[{fact_type}] {description}",
                        confidence=confidence,
                        domain=domain,
                        level=2,  # Module level
                        commit_sha=sha[:8],
                    )
                )
                break

        return candidates

    async def get_domains_from_history(self) -> set[str]:
        """Extract domain names from commit scopes."""
        domains = set()

        commits = self._get_commits()
        for msg, _ in commits:
            # Extract scope from conventional commits
            match = re.match(r"^\w+\((\w+)\):", msg)
            if match:
                domains.add(match.group(1))

        return domains
