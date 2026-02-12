# Discovery tools — project discovery, deep discover, extractors
"""
Tools: discover_project, discover_deep, extract_facts,
       extract_from_conversation, install_git_hooks
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ._common import ToolComponents, ServerType
from ..v2.hierarchical import MemoryLevel


def register_discovery_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register all discovery-related MCP tools."""

    store = c.store
    extractor = c.extractor
    cold_start = c.cold_start
    project_root = c.project_root

    @server.tool(
        name="rlm_discover_project",
        description="Smart cold start discovery for new projects. "
        "Detects project type, seeds template facts, discovers domains.",
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
                root = cold_start.project_root
            result = cold_start.discover_project(
                root=root,
                task_hint=task_hint,
            )
            return {
                "status": "success",
                "project_type": result.project_info.project_type.value,
                "project_name": result.project_info.name,
                "framework": result.project_info.framework,
                "facts_created": result.facts_created,
                "discovery_tokens": result.discovery_tokens,
                "suggested_domains": result.suggested_domains,
                "loc_estimate": result.project_info.loc_estimate,
                "file_count": result.project_info.file_count,
                "warnings": result.warnings,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_extract_facts",
        description="Auto-extract facts from git diff or file changes. "
        "Returns candidates for approval.",
    )
    async def rlm_extract_facts(
        source: str = "git_diff",
        file_path: Optional[str] = None,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """Extract facts from code changes."""
        try:
            if source == "file" and file_path:
                path = Path(file_path)
                if path.exists():
                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    result = extractor.extract_from_file(
                        path,
                        new_content=content,
                    )
                else:
                    return {
                        "status": "error",
                        "message": f"File not found: {file_path}",
                    }
            else:
                staged_only = source == "staged"
                result = extractor.extract_from_git_diff(
                    staged_only=staged_only,
                )

            if auto_approve:
                for candidate in result.candidates:
                    if candidate.confidence >= 0.8:
                        candidate.approved = True
                        candidate.requires_approval = False
                        store.add_fact(
                            content=candidate.content,
                            level=candidate.suggested_level,
                            domain=candidate.suggested_domain,
                            source=candidate.source,
                            confidence=candidate.confidence,
                        )

            return {
                "status": "success",
                "candidates": [c.to_dict() for c in result.candidates],
                "auto_approved": result.auto_approved,
                "pending_approval": result.pending_approval,
                "total_changes": result.total_changes,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_discover_deep",
        description="Deep discovery using multiple extractors: "
        "code (README, docstrings), config (package.json, pyproject), "
        "git (conventional commits), conversation. "
        "Extracts 10x more facts than basic discover.",
    )
    async def rlm_discover_deep(
        extractors_list: Optional[List[str]] = None,
        auto_approve: bool = False,
        max_facts: int = 100,
    ) -> Dict[str, Any]:
        """Deep discovery with multiple extractors."""
        try:
            import sys
            from pathlib import Path as PathLib

            rlm_toolkit_root = PathLib(__file__).parent.parent.parent
            extractors_src = rlm_toolkit_root / "src"
            if extractors_src.exists():
                if str(extractors_src) not in sys.path:
                    sys.path.insert(0, str(extractors_src))

            try:
                from rlm_mcp_server.extractors import (
                    ExtractionOrchestrator,
                )
            except ImportError as import_err:
                return {
                    "status": "error",
                    "message": (
                        f"Extractors import failed: {import_err}. "
                        f"Path checked: {extractors_src}"
                    ),
                }

            orchestrator_ext = ExtractionOrchestrator(project_root)
            result = await orchestrator_ext.discover_deep(
                extractors=extractors_list,
                auto_approve=auto_approve,
                max_facts=max_facts,
            )

            pending_db = Path(project_root) / ".rlm" / "pending_candidates.db"
            pending_db.parent.mkdir(parents=True, exist_ok=True)

            pending_store = None
            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                    PendingCandidate,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                pass

            auto_approved_count = 0
            pending_count = 0

            for candidate in result.get("candidates", []):
                confidence = candidate.get("confidence", 0)
                if confidence > 0.9 or auto_approve:
                    store.add_fact(
                        content=candidate["content"],
                        level=MemoryLevel(candidate.get("level", 1)),
                        domain=candidate.get("domain"),
                        source=(f"discover_deep:" f"{candidate.get('source')}"),
                        confidence=confidence,
                    )
                    auto_approved_count += 1
                elif confidence >= 0.5 and pending_store:
                    import uuid

                    pending_store.add(
                        PendingCandidate(
                            id=str(uuid.uuid4()),
                            content=candidate["content"],
                            source=candidate.get("source", "unknown"),
                            confidence=confidence,
                            domain=candidate.get("domain"),
                            level=candidate.get("level", 1),
                            file_path=candidate.get("file_path"),
                            line_number=candidate.get("line_number"),
                        )
                    )
                    pending_count += 1

            result["auto_approved"] = auto_approved_count
            result["pending_review"] = pending_count
            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_extract_from_conversation",
        description="Extract facts from conversation text using SFS "
        "(Significant Factual Shifts) detection. "
        "Identifies decisions, implementations, fixes, discoveries.",
    )
    async def rlm_extract_from_conversation(
        text: str,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """Extract facts from conversation text."""
        try:
            from ..v2.extractor import ConversationExtractor

            conv_extractor = ConversationExtractor()
            result = conv_extractor.extract_from_text(text)

            if auto_approve:
                for candidate in result.candidates:
                    if not candidate.requires_approval:
                        store.add_fact(
                            content=candidate.content,
                            level=candidate.suggested_level,
                            domain=candidate.suggested_domain,
                            source="conversation_sfs",
                            confidence=candidate.confidence,
                        )

            return {
                "status": "success",
                "candidates": [c.to_dict() for c in result.candidates],
                "auto_approved": result.auto_approved,
                "pending_approval": result.pending_approval,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_install_git_hooks",
        description="Install git hooks for automatic fact extraction. "
        "Extracts facts from commits automatically.",
    )
    async def rlm_install_git_hooks(
        hook_type: str = "post-commit",
    ) -> Dict[str, Any]:
        """Install git hooks for auto-extraction."""
        try:
            git_dir = project_root / ".git"
            if not git_dir.exists():
                return {
                    "status": "error",
                    "message": "Not a git repository",
                }

            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(exist_ok=True)
            hook_path = hooks_dir / hook_type

            if hook_path.exists():
                content = hook_path.read_text()
                if "rlm_toolkit" in content:
                    return {
                        "status": "success",
                        "message": "Hook already installed",
                        "hook_path": str(hook_path),
                    }
                hook_script = "\n# Memory Bridge Auto-Extract\n"
            else:
                hook_script = "#!/bin/sh\n# Memory Bridge Auto-Extract\n"

            hook_script += (
                'python -c "'
                "from rlm_toolkit.memory_bridge.v2.extractor "
                "import AutoExtractionEngine; "
                "e = AutoExtractionEngine(); "
                "r = e.extract_from_git_diff(); "
                f"print(f'Extracted {{len(r.candidates)}} facts')"
                '" 2>/dev/null || true\n'
            )

            if hook_path.exists():
                with open(hook_path, "a") as f:
                    f.write(hook_script)
            else:
                hook_path.write_text(hook_script)

            try:
                import stat

                mode = hook_path.stat().st_mode
                hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP)
            except Exception:
                pass

            return {
                "status": "success",
                "message": f"Installed {hook_type} hook",
                "hook_path": str(hook_path),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
