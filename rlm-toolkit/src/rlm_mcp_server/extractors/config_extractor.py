"""
Config Extractor - Extract facts from configuration files.

Extracts from:
- package.json (dependencies, scripts)
- pyproject.toml (dependencies, metadata)
- Dockerfile (base image, tech stack)
- .env.example (environment variables)
"""

import json
import re
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

from .base import BaseExtractor, ExtractionResult, FactCandidate


class ConfigExtractor(BaseExtractor):
    """Extract facts from configuration files."""

    name = "config"

    async def extract(self) -> ExtractionResult:
        """Extract facts from config files."""
        start = perf_counter()
        result = ExtractionResult(source=self.name)

        # package.json
        pkg_json = self.project_root / "package.json"
        if pkg_json.exists():
            candidates = await self._extract_from_package_json(pkg_json)
            result.candidates.extend(candidates)

        # pyproject.toml
        pyproject = self.project_root / "pyproject.toml"
        if pyproject.exists():
            candidates = await self._extract_from_pyproject(pyproject)
            result.candidates.extend(candidates)

        # Dockerfile
        dockerfile = self.project_root / "Dockerfile"
        if dockerfile.exists():
            candidates = await self._extract_from_dockerfile(dockerfile)
            result.candidates.extend(candidates)

        # .env.example
        env_example = self.project_root / ".env.example"
        if env_example.exists():
            candidates = await self._extract_from_env(env_example)
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

    async def _extract_from_package_json(self, path: Path) -> list[FactCandidate]:
        """Extract from package.json."""
        candidates = []

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return candidates

        # Project description
        if desc := data.get("description"):
            candidates.append(
                self._create_candidate(
                    content=f"Project: {desc}",
                    confidence=0.9,
                    level=0,
                    file_path="package.json",
                )
            )

        # Key dependencies
        deps = data.get("dependencies", {})
        dev_deps = data.get("devDependencies", {})

        key_deps = []
        for dep in list(deps.keys())[:10]:  # Top 10
            key_deps.append(dep)

        if key_deps:
            candidates.append(
                self._create_candidate(
                    content=f"Key dependencies: {', '.join(key_deps)}",
                    confidence=0.85,
                    domain="tech",
                    level=0,
                    file_path="package.json",
                )
            )

        # Scripts as capabilities
        scripts = data.get("scripts", {})
        script_names = list(scripts.keys())
        if script_names:
            candidates.append(
                self._create_candidate(
                    content=f"NPM scripts: {', '.join(script_names[:8])}",
                    confidence=0.75,
                    domain="tech",
                    level=1,
                    file_path="package.json",
                )
            )

        return candidates

    async def _extract_from_pyproject(self, path: Path) -> list[FactCandidate]:
        """Extract from pyproject.toml."""
        candidates = []

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return candidates

        # Try to parse key fields with regex (avoid tomli dependency)

        # Project name
        name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
        if name_match:
            name = name_match.group(1)
            candidates.append(
                self._create_candidate(
                    content=f"Python package: {name}",
                    confidence=0.9,
                    level=0,
                    file_path="pyproject.toml",
                )
            )

        # Description
        desc_match = re.search(r'description\s*=\s*"([^"]+)"', content)
        if desc_match:
            candidates.append(
                self._create_candidate(
                    content=f"Description: {desc_match.group(1)}",
                    confidence=0.85,
                    level=0,
                    file_path="pyproject.toml",
                )
            )

        # Python version
        python_match = re.search(r'python\s*=\s*"([^"]+)"', content)
        if python_match:
            candidates.append(
                self._create_candidate(
                    content=f"Python version: {python_match.group(1)}",
                    confidence=0.8,
                    domain="tech",
                    level=0,
                    file_path="pyproject.toml",
                )
            )

        # Key dependencies
        deps_section = re.search(
            r"\[tool\.poetry\.dependencies\](.*?)(?=\[|$)", content, re.DOTALL
        )
        if deps_section:
            deps = re.findall(r"^(\w+)\s*=", deps_section.group(1), re.MULTILINE)
            deps = [d for d in deps if d != "python"][:10]
            if deps:
                candidates.append(
                    self._create_candidate(
                        content=f"Key dependencies: {', '.join(deps)}",
                        confidence=0.8,
                        domain="tech",
                        level=0,
                        file_path="pyproject.toml",
                    )
                )

        return candidates

    async def _extract_from_dockerfile(self, path: Path) -> list[FactCandidate]:
        """Extract from Dockerfile."""
        candidates = []

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return candidates

        # Base image
        from_match = re.search(r"^FROM\s+(\S+)", content, re.MULTILINE)
        if from_match:
            candidates.append(
                self._create_candidate(
                    content=f"Docker base image: {from_match.group(1)}",
                    confidence=0.85,
                    domain="infra",
                    level=1,
                    file_path="Dockerfile",
                )
            )

        # Exposed ports
        ports = re.findall(r"^EXPOSE\s+(\d+)", content, re.MULTILINE)
        if ports:
            candidates.append(
                self._create_candidate(
                    content=f"Exposed ports: {', '.join(ports)}",
                    confidence=0.8,
                    domain="infra",
                    level=1,
                    file_path="Dockerfile",
                )
            )

        return candidates

    async def _extract_from_env(self, path: Path) -> list[FactCandidate]:
        """Extract from .env.example."""
        candidates = []

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return candidates

        # Extract env var names (not values for security)
        env_vars = re.findall(r"^([A-Z][A-Z0-9_]+)=", content, re.MULTILINE)

        if env_vars:
            # Group by prefix
            grouped = {}
            for var in env_vars:
                prefix = var.split("_")[0]
                if prefix not in grouped:
                    grouped[prefix] = []
                grouped[prefix].append(var)

            for prefix, vars in grouped.items():
                if len(vars) >= 2:
                    candidates.append(
                        self._create_candidate(
                            content=f"Config group {prefix}: {', '.join(vars[:5])}",
                            confidence=0.7,
                            domain="config",
                            level=1,
                            file_path=".env.example",
                        )
                    )

        return candidates
