"""Routing tools: route_context, auto_inject, enterprise_context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import ToolComponents

from ..v2.hierarchical import MemoryLevel


class RoutingTools:
    """Semantic routing and context injection tools."""

    def __init__(self, components: ToolComponents):
        self.c = components

    def register(self, server):
        c = self.c

        @server.tool(
            name="rlm_route_context",
            description=(
                "Semantic routing to get only relevant "
                "facts for a query. Loads L0 always, "
                "routes L1/L2 by similarity."
            ),
        )
        async def rlm_route_context(
            query: str,
            max_tokens: int = 2000,
            include_stale: bool = False,
        ) -> Dict[str, Any]:
            """Route context based on semantic similarity."""
            try:
                result = c.router.route(
                    query=query,
                    max_tokens=max_tokens,
                    include_stale=include_stale,
                )
                formatted = c.router.format_context_for_injection(result)
                return {
                    "status": "success",
                    "facts_count": len(result.facts),
                    "total_tokens": result.total_tokens,
                    "routing_confidence": (result.routing_confidence),
                    "routing_explanation": (result.routing_explanation),
                    "domains_loaded": result.domains_loaded,
                    "fallback_used": result.fallback_used,
                    "context": formatted,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_auto_inject",
            description=(
                "Get optimized context for automatic "
                "injection into LLM prompts. Returns L0 "
                "facts (always) + semantic context for "
                "active file. Use this to solve LLM "
                "amnesia between sessions."
            ),
        )
        async def rlm_auto_inject(
            active_file: Optional[str] = None,
            max_tokens: int = 2000,
            include_decisions: bool = True,
        ) -> Dict[str, Any]:
            """Get auto-inject context for LLM prompts."""
            try:
                parts = []

                # L0 facts (always loaded)
                l0_facts = c.store.get_facts_by_level(MemoryLevel.L0_PROJECT)
                if l0_facts:
                    parts.append("## Project Context (L0)")
                    for f in l0_facts:
                        parts.append(f"- {f.content}")

                # Semantic route for active file
                if active_file:
                    query = f"context for {active_file}"
                    result = c.router.route(
                        query=query,
                        max_tokens=max_tokens // 2,
                    )
                    if result.facts:
                        parts.append("\n## Relevant Context")
                        fmt = c.router.format_context_for_injection(result)
                        parts.append(fmt)

                # Recent decisions
                if include_decisions:
                    try:
                        decisions = c.causal_tracker.get_all_decisions()
                        if decisions:
                            parts.append("\n## Recent Decisions")
                            for d in decisions[:5]:
                                parts.append(f"- {d.content}")
                    except Exception:
                        pass

                context = "\n".join(parts)
                return {
                    "status": "success",
                    "context": context,
                    "token_estimate": (len(context.split()) * 1.3),
                    "l0_count": len(l0_facts),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_enterprise_context",
            description=(
                "One-call enterprise context with "
                "auto-discovery, semantic routing, and "
                "causal chains. Zero configuration. "
                "RECOMMENDED: Use this instead of "
                "individual tools."
            ),
        )
        async def rlm_enterprise_context(
            query: str,
            max_tokens: int = 3000,
            mode: str = "auto",
            include_causal: bool = True,
            task_hint: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Enterprise context in one call."""
            try:
                result = c.context_builder.build(
                    query=query,
                    max_tokens=max_tokens,
                    mode=mode,
                    include_causal=include_causal,
                    task_hint=task_hint,
                )
                return {
                    "status": "success",
                    "context": result.context,
                    "token_estimate": (result.token_estimate),
                    "discovery_ran": result.discovery_ran,
                    "facts_loaded": result.facts_loaded,
                    "suggestions": result.suggestions,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
