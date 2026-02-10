# System tools — health, status, reindex, validate, stats
"""
Tools: health_check, check_enforcement, reindex,
       status, validate, session_stats
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ._common import ToolComponents, ServerType


def register_system_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register system/admin MCP tools."""

    store = c.store
    router = c.router
    causal_tracker = c.causal_tracker
    orchestrator = c.orchestrator
    project_root = c.project_root

    @server.tool(
        name="rlm_health_check",
        description="Health check for Memory Bridge. "
        "Returns component status, metrics, and system "
        "info.",
    )
    async def rlm_health_check() -> Dict[str, Any]:
        """Health check on all components."""
        from datetime import datetime

        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
        }

        try:
            stats = store.get_stats()
            health["components"]["store"] = {
                "status": "healthy",
                "facts_count": stats.get("total_facts", 0),
                "domains": stats.get("domains", 0),
            }
        except Exception as e:
            health["components"]["store"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        try:
            health["components"]["router"] = {
                "status": "healthy",
                "embeddings_enabled": (router.embeddings_enabled),
            }
        except Exception as e:
            health["components"]["router"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        try:
            cs = causal_tracker.get_stats()
            health["components"]["causal"] = {
                "status": "healthy",
                "decisions": cs.get("total_decisions", 0),
            }
        except Exception as e:
            health["components"]["causal"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        try:
            health["components"]["orchestrator"] = {
                "status": "healthy",
                "project_root": str(orchestrator.project_root),
            }
        except Exception as e:
            health["components"]["orchestrator"] = {
                "status": "unhealthy",
                "error": str(e),
            }

        health["l0_context"] = store.get_l0_context(max_tokens=500)
        return health

    @server.tool(
        name="rlm_check_enforcement",
        description="Check L0 enforcement rules before "
        "implementation. Returns warnings if TDD Iron "
        "Law or other L0 rules are violated. "
        "Call BEFORE writing implementation code.",
    )
    async def rlm_check_enforcement(
        task_description: str,
    ) -> Dict[str, Any]:
        """Check L0 enforcement rules."""
        try:
            w = store.check_before_implementation(task_description)
            if w:
                return {
                    "status": "blocked",
                    "warnings": w,
                    "message": "Fix issues first",
                    "action_required": True,
                }
            return {
                "status": "ok",
                "warnings": [],
                "message": "No violations. Proceed.",
                "action_required": False,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_reindex",
        description="Reindex project or specific path.",
    )
    async def rlm_reindex(
        path: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Reindex project or specific path."""
        try:
            from rlm_toolkit.indexer import AutoIndexer

            target = Path(path) if path else project_root
            indexer = AutoIndexer(target)
            r = indexer._index_full()
            return {
                "status": "success",
                "files_indexed": r.files_indexed,
                "duration": r.duration_seconds,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_status",
        description="Get RLM server status and index " "info.",
    )
    async def rlm_status() -> Dict[str, Any]:
        """Get RLM server status and index info."""
        try:
            from rlm_toolkit.storage import get_storage

            storage = get_storage(project_root)
            stats = storage.get_stats()
            return {
                "status": "success",
                "version": "3.0.0",
                "index": {
                    "crystals": stats.get("total_crystals", 0),
                    "tokens": stats.get("total_tokens", 0),
                    "db_size_mb": stats.get("db_size_mb", 0),
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_validate",
        description="Validate index freshness and " "cross-references.",
    )
    async def rlm_validate() -> Dict[str, Any]:
        """Validate index freshness."""
        try:
            from rlm_toolkit.storage import get_storage
            from rlm_toolkit.freshness import (
                CrossReferenceValidator,
            )

            storage = get_storage(project_root)
            crystals = {c["crystal"]["path"]: c["crystal"] for c in storage.load_all()}
            validator = CrossReferenceValidator(crystals)
            stats = validator.get_validation_stats()
            stale = storage.get_stale_crystals(ttl_hours=24)
            return {
                "status": "success",
                "symbols": stats,
                "stale_files": len(stale),
                "total_files": len(crystals),
                "health": ("good" if not stale else "needs_refresh"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_session_stats",
        description="Get real-time session statistics " "showing token savings.",
    )
    async def rlm_session_stats(
        reset: bool = False,
    ) -> Dict[str, Any]:
        """Get real-time session statistics."""
        try:
            import time
            from rlm_toolkit.storage import get_storage

            storage = get_storage(project_root)
            if reset:
                storage.set_metadata(
                    "session_stats",
                    {
                        "queries": 0,
                        "tokens_served": 0,
                        "tokens_saved": 0,
                        "session_start": time.time(),
                    },
                )
            stats = storage.get_metadata("session_stats") or {
                "queries": 0,
                "tokens_served": 0,
                "tokens_saved": 0,
                "session_start": time.time(),
            }
            dur = (time.time() - stats.get("session_start", time.time())) / 60
            total = stats.get("tokens_served", 0) + stats.get("tokens_saved", 0)
            pct = stats["tokens_saved"] / total * 100 if total > 0 else 0
            return {
                "status": "success",
                "session": {
                    "queries": stats.get("queries", 0),
                    "tokens_served": stats.get("tokens_served", 0),
                    "tokens_saved": stats.get("tokens_saved", 0),
                    "savings_percent": round(pct, 1),
                    "duration_minutes": round(dur, 1),
                },
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
