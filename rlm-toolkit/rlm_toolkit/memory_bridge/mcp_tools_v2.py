# Memory Bridge v2.0/v2.1 — MCP Tools (Facade)
"""
MCP tools for Memory Bridge v2.x Enterprise features.

This module is a thin facade that delegates to domain-specific
tool modules under `tools/`:
- discovery: discover_project, discover_deep, reindex
- routing: route_context, auto_inject, enterprise_context
- facts: extract/approve/reject/consolidate facts
- lifecycle: TTL, stale facts, refresh, delete
- infra: stats, domains, health, enforcement, hooks, embeddings

v2.0 Tools:
- rlm_discover_project, rlm_route_context, rlm_extract_facts
- rlm_get_causal_chain, rlm_set_ttl, rlm_get_stale_facts
- rlm_index_embeddings

v2.1 Auto-Mode:
- rlm_enterprise_context, rlm_install_git_hooks

v2.4 Extension Compatibility:
- rlm_reindex
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from mcp.server import Server
    from mcp.server.fastmcp import FastMCP
except ImportError:
    Server = None
    FastMCP = None

from .v2.hierarchical import HierarchicalMemoryStore
from .v2.causal import CausalChainTracker
from .v2.hierarchical import MemoryLevel

from .tools import init_components, InlinePendingStore
from .tools.discovery import DiscoveryTools
from .tools.routing import RoutingTools
from .tools.facts import FactTools
from .tools.lifecycle import LifecycleTools
from .tools.infra import InfraTools


def register_memory_bridge_v2_tools(
    server: Union["Server", "FastMCP", Any],
    store: HierarchicalMemoryStore,
    project_root: Optional[Path] = None,
    on_context_change: Optional[callable] = None,
) -> Dict[str, Any]:
    """
    Register Memory Bridge v2.0 MCP tools on the server.

    Args:
        server: MCP server instance (Server or FastMCP)
        store: Hierarchical memory store
        project_root: Project root path
        on_context_change: Optional callback(reason: str)
            called when context changes

    Returns dict with initialized components for external access.
    """
    components = init_components(
        store=store,
        project_root=project_root,
        on_context_change=on_context_change,
    )

    # Register domain tool groups
    DiscoveryTools(components).register(server)
    RoutingTools(components).register(server)
    FactTools(components).register(server)
    LifecycleTools(components).register(server)
    InfraTools(components).register(server)

    # Causal tools (inline — only 2 handlers)
    c = components

    @server.tool(
        name="rlm_get_causal_chain",
        description=(
            "Query reasoning history for a decision. "
            "Returns full causal chain with reasons "
            "and consequences."
        ),
    )
    async def rlm_get_causal_chain(
        query: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Query causal chain for a decision."""
        try:
            chain = c.causal_tracker.query_chain(
                query=query,
                max_depth=max_depth,
            )
            if not chain:
                return {
                    "status": "success",
                    "found": False,
                    "error": (f"No decision found matching: " f"{query}"),
                }
            mermaid = c.causal_tracker.visualize(chain)
            summary = c.causal_tracker.format_chain_summary(chain)
            return {
                "status": "success",
                "found": True,
                "decision": chain.root.content,
                "reasons": [r.content for r in chain.reasons],
                "consequences": [co.content for co in chain.consequences],
                "constraints": [co.content for co in chain.constraints],
                "total_nodes": len(chain.nodes),
                "mermaid": mermaid,
                "summary": summary,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @server.tool(
        name="rlm_record_causal_decision",
        description=(
            "Record a decision with full causal context: "
            "reasons, consequences, constraints, "
            "alternatives."
        ),
    )
    async def rlm_record_causal_decision(
        decision: str,
        reasons: Optional[List[str]] = None,
        consequences: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        alternatives: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record a decision with causal context."""
        try:
            decision_id = c.causal_tracker.record_decision(
                decision=decision,
                reasons=reasons,
                consequences=consequences,
                constraints=constraints,
                alternatives=alternatives,
            )
            c.events.notify("record_causal_decision")
            return {
                "status": "success",
                "decision_id": decision_id,
                "decision": decision,
                "reasons_count": len(reasons or []),
                "consequences_count": len(consequences or []),
                "constraints_count": len(constraints or []),
                "alternatives_count": len(alternatives or []),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return components.to_dict()
