"""
Code Extractor - Extract facts from source code.

Extracts from:
- README.md, CONTRIBUTING.md
- Docstrings (Python, TypeScript)
- Comments with markers: # DECISION:, // ARCH:, # NOTE:
"""

import re
from pathlib import Path
from time import perf_counter
from typing import Optional

from .base import BaseExtractor, ExtractionResult, FactCandidate


class CodeExtractor(BaseExtractor):
    """Extract facts from source code files."""

    name = "code"

    # Files to analyze
    README_FILES = ["README.md", "README.rst", "README.txt"]
    DOC_FILES = ["CONTRIBUTING.md", "ARCHITECTURE.md", "DESIGN.md"]

    # Patterns for decision markers in code
    DECISION_PATTERNS = [
        (r"#\s*DECISION:\s*(.+)", 0.9),  # High confidence
        (r"#\s*ARCH(?:ITECTURE)?:\s*(.+)", 0.85),
        (r"#\s*NOTE:\s*(.+)", 0.7),
        (r"//\s*DECISION:\s*(.+)", 0.9),
        (r"//\s*ARCH:\s*(.+)", 0.85),
        (r"/\*\s*DECISION:\s*(.+?)\s*\*/", 0.9),
    ]

    # Patterns for README sections
    README_SECTION_PATTERNS = [
        (r"##\s*Architecture\s*\n+(.+?)(?=\n##|\Z)", "architecture", 0.85),
        (r"##\s*Design\s*\n+(.+?)(?=\n##|\Z)", "design", 0.85),
        (r"##\s*Features?\s*\n+(.+?)(?=\n##|\Z)", "features", 0.75),
        (r"##\s*Tech(?:nology)?\s*Stack\s*\n+(.+?)(?=\n##|\Z)", "tech", 0.8),
    ]

    async def extract(self) -> ExtractionResult:
        """Extract facts from code files."""
        start = perf_counter()
        result = ExtractionResult(source=self.name)

        # Extract from README files
        for readme in self.README_FILES:
            readme_path = self.project_root / readme
            if readme_path.exists():
                candidates = await self._extract_from_readme(readme_path)
                result.candidates.extend(candidates)
                break  # Only process first found

        # Extract from doc files
        for doc in self.DOC_FILES:
            doc_path = self.project_root / doc
            if doc_path.exists():
                candidates = await self._extract_from_readme(doc_path)
                result.candidates.extend(candidates)

        # Extract from Python files with decision markers
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip(py_file):
                continue
            candidates = await self._extract_from_python(py_file)
            result.candidates.extend(candidates)

        # Categorize by confidence
        for c in result.candidates:
            if c.should_auto_approve():
                result.auto_approved += 1
            elif c.should_drop():
                result.dropped += 1
            else:
                result.pending_review += 1

        result.duration_ms = (perf_counter() - start) * 1000
        return result

    def _should_skip(self, path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
        }
        return any(part in skip_dirs for part in path.parts)

    async def _extract_from_readme(self, path: Path) -> list[FactCandidate]:
        """Extract facts from README-like files."""
        candidates = []

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return candidates

        # Extract titled sections
        for pattern, domain, confidence in self.README_SECTION_PATTERNS:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                # Take first paragraph
                text = match.strip().split("\n\n")[0]
                if len(text) > 30 and len(text) < 500:
                    candidates.append(
                        self._create_candidate(
                            content=text,
                            confidence=confidence,
                            domain=domain,
                            level=0,  # L0 - Project level
                            file_path=str(path.relative_to(self.project_root)),
                        )
                    )

        return candidates

    async def _extract_from_python(self, path: Path) -> list[FactCandidate]:
        """Extract facts from Python files."""
        candidates = []

        try:
            content = path.read_text(encoding="utf-8")
            lines = content.split("\n")
        except Exception:
            return candidates

        # Look for decision markers
        for i, line in enumerate(lines):
            for pattern, confidence in self.DECISION_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    text = match.group(1).strip()
                    if len(text) > 20:
                        # Infer domain from path
                        domain = self._infer_domain(path)

                        candidates.append(
                            self._create_candidate(
                                content=text,
                                confidence=confidence,
                                domain=domain,
                                level=3,  # L3 - Code level
                                file_path=str(path.relative_to(self.project_root)),
                                line_number=i + 1,
                            )
                        )

        # Extract module docstrings (first docstring in file)
        docstring_match = re.search(r'^"""(.+?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1).strip()
            # Only first line/paragraph
            first_para = docstring.split("\n\n")[0].replace("\n", " ")
            if len(first_para) > 30 and len(first_para) < 300:
                domain = self._infer_domain(path)
                candidates.append(
                    self._create_candidate(
                        content=f"Module {path.stem}: {first_para}",
                        confidence=0.7,
                        domain=domain,
                        level=2,  # L2 - Module level
                        file_path=str(path.relative_to(self.project_root)),
                    )
                )

        return candidates

    def _infer_domain(self, path: Path) -> Optional[str]:
        """Infer domain from file path."""
        parts = path.relative_to(self.project_root).parts

        # Common patterns: src/module_name/, package/module/
        if len(parts) >= 2:
            if parts[0] in ("src", "lib", "packages"):
                return parts[1]
            return parts[0]

        return None
