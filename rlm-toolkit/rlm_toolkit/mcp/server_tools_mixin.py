"""Server tool handlers for RLMServer.

Infrastructure tools: status, session_stats, reindex,
validate, settings.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..memory.hierarchical import HierarchicalMemory

logger = logging.getLogger("rlm_mcp")


class ServerToolsMixin:
    """Server infrastructure tools for RLMServer."""

    if TYPE_CHECKING:
        mcp: FastMCP[Any]
        memory: HierarchicalMemory
        session_stats: Dict[str, Any]
        memory_bridge_v2_store: Any
        _last_reindex_time: float
        _reindex_rate_limit_seconds: int

    def _register_server_tools(self) -> None:
        """Register server infrastructure MCP tools."""

        @self.mcp.tool("rlm_status")  # type: ignore[misc]
        async def status() -> Dict[str, Any]:
            """
            Get RLM server status and index info.

            Returns:
                Server status, index stats, memory stats
            """
            try:
                from ..storage import get_storage
                from ..freshness import (
                    CrossReferenceValidator,
                )

                project_root = os.getenv(
                    "RLM_PROJECT_ROOT",
                    os.getcwd(),
                )
                storage = get_storage(Path(project_root))
                stats = storage.get_stats()

                memory_stats = {}
                if hasattr(self.memory, "get_stats"):
                    memory_stats = self.memory.get_stats()

                from ..memory.secure import (
                    SecureHierarchicalMemory,
                )

                return {
                    "success": True,
                    "server": "rlm-toolkit",
                    "version": "1.2.0",
                    "project_root": project_root,
                    "index": {
                        "crystals": stats.get(
                            "total_crystals",
                            0,
                        ),
                        "tokens": stats.get(
                            "total_tokens",
                            0,
                        ),
                        "db_size_mb": stats.get(
                            "db_size_mb",
                            0,
                        ),
                    },
                    "memory": memory_stats,
                    "secure_mode": isinstance(
                        self.memory,
                        SecureHierarchicalMemory,
                    ),
                    "l0_context": (
                        self.memory_bridge_v2_store.get_l0_context(max_tokens=500)
                    ),
                }
            except Exception as e:
                logger.error(
                    f"Status check failed: {e}",
                )
                return {
                    "success": False,
                    "error": str(e),
                }

        @self.mcp.tool("rlm_session_stats")  # type: ignore[misc]
        async def session_stats(
            reset: bool = False,
        ) -> Dict[str, Any]:
            """
            Get real-time session statistics
            showing token savings.

            Args:
                reset: Reset session stats to zero

            Returns:
                Session statistics including queries,
                tokens, and savings
            """
            import time

            if reset:
                self.session_stats = {
                    "queries": 0,
                    "tokens_served": 0,
                    "tokens_saved": 0,
                    "raw_context_size": 0,
                    "session_start": time.time(),
                }
                return {
                    "success": True,
                    "message": "Session stats reset",
                }

            session_start = self.session_stats.get(
                "session_start",
            )
            duration_minutes = 0.0
            if session_start:
                duration_minutes = (time.time() - session_start) / 60

            total_requested = (
                self.session_stats["tokens_served"] + self.session_stats["tokens_saved"]
            )
            savings_percent = 0.0
            if total_requested > 0:
                savings_percent = (
                    self.session_stats["tokens_saved"] / total_requested * 100
                )

            return {
                "success": True,
                "session": {
                    "queries": (self.session_stats["queries"]),
                    "tokens_served": (self.session_stats["tokens_served"]),
                    "tokens_saved": (self.session_stats["tokens_saved"]),
                    "savings_percent": round(
                        savings_percent,
                        1,
                    ),
                    "duration_minutes": round(
                        duration_minutes,
                        1,
                    ),
                    "raw_context_size": (self.session_stats["raw_context_size"]),
                },
            }

        @self.mcp.tool("rlm_reindex")  # type: ignore[misc]
        async def reindex(
            path: Optional[str] = None,
            force: bool = False,
        ) -> Dict[str, Any]:
            """
            Reindex project or specific path.

            Args:
                path: Path to reindex
                    (defaults to project root)
                force: Force full reindex

            Returns:
                Reindex results
            """
            try:
                import time as time_module
                from ..indexer import AutoIndexer

                current_time = time_module.time()
                if (
                    current_time - self._last_reindex_time
                    < self._reindex_rate_limit_seconds
                ):
                    wait_time = int(
                        self._reindex_rate_limit_seconds
                        - (current_time - self._last_reindex_time)
                    )
                    return {
                        "success": False,
                        "error": (f"Rate limited. " f"Try again in {wait_time}s"),
                        "rate_limited": True,
                    }
                self._last_reindex_time = current_time

                project_root_str: str = path or os.getenv(
                    "RLM_PROJECT_ROOT",
                    os.getcwd(),
                )
                indexer = AutoIndexer(
                    Path(project_root_str),
                )

                if force:
                    result = indexer._index_full()
                    return {
                        "success": True,
                        "action": "full_reindex",
                        "files_indexed": (result.files_indexed),
                        "duration": (result.duration_seconds),
                    }
                else:
                    from ..storage import get_storage

                    storage = get_storage(
                        Path(project_root_str),
                    )
                    modified = storage.get_modified_files(
                        Path(project_root_str),
                    )

                    if modified:
                        updated = indexer.delta_update(modified)
                        return {
                            "success": True,
                            "action": "delta_update",
                            "files_updated": updated,
                        }
                    else:
                        return {
                            "success": True,
                            "action": "none",
                            "message": ("Index is up-to-date"),
                        }
            except Exception as e:
                logger.error(f"Reindex failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

        @self.mcp.tool("rlm_validate")  # type: ignore[misc]
        async def validate() -> Dict[str, Any]:
            """
            Validate index freshness and
            cross-references.

            Returns:
                Validation results
            """
            try:
                from ..storage import get_storage
                from ..freshness import (
                    CrossReferenceValidator,
                    ActualityReviewQueue,
                )

                project_root = os.getenv(
                    "RLM_PROJECT_ROOT",
                    os.getcwd(),
                )
                storage = get_storage(
                    Path(project_root),
                )

                crystals = {
                    c["crystal"]["path"]: c["crystal"] for c in storage.load_all()
                }

                validator = CrossReferenceValidator(
                    crystals,
                )
                stats = validator.get_validation_stats()
                stale = storage.get_stale_crystals(
                    ttl_hours=24,
                )

                return {
                    "success": True,
                    "symbols": stats,
                    "stale_files": len(stale),
                    "total_files": len(crystals),
                    "health": ("good" if len(stale) == 0 else "needs_refresh"),
                }
            except Exception as e:
                logger.error(
                    f"Validation failed: {e}",
                )
                return {
                    "success": False,
                    "error": str(e),
                }

        @self.mcp.tool("rlm_settings")  # type: ignore[misc]
        async def settings(
            action: str = "get",
            key: Optional[str] = None,
            value: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Get or set RLM settings.

            Args:
                action: 'get' or 'set'
                key: Setting key
                value: Setting value (for set)

            Returns:
                Current settings or update result
            """
            try:
                from ..storage import get_storage

                project_root = os.getenv(
                    "RLM_PROJECT_ROOT",
                    os.getcwd(),
                )
                storage = get_storage(
                    Path(project_root),
                )

                from ..memory.secure import (
                    SecureHierarchicalMemory,
                )

                if action == "get":
                    s = {
                        "project_root": project_root,
                        "secure_mode": isinstance(
                            self.memory,
                            SecureHierarchicalMemory,
                        ),
                        "ttl_hours": (
                            storage.get_metadata(
                                "ttl_hours",
                            )
                            or 24
                        ),
                        "auto_index": (
                            storage.get_metadata(
                                "auto_index",
                            )
                            or True
                        ),
                    }
                    return {
                        "success": True,
                        "settings": s,
                    }

                elif action == "set" and key:
                    storage.set_metadata(key, value)
                    return {
                        "success": True,
                        "updated": {key: value},
                    }

                else:
                    return {
                        "success": False,
                        "error": ("Use action='get' or " "action='set' with key/value"),
                    }
            except Exception as e:
                logger.error(
                    f"Settings failed: {e}",
                )
                return {
                    "success": False,
                    "error": str(e),
                }
