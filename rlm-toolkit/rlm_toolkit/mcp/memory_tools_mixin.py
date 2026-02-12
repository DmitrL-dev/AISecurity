"""Memory tool handlers for RLMServer.

H-MEM tools: store, recall, forget, consolidate, stats.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..memory.hierarchical import HierarchicalMemory

logger = logging.getLogger("rlm_mcp")


class MemoryToolsMixin:
    """H-MEM Memory tools for RLMServer."""

    if TYPE_CHECKING:
        memory: HierarchicalMemory

    def _register_memory_tools(self) -> None:
        """Register memory-related MCP tools."""

        @self.mcp.tool("rlm_memory")  # type: ignore[attr-defined, misc]
        async def memory(
            action: str,
            content: Optional[str] = None,
            topic: Optional[str] = None,
        ) -> Dict[str, Any]:
            """
            Manage H-MEM hierarchical memory.

            Args:
                action: Action to perform -
                    recall, store, forget,
                    consolidate, stats
                content: Content to store
                    (for 'store' action)
                topic: Topic to recall/forget
                    (for 'recall'/'forget' actions)

            Returns:
                Memory operation result
            """
            try:
                if action == "store":
                    if not content:
                        return {
                            "success": False,
                            "error": ("Content required for store"),
                        }
                    memory_id = self.memory.add_episode(
                        content=content,
                        metadata={"source": "mcp_tool"},
                    )
                    logger.info(
                        f"Stored episode: {memory_id}",
                    )
                    return {
                        "success": True,
                        "action": "store",
                        "memory_id": memory_id,
                    }

                elif action == "recall":
                    query = topic or ""
                    results = self.memory.retrieve(
                        query,
                        top_k=5,
                    )
                    return {
                        "success": True,
                        "action": "recall",
                        "query": query,
                        "count": len(results),
                        "memories": [
                            {
                                "id": m.id,
                                "content": m.content[:200],
                                "level": m.level.name,
                                "score": getattr(
                                    m,
                                    "score",
                                    0,
                                ),
                            }
                            for m in results[:10]
                        ],
                    }

                elif action == "forget":
                    if not topic:
                        return {
                            "success": False,
                            "error": ("Topic required for forget"),
                        }
                    results = self.memory.retrieve(
                        topic,
                        top_k=5,
                    )
                    removed = 0
                    for m in results:
                        if hasattr(self.memory, "remove"):
                            self.memory.remove(m.id)
                            removed += 1
                    return {
                        "success": True,
                        "action": "forget",
                        "topic": topic,
                        "removed_count": removed,
                    }

                elif action == "consolidate":
                    if hasattr(
                        self.memory,
                        "consolidate",
                    ):
                        self.memory.consolidate()
                    return {
                        "success": True,
                        "action": "consolidate",
                        "message": ("Consolidation triggered"),
                    }

                elif action == "stats":
                    stats = (
                        self.memory.get_stats()
                        if hasattr(
                            self.memory,
                            "get_stats",
                        )
                        else {}
                    )
                    return {
                        "success": True,
                        "action": "stats",
                        "stats": stats,
                    }

                else:
                    return {
                        "success": False,
                        "error": (
                            f"Unknown action: {action}. "
                            f"Use: recall, store, forget, "
                            f"consolidate, stats"
                        ),
                    }

            except Exception as e:
                logger.error(
                    f"Memory operation failed: {e}",
                )
                return {
                    "success": False,
                    "error": str(e),
                }
