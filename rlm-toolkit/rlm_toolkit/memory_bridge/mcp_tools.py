# Memory Bridge — MCP Tools
"""
MCP tools для Memory Bridge.
Интеграция с RLM-Toolkit MCP Server.
Поддерживает как Server (mcp.server), так и FastMCP (mcp.server.fastmcp).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from mcp.server import Server
    from mcp.server.fastmcp import FastMCP
except ImportError:
    Server = None
    FastMCP = None

from .models import EntityType, HypothesisStatus
from .manager import MemoryBridgeManager


def register_memory_bridge_tools(
    server: Union["Server", "FastMCP", Any],
    manager: MemoryBridgeManager,
) -> None:
    """Register all Memory Bridge MCP tools on the server.

    Supports both mcp.server.Server and mcp.server.fastmcp.FastMCP.
    """
    # Default session for auto-restore
    DEFAULT_SESSION = "default"

    def _ensure_session() -> None:
        """Auto-restore default session if no active session.

        This enables fully automatic context injection:
        user just starts chatting, Memory Bridge handles the rest.
        """
        if manager._current_state is None:
            # Try to restore default session
            try:
                manager.start_session(session_id=DEFAULT_SESSION, restore=True)
            except Exception:
                # If no saved session, create new one
                manager.start_session(session_id=DEFAULT_SESSION, restore=False)

    @server.tool(
        name="rlm_start_session",
        description="Start a new session or restore existing one. Required before adding facts.",
    )
    async def rlm_start_session(
        session_id: Optional[str] = None,
        restore: bool = True,
    ) -> Dict[str, Any]:
        """Start or restore a session."""
        try:
            state = manager.start_session(session_id=session_id, restore=restore)
            return {
                "status": "success",
                "session_id": state.session_id,
                "version": state.version,
                "restored": restore and state.version > 1,
                "message": f"Session started: {state.session_id}",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_sync_state",
        description="Save current cognitive state to persistent storage",
    )
    async def rlm_sync_state() -> Dict[str, Any]:
        """Sync state to storage."""
        try:
            version = manager.sync_state()
            # Include debug info about storage path
            db_path = str(manager.storage.db_path) if manager.storage else "unknown"
            return {
                "status": "success",
                "version": version,
                "message": f"State synced (version {version})",
                "db_path": db_path,  # Debug: show actual path
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_restore_state",
        description="Restore cognitive state for a session",
    )
    async def rlm_restore_state(
        session_id: str,
        version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Restore state from storage."""
        try:
            state = manager.start_session(session_id=session_id, restore=True)
            return {
                "status": "success",
                "session_id": state.session_id,
                "version": state.version,
                "has_goal": state.primary_goal is not None,
                "facts_count": len(state.facts),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_auto_context",
        description="Auto-restore session and return context for prompt injection. "
        "One-call solution for always having project knowledge.",
    )
    async def rlm_auto_context(
        session_id: str = "default",
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """One-call: restore session + get compact state for injection."""
        try:
            # Auto-restore session
            state = manager.start_session(session_id=session_id, restore=True)

            # Get compact state for injection
            compact = manager.get_state_for_injection(max_tokens=max_tokens)

            return {
                "status": "success",
                "session_id": state.session_id,
                "version": state.version,
                "facts_count": len(state.facts),
                "decisions_count": len(state.decisions),
                "has_goal": state.primary_goal is not None,
                "context": compact,  # Ready for prompt injection
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_state",
        description="Get current cognitive state as compact string",
    )
    async def rlm_get_state(
        max_tokens: int = 500,
    ) -> Dict[str, Any]:
        """Get state for context injection."""
        try:
            _ensure_session()  # Auto-restore if needed
            compact = manager.get_state_for_injection(max_tokens)
            state = manager.get_state()
            return {
                "status": "success",
                "compact_state": compact,
                "session_id": state.session_id if state else None,
                "version": state.version if state else 0,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_update_goals",
        description="Set or update the primary goal",
    )
    async def rlm_update_goals(
        description: str,
        progress: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Update goals."""
        try:
            _ensure_session()  # Auto-restore if needed
            goal = manager.set_goal(description)
            if progress is not None:
                manager.update_goal_progress(progress)
            return {
                "status": "success",
                "goal_id": goal.id,
                "description": goal.description,
                "progress": goal.progress,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_record_decision",
        description="Record a decision with rationale",
    )
    async def rlm_record_decision(
        description: str,
        rationale: str,
        alternatives: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Record a decision."""
        try:
            _ensure_session()  # Auto-restore if needed
            decision = manager.record_decision(
                description=description,
                rationale=rationale,
                alternatives=alternatives or [],
            )
            return {
                "status": "success",
                "decision_id": decision.id,
                "description": decision.description,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_add_hypothesis",
        description="Add a hypothesis to test",
    )
    async def rlm_add_hypothesis(
        statement: str,
    ) -> Dict[str, Any]:
        """Add a hypothesis."""
        try:
            _ensure_session()  # Auto-restore if needed
            h = manager.add_hypothesis(statement)
            return {
                "status": "success",
                "hypothesis_id": h.id,
                "statement": h.statement,
                "hypothesis_status": h.status.value,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_add_fact",
        description="Add a fact with bi-temporal tracking",
    )
    async def rlm_add_fact(
        content: str,
        entity_type: str = "fact",
        confidence: float = 1.0,
        custom_type_name: Optional[str] = None,
        auto_start: bool = False,
    ) -> Dict[str, Any]:
        """Add a fact with bi-temporal tracking."""
        try:
            _ensure_session()  # Auto-restore if needed

            # Parse entity type
            try:
                etype = EntityType(entity_type.lower())
            except ValueError:
                import warnings

                warnings.warn(
                    f"Unknown entity_type '{entity_type}', "
                    f"falling back to 'other'.",
                    UserWarning,
                    stacklevel=2,
                )
                etype = EntityType.OTHER

            fact = manager.add_fact(
                content=content,
                entity_type=etype,
                confidence=confidence,
                custom_type_name=custom_type_name,
            )
            return {
                "status": "success",
                "fact_id": fact.id,
                "entity_type": fact.entity_type.value,
                "content": fact.content,
                "valid_at": fact.valid_at.isoformat() if fact.valid_at else None,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_search_facts",
        description="Hybrid search across facts (semantic + keyword + recency)",
    )
    async def rlm_search_facts(
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        keyword_weight: float = 0.3,
        recency_weight: float = 0.2,
    ) -> Dict[str, Any]:
        """Search facts using hybrid scoring."""
        try:
            results = manager.hybrid_search(
                query=query,
                top_k=top_k,
                semantic_weight=semantic_weight,
                keyword_weight=keyword_weight,
                recency_weight=recency_weight,
            )
            return {
                "status": "success",
                "query": query,
                "results": [
                    {
                        "fact_id": fact.id,
                        "content": fact.content,
                        "entity_type": fact.entity_type.value,
                        "score": round(score, 4),
                    }
                    for fact, score in results
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_build_communities",
        description="Cluster facts into communities using DBSCAN",
    )
    async def rlm_build_communities(
        min_cluster_size: int = 3,
    ) -> Dict[str, Any]:
        """Build fact communities."""
        try:
            communities = manager.build_communities(min_cluster_size)
            return {
                "status": "success",
                "communities_count": len(communities),
                "communities": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "fact_count": len(c.fact_ids),
                    }
                    for c in communities
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_list_sessions",
        description="List all saved sessions",
    )
    async def rlm_list_sessions() -> Dict[str, Any]:
        """List all sessions."""
        try:
            sessions = manager.storage.list_sessions()
            return {
                "status": "success",
                "sessions": sessions,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_delete_session",
        description="Delete a session and all its versions (AC-06.4)",
    )
    async def rlm_delete_session(session_id: str) -> Dict[str, Any]:
        """Delete a session."""
        try:
            deleted_count = manager.storage.delete_session(session_id)
            return {
                "status": "success",
                "session_id": session_id,
                "deleted_versions": deleted_count,
                "message": (
                    f"Deleted {deleted_count} version(s)"
                    if deleted_count > 0
                    else "Session not found"
                ),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_audit_log",
        description="Get audit log entries for state changes (AC-04.4)",
    )
    async def rlm_get_audit_log(
        session_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get audit log entries."""
        try:
            entries = manager.storage.get_audit_log(session_id, limit)
            return {
                "status": "success",
                "entries_count": len(entries),
                "entries": entries,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
