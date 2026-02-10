# Context tools — semantic routing, enterprise context
"""
Tools: route_context, enterprise_context
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ._common import ToolComponents, ServerType


def register_context_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register context/routing MCP tools."""

    router = c.router
    orchestrator = c.orchestrator
    context_builder = c.context_builder

    @server.tool(
        name="rlm_route_context",
        description="Semantic routing to get only relevant facts "
        "for a query. "
        "Loads L0 always, routes L1/L2 by similarity.",
    )
    async def rlm_route_context(
        query: str,
        max_tokens: int = 2000,
        include_stale: bool = False,
    ) -> Dict[str, Any]:
        """Route context based on semantic similarity."""
        try:
            result = router.route(
                query=query,
                max_tokens=max_tokens,
                include_stale=include_stale,
            )
            formatted = router.format_context_for_injection(result)
            return {
                "status": "success",
                "facts_count": len(result.facts),
                "total_tokens": result.total_tokens,
                "routing_confidence": result.routing_confidence,
                "routing_explanation": (result.routing_explanation),
                "domains_loaded": result.domains_loaded,
                "fallback_used": result.fallback_used,
                "context": formatted,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_enterprise_context",
        description="One-call enterprise context with "
        "auto-discovery, semantic routing, and causal chains. "
        "Zero configuration. "
        "RECOMMENDED: Use this instead of individual tools.",
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
            if mode == "discovery":
                orchestrator.force_discovery(task_hint=task_hint)
            elif mode == "auto":
                orchestrator.discover_or_restore(task_hint=task_hint)

            context = context_builder.build(
                query=query,
                max_tokens=max_tokens,
                include_causal=include_causal,
                task_hint=task_hint,
            )

            return {
                "status": "success",
                "context": context.to_injection_string(),
                "facts_count": len(context.facts),
                "tokens_used": context.total_tokens,
                "discovery_performed": (context.discovery_performed),
                "causal_included": bool(context.causal_summary),
                "suggestions": [s.to_dict() for s in context.suggestions],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
