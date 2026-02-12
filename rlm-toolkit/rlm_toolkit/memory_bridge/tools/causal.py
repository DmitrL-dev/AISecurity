# Causal tools — decision chains, causal reasoning
"""
Tools: get_causal_chain, record_causal_decision
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._common import ToolComponents, ServerType


def register_causal_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register causal chain MCP tools."""

    causal_tracker = c.causal_tracker

    @server.tool(
        name="rlm_get_causal_chain",
        description="Query reasoning history for a decision. "
        "Returns full causal chain with reasons and "
        "consequences.",
    )
    async def rlm_get_causal_chain(
        query: str,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Query causal chain for a decision."""
        try:
            chain = causal_tracker.query_chain(
                query=query,
                max_depth=max_depth,
            )
            if not chain:
                return {
                    "status": "success",
                    "found": False,
                    "message": (f"No decision found matching: " f"{query}"),
                }

            mermaid = causal_tracker.visualize(chain)
            summary = causal_tracker.format_chain_summary(chain)

            return {
                "status": "success",
                "found": True,
                "decision": chain.root.content,
                "reasons": [r.content for r in chain.reasons],
                "consequences": [c.content for c in chain.consequences],
                "constraints": [c.content for c in chain.constraints],
                "total_nodes": len(chain.nodes),
                "mermaid": mermaid,
                "summary": summary,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_record_causal_decision",
        description="Record a decision with full causal "
        "context: reasons, consequences, constraints, "
        "alternatives.",
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
            decision_id = causal_tracker.record_decision(
                decision=decision,
                reasons=reasons,
                consequences=consequences,
                constraints=constraints,
                alternatives=alternatives,
            )
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
            return {"status": "error", "message": str(e)}
