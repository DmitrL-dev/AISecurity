"""Discovery tools: discover_project, discover_deep, reindex."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import ToolComponents


class DiscoveryTools:
    """Project discovery and indexing tools."""

    def __init__(self, components: ToolComponents):
        self.c = components

    def register(self, server):
        c = self.c

        @server.tool(
            name="rlm_discover_project",
            description=(
                "Smart cold start discovery for new projects. "
                "Detects project type, seeds template facts, "
                "discovers domains."
            ),
        )
        async def rlm_discover_project(
            project_root: Optional[str] = None,
            task_hint: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Perform smart project discovery."""
            try:
                if project_root:
                    root = Path(project_root)
                else:
                    root = c.cold_start.project_root
                result = c.cold_start.discover_project(
                    root=root,
                    task_hint=task_hint,
                )
                c.events.notify("discover_project")
                return {
                    "status": "success",
                    "project_type": (result.project_info.project_type.value),
                    "project_name": result.project_info.name,
                    "framework": result.project_info.framework,
                    "facts_created": result.facts_created,
                    "discovery_tokens": (result.discovery_tokens),
                    "suggested_domains": (result.suggested_domains),
                    "loc_estimate": (result.project_info.loc_estimate),
                    "file_count": (result.project_info.file_count),
                    "warnings": result.warnings,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_discover_deep",
            description=(
                "Deep discovery using multiple extractors: "
                "code (README, docstrings), config "
                "(package.json, pyproject), git "
                "(conventional commits), conversation. "
                "Extracts 10x more facts than basic discover."
            ),
        )
        async def rlm_discover_deep(
            extractors_list: Optional[List[str]] = None,
            auto_approve: bool = False,
            max_facts: int = 100,
        ) -> Dict[str, Any]:
            """Deep discovery with multiple extractors."""
            try:
                extractors = extractors_list or [
                    "code",
                    "config",
                    "git",
                ]
                all_candidates = []
                auto_approved = 0
                total_extracted = 0
                extractor_results = {}

                for ext_name in extractors:
                    try:
                        candidates = _run_extractor(c, ext_name, max_facts)
                        extractor_results[ext_name] = len(candidates)
                        total_extracted += len(candidates)

                        for cand in candidates:
                            if auto_approve or (cand.get("confidence", 0) >= 0.8):
                                c.store.add_fact(
                                    content=cand["content"],
                                    level=cand.get(
                                        "level",
                                        (
                                            c.store.MemoryLevel
                                            if hasattr(
                                                c.store,
                                                "MemoryLevel",
                                            )
                                            else 1
                                        ),
                                    ),
                                    domain=cand.get("domain"),
                                    source=ext_name,
                                    confidence=cand.get("confidence", 0.7),
                                )
                                auto_approved += 1
                            else:
                                all_candidates.append(cand)
                    except Exception as ext_err:
                        extractor_results[ext_name] = f"error: {ext_err}"

                if auto_approved > 0:
                    c.events.notify("discover_deep")

                return {
                    "status": "success",
                    "total_extracted": total_extracted,
                    "auto_approved": auto_approved,
                    "pending_review": len(all_candidates),
                    "extractor_results": extractor_results,
                    "candidates": all_candidates[:20],
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_reindex",
            description=("Reindex project or specific path."),
        )
        async def rlm_reindex(
            path: Optional[str] = None,
            force: bool = False,
        ) -> Dict[str, Any]:
            """Reindex project files."""
            try:
                target = Path(path) if path else c.project_root
                if not target.exists():
                    return {
                        "status": "error",
                        "error": f"Path not found: {path}",
                    }

                indexed = 0
                errors = []
                files_found = 0

                code_exts = {
                    ".py",
                    ".js",
                    ".ts",
                    ".go",
                    ".rs",
                    ".java",
                    ".cpp",
                    ".c",
                    ".h",
                    ".rb",
                    ".php",
                    ".swift",
                    ".kt",
                    ".scala",
                    ".md",
                    ".yaml",
                    ".yml",
                    ".json",
                    ".toml",
                    ".cfg",
                    ".ini",
                }

                for f in target.rglob("*"):
                    if not f.is_file():
                        continue
                    if f.suffix not in code_exts:
                        continue
                    if any(
                        p in str(f)
                        for p in [
                            "node_modules",
                            ".git",
                            "__pycache__",
                            ".venv",
                            "venv",
                            "dist",
                            "build",
                        ]
                    ):
                        continue
                    files_found += 1

                    try:
                        content = f.read_text(
                            encoding="utf-8",
                            errors="ignore",
                        )
                        if len(content) > 100:
                            from ..v2.extractor import (
                                AutoExtractionEngine,
                            )

                            result = c.extractor.extract_from_file(
                                f, new_content=content
                            )
                            for cand in result.candidates:
                                if cand.confidence >= 0.7:
                                    c.store.add_fact(
                                        content=(cand.content),
                                        level=(cand.suggested_level),
                                        domain=(cand.suggested_domain),
                                        source="reindex",
                                        confidence=(cand.confidence),
                                    )
                                    indexed += 1
                    except Exception as fe:
                        errors.append(f"{f.name}: {fe}")

                if indexed > 0:
                    c.events.notify("reindex")

                return {
                    "status": "success",
                    "files_scanned": files_found,
                    "facts_indexed": indexed,
                    "errors": errors[:10],
                    "path": str(target),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}


def _run_extractor(c, name: str, max_facts: int):
    """Run a single extractor by name."""
    candidates = []

    if name == "code":
        for ext in [".md", ".py", ".js", ".ts"]:
            for f in c.project_root.rglob(f"*{ext}"):
                if any(
                    p in str(f)
                    for p in [
                        "node_modules",
                        ".git",
                        "__pycache__",
                    ]
                ):
                    continue
                if len(candidates) >= max_facts:
                    break
                try:
                    content = f.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    result = c.extractor.extract_from_file(f, new_content=content)
                    for cand in result.candidates:
                        candidates.append(cand.to_dict())
                except Exception:
                    pass

    elif name == "config":
        config_files = [
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
        ]
        for cf in config_files:
            fp = c.project_root / cf
            if fp.exists():
                try:
                    content = fp.read_text(encoding="utf-8")
                    result = c.extractor.extract_from_file(fp, new_content=content)
                    for cand in result.candidates:
                        candidates.append(cand.to_dict())
                except Exception:
                    pass

    elif name == "git":
        try:
            result = c.extractor.extract_from_git_diff(staged_only=False)
            for cand in result.candidates:
                candidates.append(cand.to_dict())
        except Exception:
            pass

    return candidates[:max_facts]
