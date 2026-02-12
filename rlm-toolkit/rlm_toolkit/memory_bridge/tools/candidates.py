# Candidates tools — approval workflow
"""
Tools: get_pending_candidates, approve_candidate,
       reject_candidate, approve_all_candidates
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ._common import ToolComponents, ServerType
from ..v2.hierarchical import MemoryLevel


def register_candidates_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register candidate approval MCP tools."""

    store = c.store
    project_root = c.project_root

    @server.tool(
        name="rlm_get_pending_candidates",
        description="Get pending fact candidates awaiting "
        "user approval. "
        "Returns candidates with confidence 0.5-0.8 for "
        "review.",
    )
    async def rlm_get_pending_candidates(
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get pending candidates for review."""
        try:
            pending_db = Path(project_root) / ".rlm" / "pending_candidates.db"
            if not pending_db.exists():
                return {
                    "status": "success",
                    "candidates": [],
                    "count": 0,
                }

            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {
                    "status": "error",
                    "message": "Pending store not found",
                }

            candidates = pending_store.get_pending(limit=limit)
            stats = pending_store.get_stats()

            return {
                "status": "success",
                "candidates": [
                    {
                        "id": c.id,
                        "content": (
                            c.content[:200] + "..."
                            if len(c.content) > 200
                            else c.content
                        ),
                        "source": c.source,
                        "confidence": c.confidence,
                        "domain": c.domain,
                        "level": c.level,
                    }
                    for c in candidates
                ],
                "count": len(candidates),
                "stats": stats,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_approve_candidate",
        description="Approve a pending fact candidate and " "add it to facts store.",
    )
    async def rlm_approve_candidate(
        candidate_id: str,
    ) -> Dict[str, Any]:
        """Approve a pending candidate."""
        try:
            pending_db = Path(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {
                    "status": "error",
                    "message": "Pending store not found",
                }

            candidate = pending_store.approve(candidate_id)
            if not candidate:
                return {
                    "status": "error",
                    "message": "Candidate not found",
                }

            fact_id = store.add_fact(
                content=candidate.content,
                level=MemoryLevel(candidate.level),
                domain=candidate.domain,
                source=f"approved:{candidate.source}",
                confidence=1.0,
            )

            return {
                "status": "success",
                "fact_id": fact_id,
                "content": candidate.content[:100],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_reject_candidate",
        description="Reject a pending fact candidate.",
    )
    async def rlm_reject_candidate(
        candidate_id: str,
    ) -> Dict[str, Any]:
        """Reject a pending candidate."""
        try:
            pending_db = Path(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {
                    "status": "error",
                    "message": "Pending store not found",
                }

            success = pending_store.reject(candidate_id)
            return {
                "status": ("success" if success else "error"),
                "message": ("Candidate rejected" if success else "Not found"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_approve_all_candidates",
        description="Approve all pending fact candidates " "at once.",
    )
    async def rlm_approve_all_candidates() -> Dict[str, Any]:
        """Approve all pending candidates."""
        try:
            pending_db = Path(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {
                    "status": "error",
                    "message": "Pending store not found",
                }

            candidates = pending_store.approve_all()

            for candidate in candidates:
                store.add_fact(
                    content=candidate.content,
                    level=MemoryLevel(candidate.level),
                    domain=candidate.domain,
                    source=(f"approved:{candidate.source}"),
                    confidence=1.0,
                )

            return {
                "status": "success",
                "approved_count": len(candidates),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
