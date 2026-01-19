"""
Crystal Summarizer.

Creates semantic summaries of crystals to achieve higher compression ratios.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("rlm_crystal.summarizer")


@dataclass
class CrystalSummary:
    """Summarized crystal representation."""

    path: str
    name: str
    purpose: str  # One-line description
    main_classes: List[str]
    main_functions: List[str]
    dependencies: List[str]
    key_concepts: List[str]
    token_count: int

    def to_prompt(self) -> str:
        """Convert to LLM-friendly prompt format."""
        lines = [f"## {self.name}"]
        lines.append(f"Purpose: {self.purpose}")

        if self.main_classes:
            lines.append(f"Classes: {', '.join(self.main_classes[:5])}")
        if self.main_functions:
            lines.append(f"Functions: {', '.join(self.main_functions[:10])}")
        if self.dependencies:
            deps = [d for d in self.dependencies[:5] if d]
            if deps:
                lines.append(f"Depends on: {', '.join(deps)}")

        return "\n".join(lines)

    @property
    def compressed_size(self) -> int:
        """Size of compressed representation."""
        return len(self.to_prompt()) // 4  # Tokens


class CrystalSummarizer:
    """
    Create semantic summaries of crystals.

    Achieves higher compression by extracting:
    - Purpose (from docstrings)
    - Key entities (classes, main functions)
    - Dependencies
    - Key concepts

    Example:
        >>> summarizer = CrystalSummarizer()
        >>> summary = summarizer.summarize(crystal)
        >>> print(summary.to_prompt())
    """

    def summarize(self, crystal) -> CrystalSummary:
        """Create summary from crystal."""
        # Handle dict or object
        if isinstance(crystal, dict):
            path = crystal.get("path", "")
            name = crystal.get("name", "")
            primitives = crystal.get("primitives", [])
        else:
            path = crystal.path
            name = crystal.name
            primitives = crystal.primitives

        # Extract purpose from module docstring
        purpose = self._extract_purpose(primitives)

        # Extract main entities
        classes = []
        functions = []
        imports = []

        for prim in primitives:
            ptype = prim.get("ptype", "") if isinstance(prim, dict) else prim.ptype
            pname = prim.get("name", "") if isinstance(prim, dict) else prim.name

            if ptype == "CLASS":
                classes.append(pname)
            elif ptype == "FUNCTION":
                functions.append(pname)
            elif ptype == "IMPORT":
                imports.append(pname)

        # Extract key concepts from names
        concepts = self._extract_concepts(classes + functions)

        return CrystalSummary(
            path=path,
            name=name,
            purpose=purpose,
            main_classes=classes[:10],
            main_functions=functions[:20],
            dependencies=imports[:10],
            key_concepts=concepts[:10],
            token_count=sum(1 for _ in primitives) * 10,  # Rough estimate
        )

    def _extract_purpose(self, primitives: List) -> str:
        """Extract purpose from module docstring."""
        for prim in primitives:
            ptype = prim.get("ptype", "") if isinstance(prim, dict) else prim.ptype
            value = prim.get("value", "") if isinstance(prim, dict) else prim.value

            if ptype == "DOCSTRING":
                # First line of first docstring
                lines = value.split("\n")
                purpose = lines[0].strip().strip("\"'")
                if purpose and len(purpose) > 10:
                    return purpose[:200]

        return "Module with no docstring"

    def _extract_concepts(self, names: List[str]) -> List[str]:
        """Extract key concepts from names."""
        concepts = set()

        for name in names:
            # Split camelCase and snake_case
            parts = []
            current = ""
            for char in name:
                if char == "_":
                    if current:
                        parts.append(current.lower())
                    current = ""
                elif char.isupper():
                    if current:
                        parts.append(current.lower())
                    current = char
                else:
                    current += char
            if current:
                parts.append(current.lower())

            # Add meaningful parts
            for part in parts:
                if len(part) > 3 and part not in (
                    "self",
                    "init",
                    "none",
                    "true",
                    "false",
                ):
                    concepts.add(part)

        return sorted(concepts)[:20]

    def summarize_project(
        self,
        crystals: Dict[str, Any],
    ) -> Dict[str, CrystalSummary]:
        """Summarize entire project."""
        summaries = {}

        for path, crystal in crystals.items():
            summaries[path] = self.summarize(crystal)

        return summaries

    def generate_project_overview(
        self,
        summaries: Dict[str, CrystalSummary],
    ) -> str:
        """Generate project overview from summaries."""
        lines = ["# Project Overview", ""]

        # Group by directory
        by_dir: Dict[str, List[CrystalSummary]] = {}
        for path, summary in summaries.items():
            dir_name = "/".join(path.split("/")[:-1]) or "root"
            if dir_name not in by_dir:
                by_dir[dir_name] = []
            by_dir[dir_name].append(summary)

        for dir_name, dir_summaries in sorted(by_dir.items()):
            lines.append(f"## {dir_name}/")
            for s in dir_summaries[:10]:
                lines.append(f"- **{s.name}**: {s.purpose}")
            lines.append("")

        return "\n".join(lines)


def summarize_crystal(crystal) -> CrystalSummary:
    """Quick summarization."""
    return CrystalSummarizer().summarize(crystal)
