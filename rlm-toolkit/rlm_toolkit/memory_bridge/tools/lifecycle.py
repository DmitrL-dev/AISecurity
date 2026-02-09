"""Lifecycle tools: set_ttl, get_stale_facts, refresh_fact, delete_fact."""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from . import ToolComponents

from ..v2.hierarchical import TTLAction


class LifecycleTools:
    """TTL and fact lifecycle management tools."""

    def __init__(self, components: ToolComponents):
        self.c = components

    def register(self, server):
        c = self.c

        @server.tool(
            name="rlm_set_ttl",
            description=("Set TTL (Time-To-Live) configuration " "for a fact."),
        )
        async def rlm_set_ttl(
            fact_id: str,
            ttl_days: int,
            refresh_trigger: Optional[str] = None,
            on_expire: str = "mark_stale",
        ) -> Dict[str, Any]:
            """Set TTL for a fact."""
            try:
                action = TTLAction(on_expire)
                success = c.ttl_manager.set_ttl(
                    fact_id=fact_id,
                    ttl_seconds=ttl_days * 24 * 3600,
                    refresh_trigger=refresh_trigger,
                    on_expire=action,
                )
                return {
                    "status": ("success" if success else "error"),
                    "fact_id": fact_id,
                    "ttl_days": ttl_days,
                    "refresh_trigger": refresh_trigger,
                    "on_expire": on_expire,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_get_stale_facts",
            description=("Get facts that have expired or need " "review."),
        )
        async def rlm_get_stale_facts(
            include_archived: bool = False,
        ) -> Dict[str, Any]:
            """Get stale/expired facts."""
            try:
                report = c.ttl_manager.process_expired()
                all_facts = c.store.get_all_facts(include_stale=True)
                stale = [f for f in all_facts if f.is_stale]
                return {
                    "status": "success",
                    "stale_count": len(stale),
                    "stale_facts": [
                        {
                            "id": f.id,
                            "content": (
                                f.content[:100] + "..."
                                if len(f.content) > 100
                                else f.content
                            ),
                            "level": f.level.name,
                            "domain": f.domain,
                            "created_at": (f.created_at.isoformat()),
                        }
                        for f in stale[:20]
                    ],
                    "ttl_report": report.to_dict(),
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_refresh_fact",
            description=("Refresh TTL for a fact, resetting its " "expiration timer."),
        )
        async def rlm_refresh_fact(
            fact_id: str,
        ) -> Dict[str, Any]:
            """Refresh TTL for a fact."""
            try:
                success = c.ttl_manager.refresh(fact_id)
                return {
                    "status": ("success" if success else "error"),
                    "fact_id": fact_id,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}

        @server.tool(
            name="rlm_delete_fact",
            description=("Delete a fact from the hierarchical " "memory store."),
        )
        async def rlm_delete_fact(
            fact_id: str,
        ) -> Dict[str, Any]:
            """Delete a fact."""
            try:
                success = c.store.delete_fact(fact_id)
                if success:
                    c.events.notify("delete_fact")
                return {
                    "status": ("success" if success else "error"),
                    "fact_id": fact_id,
                }
            except Exception as e:
                return {"status": "error", "error": str(e)}
