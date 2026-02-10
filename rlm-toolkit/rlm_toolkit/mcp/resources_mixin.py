"""MCP resource registration mixin for RLMServer.

Extracted from server.py _register_resources() method.
Contains: rlm://context, rlm://status, rlm://events resources.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("rlm_mcp")


class ResourcesMixin:
    """MCP resource registration for RLMServer."""

    if TYPE_CHECKING:
        mcp: FastMCP[Any]
        memory_bridge_v2_store: Any
        memory_bridge_v2_components: Dict[str, Any]
        session_stats: Dict[str, Any]
        indexer: Any

    def _register_resources(self) -> None:
        """Register MCP resources for auto-context
        injection (v2.5 Anti-Amnesia)."""
        if not self.mcp:
            return

        @self.mcp.resource("rlm://context")  # type: ignore[misc]
        async def get_project_context() -> str:
            """
            Auto-injected project context.

            This resource provides persistent project
            knowledge that LLM clients can automatically
            include in their context. Solves the
            "amnesia" problem.

            Returns:
                Formatted markdown with L0 facts,
                domain context, and recent decisions.
            """
            try:
                sections = []

                # === L0: Project Architecture ===
                if self.memory_bridge_v2_store:
                    from ..memory_bridge.v2.hierarchical import (  # noqa: E501
                        MemoryLevel,
                    )

                    l0_facts = self.memory_bridge_v2_store.get_facts_by_level(
                        MemoryLevel.L0_PROJECT
                    )
                    if l0_facts:
                        sections.append("## 🏗️ Project Architecture")
                        for fact in l0_facts[:10]:
                            sections.append(f"- {fact.content}")

                # === L1: Active Domains ===
                if self.memory_bridge_v2_store:
                    domains = self.memory_bridge_v2_store.get_domains()
                    if domains:
                        sections.append("\n## 📂 Active Domains")
                        for domain in list(domains)[:5]:
                            sections.append(f"- {domain}")

                # === Recent Decisions ===
                causal_tracker = self.memory_bridge_v2_components.get("causal_tracker")
                if causal_tracker:
                    try:
                        recent = causal_tracker.get_recent_decisions(limit=3)
                        if recent:
                            sections.append("\n## 🎯 Recent " "Decisions")
                            for d in recent:
                                sections.append(f"- {d.content}")
                    except Exception:
                        pass

                # === Session Stats ===
                sections.append("\n## 📊 Session")
                sections.append(
                    f"- Queries: " f"{self.session_stats.get('queries', 0)}"
                )
                sections.append(
                    f"- Tokens saved: " f"{self.session_stats.get('tokens_saved', 0):,}"
                )

                if sections:
                    return "\n".join(sections)
                else:
                    return (
                        "# RLM Project Context\n\n"
                        "No project facts discovered "
                        "yet. Run "
                        "`rlm_discover_project` first."
                    )

            except Exception as e:
                logger.error(f"Context resource error: {e}")
                return f"# RLM Context Error\n\n{str(e)}"

        @self.mcp.resource("rlm://status")  # type: ignore[misc]
        async def get_status_resource() -> str:
            """Quick status check for LLM context."""
            try:
                stats = self.indexer.get_stats() if self.indexer else {}
                return (
                    f"# RLM Status\n"
                    f"- Crystals: "
                    f"{stats.get('total_crystals', 0)}\n"
                    f"- Tokens: "
                    f"{stats.get('total_tokens', 0):,}\n"
                    f"- Version: 2.5.0\n"
                )
            except Exception as e:
                return f"# RLM Status Error\n\n{str(e)}"

        @self.mcp.resource("rlm://events")  # type: ignore[misc]
        async def get_context_events() -> str:
            """
            Context change notifications (persistent).

            Poll this resource to check if project
            context has been updated since you last
            read it. Reads from SQLite for
            cross-process support.
            """
            try:
                import rlm_toolkit

                pkg_path = Path(rlm_toolkit.__file__).parent.parent
                project_root = Path(
                    os.getenv(
                        "RLM_PROJECT_ROOT",
                        str(pkg_path),
                    )
                )
                marker_file = project_root / ".rlm" / "context_changed.json"

                if not marker_file.exists():
                    return (
                        "# ✓ Context Current\n"
                        "- Version: 0\n"
                        "- Status: unchanged "
                        "(no marker file yet)\n"
                    )

                data = json.loads(marker_file.read_text())
                version = data.get("version", 0)
                changed = data.get("changed", False)
                events = data.get("events", [])

                if changed:
                    data["changed"] = False
                    marker_file.write_text(json.dumps(data, indent=2))

                    events_str = "\n".join(
                        [
                            f"  - {e['reason']} " f"({e['timestamp'][:19]})"
                            for e in events[:3]
                        ]
                    )
                    return (
                        f"# 🔔 Context Changed!\n"
                        f"- Version: {version}\n"
                        f"- Status: UPDATED\n"
                        f"- Hint: Call "
                        f'`read_resource("rlm://context")'
                        f"` for fresh context\n"
                        f"- Recent events:\n"
                        f"{events_str}\n"
                    )
                else:
                    return (
                        f"# ✓ Context Current\n"
                        f"- Version: {version}\n"
                        f"- Status: unchanged\n"
                    )

            except Exception as e:
                logger.error(f"Context events error: {e}")
                return f"# Context Events Error\n\n" f"{str(e)}"

        logger.info(
            "MCP resources registered: " "rlm://context, rlm://status, rlm://events"
        )
