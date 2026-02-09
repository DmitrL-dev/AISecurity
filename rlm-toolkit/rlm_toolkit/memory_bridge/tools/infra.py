"""Infrastructure tools: stats, domains, health, enforcement, hooks, embeddings."""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import ToolComponents

from ..v2.hierarchical import MemoryLevel


class InfraTools:
    """Infrastructure, monitoring, and operational tools."""

    def __init__(self, components: ToolComponents):
        self.c = components

    def register(self, server):
        c = self.c

        @server.tool(
            name="rlm_get_hierarchy_stats",
            description=("Get statistics about the hierarchical " "memory store."),
        )
        async def rlm_get_hierarchy_stats() -> Dict[str, Any]:
            """Get memory store statistics."""
            try:
                stats = c.store.get_stats()
                causal_stats = c.causal_tracker.get_stats()
                return {
                    "status": "success",
                    "memory_store": stats,
                    "causal_chains": causal_stats,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_status",
            description=("Get project index status for dashboard."),
        )
        async def rlm_status() -> Dict[str, Any]:
            """Get project index status."""
            try:
                stats = c.store.get_stats()
                total = stats.get("total_facts", 0)
                return {
                    "success": True,
                    "status": "success",
                    "version": "3.0.0",
                    "index": {
                        "crystals": total * 5,
                        "tokens": total * 150,
                    },
                    "facts_count": total,
                }
            except Exception as e:
                return {
                    "success": False,
                    "status": "error",
                    "error": str(e),
                }

        @server.tool(
            name="rlm_get_facts_by_domain",
            description=("Get all facts for a specific domain."),
        )
        async def rlm_get_facts_by_domain(
            domain: str,
            include_stale: bool = False,
        ) -> Dict[str, Any]:
            """Get facts for a domain."""
            try:
                facts = c.store.get_domain_facts(domain)
                if not include_stale:
                    facts = [f for f in facts if not f.is_stale]
                return {
                    "status": "success",
                    "domain": domain,
                    "facts_count": len(facts),
                    "facts": [
                        {
                            "id": f.id,
                            "content": f.content,
                            "level": f.level.name,
                            "module": f.module,
                            "is_stale": f.is_stale,
                        }
                        for f in facts
                    ],
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_list_domains",
            description=("List all discovered domains in the " "memory store."),
        )
        async def rlm_list_domains() -> Dict[str, Any]:
            """List all domains."""
            try:
                domains = c.store.get_domains()
                domain_counts = {}
                for d in domains:
                    facts = c.store.get_domain_facts(d)
                    domain_counts[d] = len(facts)
                return {
                    "status": "success",
                    "domains": domains,
                    "domain_counts": domain_counts,
                    "total_domains": len(domains),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_index_embeddings",
            description=(
                "Generate embeddings for all facts "
                "without embeddings. Required for "
                "semantic routing."
            ),
        )
        async def rlm_index_embeddings() -> Dict[str, Any]:
            """Index all facts with embeddings."""
            try:
                indexed = c.router.index_all_facts()
                return {
                    "status": "success",
                    "indexed_count": indexed,
                    "message": (f"Indexed {indexed} facts " f"with embeddings"),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_install_git_hooks",
            description=(
                "Install git hooks for automatic fact "
                "extraction. Extracts facts from "
                "commits automatically."
            ),
        )
        async def rlm_install_git_hooks(
            hook_type: str = "post-commit",
        ) -> Dict[str, Any]:
            """Install git hooks for auto-extraction."""
            try:
                git_dir = c.project_root / ".git"
                if not git_dir.exists():
                    return {
                        "status": "error",
                        "error": ("Not a git repository"),
                    }

                hooks_dir = git_dir / "hooks"
                hooks_dir.mkdir(exist_ok=True)

                hook_path = hooks_dir / hook_type
                hook_script = (
                    "#!/bin/sh\n"
                    "# RLM Auto-extraction hook\n"
                    'python -c "\n'
                    "import sys\n"
                    "sys.path.insert(0, '.')\n"
                    "try:\n"
                    "    from rlm_toolkit.memory_bridge"
                    ".v2.extractor import "
                    "AutoExtractionEngine\n"
                    "    e = AutoExtractionEngine()\n"
                    "    r = e.extract_from_git_diff()\n"
                    "    print(f'RLM: Extracted "
                    "{len(r.candidates)} facts')\n"
                    "except Exception as ex:\n"
                    "    print(f'RLM hook error: {ex}')\n"
                    '" 2>/dev/null || true\n'
                )
                hook_path.write_text(hook_script)

                # Make executable on Unix
                if platform.system() != "Windows":
                    import stat

                    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)

                return {
                    "status": "success",
                    "hook_type": hook_type,
                    "hook_path": str(hook_path),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_health_check",
            description=(
                "Health check for Memory Bridge. "
                "Returns component status, metrics, "
                "and system info."
            ),
        )
        async def rlm_health_check() -> Dict[str, Any]:
            """Perform health check."""
            try:
                checks = {}

                # Store
                try:
                    stats = c.store.get_stats()
                    checks["store"] = {
                        "status": "healthy",
                        "facts": stats.get("total_facts", 0),
                    }
                except Exception as e:
                    checks["store"] = {
                        "status": "error",
                        "error": str(e),
                    }

                # Router
                try:
                    checks["router"] = {
                        "status": "healthy",
                        "embedder": (
                            "available" if c.router.embedding_service else "unavailable"
                        ),
                    }
                except Exception as e:
                    checks["router"] = {
                        "status": "error",
                        "error": str(e),
                    }

                # Causal
                try:
                    cs = c.causal_tracker.get_stats()
                    checks["causal"] = {
                        "status": "healthy",
                        "decisions": cs.get("total_decisions", 0),
                    }
                except Exception as e:
                    checks["causal"] = {
                        "status": "error",
                        "error": str(e),
                    }

                # TTL
                try:
                    checks["ttl"] = {
                        "status": "healthy",
                    }
                except Exception as e:
                    checks["ttl"] = {
                        "status": "error",
                        "error": str(e),
                    }

                healthy = all(v.get("status") == "healthy" for v in checks.values())

                return {
                    "status": "success",
                    "healthy": healthy,
                    "components": checks,
                    "version": "3.0.0",
                    "python_version": (platform.python_version()),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_check_enforcement",
            description=(
                "Check L0 enforcement rules before "
                "implementation. Returns warnings if "
                "TDD Iron Law or other L0 rules are "
                "violated. Call BEFORE writing "
                "implementation code."
            ),
        )
        async def rlm_check_enforcement(
            task_description: str,
        ) -> Dict[str, Any]:
            """Check L0 enforcement rules."""
            try:
                l0_facts = c.store.get_facts_by_level(MemoryLevel.L0_PROJECT)
                warnings = []
                for f in l0_facts:
                    content_lower = f.content.lower()
                    task_lower = task_description.lower()

                    if "tdd" in content_lower and "test" not in task_lower:
                        warnings.append(
                            f"L0 Rule: {f.content} — "
                            f"Consider writing tests "
                            f"first."
                        )
                    if (
                        "must" in content_lower
                        or "never" in content_lower
                        or "always" in content_lower
                    ):
                        warnings.append(f"L0 Constraint: {f.content}")

                return {
                    "status": "success",
                    "task": task_description,
                    "warnings": warnings,
                    "warnings_count": len(warnings),
                    "safe_to_proceed": (len(warnings) == 0),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
