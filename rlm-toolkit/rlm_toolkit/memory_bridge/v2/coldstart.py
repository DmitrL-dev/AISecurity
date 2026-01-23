"""
Cold Start Optimizer for Memory Bridge v2.0

Provides smart project discovery and template seeding
to minimize token consumption for new projects.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple
import json
import logging
import re
import subprocess

from .hierarchical import (
    HierarchicalMemoryStore,
    HierarchicalFact,
    MemoryLevel,
)

logger = logging.getLogger(__name__)


class ProjectType(Enum):
    """Supported project types for template seeding."""

    PYTHON = "python"
    NODEJS = "nodejs"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    UNKNOWN = "unknown"


@dataclass
class ProjectInfo:
    """Discovered project information."""

    project_type: ProjectType
    name: str
    root_path: Path
    framework: Optional[str] = None
    language_version: Optional[str] = None
    main_domains: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    loc_estimate: int = 0
    file_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_type": self.project_type.value,
            "name": self.name,
            "root_path": str(self.root_path),
            "framework": self.framework,
            "language_version": self.language_version,
            "main_domains": self.main_domains,
            "entry_points": self.entry_points,
            "dependencies": self.dependencies,
            "loc_estimate": self.loc_estimate,
            "file_count": self.file_count,
        }


@dataclass
class DiscoveryResult:
    """Result of project discovery."""

    project_info: ProjectInfo
    facts_created: int
    discovery_tokens: int
    suggested_domains: List[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_info": self.project_info.to_dict(),
            "facts_created": self.facts_created,
            "discovery_tokens": self.discovery_tokens,
            "suggested_domains": self.suggested_domains,
            "warnings": self.warnings,
        }


class ColdStartOptimizer:
    """
    Optimizes cold start for new projects.

    Features:
    - Project type detection
    - Template-based fact seeding
    - Progressive task-focused discovery
    - Background indexing
    """

    # Project type detection signatures
    SIGNATURES: Dict[ProjectType, List[str]] = {
        ProjectType.PYTHON: [
            "pyproject.toml",
            "setup.py",
            "requirements.txt",
            "Pipfile",
        ],
        ProjectType.NODEJS: ["package.json", "yarn.lock", "pnpm-lock.yaml"],
        ProjectType.RUST: ["Cargo.toml"],
        ProjectType.GO: ["go.mod", "go.sum"],
        ProjectType.JAVA: ["pom.xml", "build.gradle", "build.gradle.kts"],
        ProjectType.CSHARP: ["*.csproj", "*.sln"],
        ProjectType.CPP: ["CMakeLists.txt", "Makefile", "*.vcxproj"],
    }

    # Framework detection patterns
    FRAMEWORK_PATTERNS: Dict[str, Dict[str, str]] = {
        "python": {
            "fastapi": r'"fastapi"|fastapi',
            "django": r'"django"|django',
            "flask": r'"flask"|flask',
            "streamlit": r'"streamlit"|streamlit',
            "pytorch": r'"torch"|torch',
            "tensorflow": r'"tensorflow"|tensorflow',
        },
        "nodejs": {
            "react": r'"react"',
            "vue": r'"vue"',
            "next": r'"next"',
            "express": r'"express"',
            "nestjs": r'"@nestjs/core"',
            "angular": r'"@angular/core"',
        },
        "rust": {
            "actix": r"actix-web",
            "axum": r"axum",
            "rocket": r"rocket",
            "tokio": r"tokio",
        },
    }

    # Domain inference from directory names
    DOMAIN_KEYWORDS: Dict[str, str] = {
        "api": "api",
        "auth": "auth",
        "database": "database",
        "db": "database",
        "models": "models",
        "views": "frontend",
        "components": "frontend",
        "pages": "frontend",
        "services": "services",
        "utils": "utilities",
        "helpers": "utilities",
        "common": "core",
        "core": "core",
        "lib": "core",
        "tests": "testing",
        "test": "testing",
        "docs": "docs",
        "config": "config",
        "settings": "config",
    }

    def __init__(
        self,
        store: HierarchicalMemoryStore,
        project_root: Optional[Path] = None,
    ):
        self.store = store
        self.project_root = project_root or Path.cwd()

    def detect_project_type(self, root: Optional[Path] = None) -> ProjectType:
        """
        Detect project type from signatures.

        Args:
            root: Project root path (uses default if None)

        Returns:
            Detected ProjectType
        """
        root = root or self.project_root

        for project_type, signatures in self.SIGNATURES.items():
            for signature in signatures:
                if "*" in signature:
                    # Glob pattern
                    if list(root.glob(signature)):
                        return project_type
                else:
                    # Exact file
                    if (root / signature).exists():
                        return project_type

        return ProjectType.UNKNOWN

    def discover_project(
        self,
        root: Optional[Path] = None,
        task_hint: Optional[str] = None,
    ) -> DiscoveryResult:
        """
        Perform smart cold start discovery.

        Args:
            root: Project root path
            task_hint: Optional hint about first task for focused discovery

        Returns:
            DiscoveryResult with project info and created facts
        """
        root = root or self.project_root
        warnings: List[str] = []

        # Step 1: Detect project type
        project_type = self.detect_project_type(root)

        # Step 2: Gather project info
        project_info = self._gather_project_info(root, project_type)

        # Step 3: Seed template facts
        template_facts = self._get_template_facts(project_info)

        # Step 4: Discover domains
        domains = self._discover_domains(root)
        project_info.main_domains = domains

        # Step 5: Task-focused discovery if hint provided
        if task_hint:
            focused_facts = self._focused_discovery(root, task_hint, domains)
            template_facts.extend(focused_facts)

        # Step 6: Store facts
        facts_created = 0
        for fact_data in template_facts:
            try:
                self.store.add_fact(
                    content=fact_data["content"],
                    level=MemoryLevel(fact_data.get("level", 0)),
                    domain=fact_data.get("domain"),
                    source="template",
                    confidence=fact_data.get("confidence", 0.9),
                )
                facts_created += 1
            except Exception as e:
                warnings.append(f"Failed to add fact: {e}")

        # Estimate tokens used
        discovery_tokens = self._estimate_discovery_tokens(project_info, template_facts)

        return DiscoveryResult(
            project_info=project_info,
            facts_created=facts_created,
            discovery_tokens=discovery_tokens,
            suggested_domains=domains,
            warnings=warnings,
        )

    def _gather_project_info(
        self,
        root: Path,
        project_type: ProjectType,
    ) -> ProjectInfo:
        """Gather detailed project information."""
        name = root.name
        framework = None
        language_version = None
        dependencies: List[str] = []
        entry_points: List[str] = []

        # Type-specific parsing
        if project_type == ProjectType.PYTHON:
            # Parse pyproject.toml or setup.py
            pyproject = root / "pyproject.toml"
            if pyproject.exists():
                content = pyproject.read_text(encoding="utf-8", errors="ignore")

                # Extract name
                name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
                if name_match:
                    name = name_match.group(1)

                # Detect framework
                for fw_name, pattern in self.FRAMEWORK_PATTERNS.get(
                    "python", {}
                ).items():
                    if re.search(pattern, content, re.IGNORECASE):
                        framework = fw_name
                        break

                # Extract dependencies (simplified)
                deps_match = re.findall(
                    r'^\s*["\']([a-zA-Z][a-zA-Z0-9_-]+)', content, re.MULTILINE
                )
                dependencies = list(set(deps_match))[:20]

            # Find entry points
            for ep in ["main.py", "app.py", "__main__.py", "cli.py"]:
                if (root / ep).exists():
                    entry_points.append(ep)

        elif project_type == ProjectType.NODEJS:
            # Parse package.json
            package_json = root / "package.json"
            if package_json.exists():
                try:
                    data = json.loads(package_json.read_text(encoding="utf-8"))
                    name = data.get("name", name)

                    # Detect framework
                    all_deps = {
                        **data.get("dependencies", {}),
                        **data.get("devDependencies", {}),
                    }
                    for fw_name, pattern in self.FRAMEWORK_PATTERNS.get(
                        "nodejs", {}
                    ).items():
                        for dep in all_deps:
                            if re.search(pattern, dep):
                                framework = fw_name
                                break

                    dependencies = list(all_deps.keys())[:20]

                    # Entry point
                    if "main" in data:
                        entry_points.append(data["main"])
                except Exception:
                    pass

        elif project_type == ProjectType.RUST:
            # Parse Cargo.toml
            cargo_toml = root / "Cargo.toml"
            if cargo_toml.exists():
                content = cargo_toml.read_text(encoding="utf-8", errors="ignore")

                name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
                if name_match:
                    name = name_match.group(1)

                # Detect framework
                for fw_name, pattern in self.FRAMEWORK_PATTERNS.get("rust", {}).items():
                    if re.search(pattern, content, re.IGNORECASE):
                        framework = fw_name
                        break

                # Entry points
                if (root / "src" / "main.rs").exists():
                    entry_points.append("src/main.rs")
                if (root / "src" / "lib.rs").exists():
                    entry_points.append("src/lib.rs")

        # Count files and estimate LOC
        file_count, loc_estimate = self._count_files_and_loc(root, project_type)

        return ProjectInfo(
            project_type=project_type,
            name=name,
            root_path=root,
            framework=framework,
            language_version=language_version,
            entry_points=entry_points,
            dependencies=dependencies,
            loc_estimate=loc_estimate,
            file_count=file_count,
        )

    def _discover_domains(self, root: Path) -> List[str]:
        """Discover main domains/modules in the project."""
        domains: Set[str] = set()

        # Check top-level directories
        for item in root.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                name_lower = item.name.lower()

                # Map to domain if known keyword
                if name_lower in self.DOMAIN_KEYWORDS:
                    domains.add(self.DOMAIN_KEYWORDS[name_lower])
                elif name_lower not in [
                    "node_modules",
                    "__pycache__",
                    "venv",
                    ".venv",
                    "target",
                    "build",
                    "dist",
                ]:
                    # Use directory name as domain
                    domains.add(name_lower)

        return sorted(list(domains))[:10]  # Limit to 10 domains

    def _get_template_facts(self, info: ProjectInfo) -> List[Dict[str, Any]]:
        """Generate template facts based on project info."""
        facts: List[Dict[str, Any]] = []

        # L0: Project overview
        type_name = info.project_type.value.title()
        overview = f"{info.name} is a {type_name} project"
        if info.framework:
            overview += f" using {info.framework}"
        if info.loc_estimate > 0:
            overview += f" (~{info.loc_estimate:,} LOC, {info.file_count} files)"

        facts.append(
            {
                "content": overview,
                "level": 0,  # L0_PROJECT
                "confidence": 0.95,
            }
        )

        # Entry points
        if info.entry_points:
            facts.append(
                {
                    "content": f"Main entry points: {', '.join(info.entry_points)}",
                    "level": 0,
                    "confidence": 0.9,
                }
            )

        # Key dependencies
        if info.dependencies:
            top_deps = info.dependencies[:5]
            facts.append(
                {
                    "content": f"Key dependencies: {', '.join(top_deps)}",
                    "level": 1,  # L1_DOMAIN
                    "domain": "dependencies",
                    "confidence": 0.85,
                }
            )

        # Domains
        if info.main_domains:
            facts.append(
                {
                    "content": f"Main domains/modules: {', '.join(info.main_domains)}",
                    "level": 0,
                    "confidence": 0.85,
                }
            )

        # Type-specific facts
        if info.project_type == ProjectType.PYTHON:
            facts.extend(self._python_template_facts(info))
        elif info.project_type == ProjectType.NODEJS:
            facts.extend(self._nodejs_template_facts(info))
        elif info.project_type == ProjectType.RUST:
            facts.extend(self._rust_template_facts(info))

        return facts

    def _python_template_facts(self, info: ProjectInfo) -> List[Dict[str, Any]]:
        """Python-specific template facts."""
        facts = []

        # Check for common patterns
        root = info.root_path

        if (root / "tests").exists() or (root / "test").exists():
            facts.append(
                {
                    "content": "Has test suite in tests/ directory",
                    "level": 1,
                    "domain": "testing",
                    "confidence": 0.9,
                }
            )

        if (root / "docs").exists():
            facts.append(
                {
                    "content": "Has documentation in docs/ directory",
                    "level": 1,
                    "domain": "docs",
                    "confidence": 0.9,
                }
            )

        if (root / ".github" / "workflows").exists():
            facts.append(
                {
                    "content": "Uses GitHub Actions for CI/CD",
                    "level": 1,
                    "domain": "devops",
                    "confidence": 0.9,
                }
            )

        return facts

    def _nodejs_template_facts(self, info: ProjectInfo) -> List[Dict[str, Any]]:
        """Node.js-specific template facts."""
        facts = []
        root = info.root_path

        if (root / "src").exists():
            facts.append(
                {
                    "content": "Source code in src/ directory",
                    "level": 1,
                    "domain": "core",
                    "confidence": 0.9,
                }
            )

        if (root / "pages").exists():
            facts.append(
                {
                    "content": "Uses pages-based routing (likely Next.js)",
                    "level": 1,
                    "domain": "frontend",
                    "confidence": 0.85,
                }
            )

        return facts

    def _rust_template_facts(self, info: ProjectInfo) -> List[Dict[str, Any]]:
        """Rust-specific template facts."""
        facts = []
        root = info.root_path

        if (root / "src" / "lib.rs").exists():
            facts.append(
                {
                    "content": "Library crate with src/lib.rs",
                    "level": 1,
                    "domain": "core",
                    "confidence": 0.9,
                }
            )

        if (root / "benches").exists():
            facts.append(
                {
                    "content": "Has benchmarks in benches/ directory",
                    "level": 1,
                    "domain": "testing",
                    "confidence": 0.9,
                }
            )

        return facts

    def _focused_discovery(
        self,
        root: Path,
        task_hint: str,
        domains: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Perform task-focused discovery.

        Only discovers files/facts relevant to the given task.
        """
        facts: List[Dict[str, Any]] = []
        task_lower = task_hint.lower()

        # Extract keywords from task
        keywords = set(re.findall(r"\b\w+\b", task_lower))

        # Find relevant domains
        relevant_domains = []
        for domain in domains:
            if domain in keywords or any(kw in domain for kw in keywords):
                relevant_domains.append(domain)

        if relevant_domains:
            facts.append(
                {
                    "content": f"Task '{task_hint[:50]}' likely involves: {', '.join(relevant_domains)}",
                    "level": 1,
                    "confidence": 0.7,
                }
            )

        return facts

    def _count_files_and_loc(
        self,
        root: Path,
        project_type: ProjectType,
    ) -> Tuple[int, int]:
        """
        Count files and estimate lines of code.

        Uses efficient traversal that skips excluded dirs early.
        """
        extensions = {
            ProjectType.PYTHON: {".py"},
            ProjectType.NODEJS: {".js", ".ts", ".jsx", ".tsx", ".vue"},
            ProjectType.RUST: {".rs"},
            ProjectType.GO: {".go"},
            ProjectType.JAVA: {".java"},
            ProjectType.CSHARP: {".cs"},
            ProjectType.CPP: {".cpp", ".hpp", ".c", ".h"},
            ProjectType.UNKNOWN: set(),
        }

        exts = extensions.get(project_type, set())
        if not exts:
            return 0, 0

        # Directories to skip (case-insensitive on Windows)
        SKIP_DIRS = {
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            ".hg",
            ".svn",
            "target",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".tox",
            "htmlcov",
            ".next",
            ".nuxt",
            "vendor",
            "bower_components",
        }

        file_count = 0
        max_files = 10000  # Safety limit

        # Try git ls-files first (fastest)
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                files = result.stdout.strip().split("\n")
                file_count = sum(
                    1 for f in files if f and any(f.endswith(ext) for ext in exts)
                )
                loc_estimate = file_count * 50
                logger.info(f"Fast count via git: {file_count} files")
                return file_count, loc_estimate
        except Exception as e:
            logger.debug(f"git ls-files failed: {e}")

        # Fallback: efficient iterdir traversal
        def count_in_dir(path: Path, depth: int = 0) -> int:
            nonlocal file_count
            if depth > 15 or file_count >= max_files:
                return 0

            count = 0
            try:
                for item in path.iterdir():
                    if file_count >= max_files:
                        break

                    if item.is_dir():
                        # Skip excluded directories EARLY
                        if item.name.lower() in SKIP_DIRS:
                            continue
                        count += count_in_dir(item, depth + 1)
                    elif item.is_file():
                        if item.suffix.lower() in exts:
                            count += 1
                            file_count += 1
            except PermissionError:
                pass
            except OSError:
                pass

            return count

        count_in_dir(root)
        loc_estimate = file_count * 50

        logger.info(f"Counted {file_count} files via iterdir")
        return file_count, loc_estimate

    def _estimate_discovery_tokens(
        self,
        info: ProjectInfo,
        facts: List[Dict[str, Any]],
    ) -> int:
        """Estimate tokens used in discovery."""
        # Base overhead
        tokens = 500

        # Reading config files
        if info.project_type == ProjectType.PYTHON:
            tokens += 300  # pyproject.toml
        elif info.project_type == ProjectType.NODEJS:
            tokens += 500  # package.json can be large
        elif info.project_type == ProjectType.RUST:
            tokens += 200  # Cargo.toml

        # Facts created
        for fact in facts:
            tokens += len(fact.get("content", "")) // 4 + 10

        return tokens

    async def background_index(
        self,
        root: Optional[Path] = None,
        priority_paths: Optional[List[str]] = None,
    ) -> AsyncGenerator[HierarchicalFact, None]:
        """
        Perform background indexing of the project.

        Yields facts as they are discovered.

        Args:
            root: Project root path
            priority_paths: Paths to index first

        Yields:
            HierarchicalFact objects as discovered
        """
        root = root or self.project_root
        priority_paths = priority_paths or []

        # This is a placeholder for async background indexing
        # In a real implementation, this would:
        # 1. Walk the file tree
        # 2. Parse each file with AST
        # 3. Extract facts and yield them
        # 4. Support cancellation

        logger.info(f"Background indexing started for {root}")

        # For now, yield nothing (actual implementation would be async file walking)
        return
        yield  # Makes this a generator
