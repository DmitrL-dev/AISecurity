# Facts tools — CRUD, TTL, hierarchy, consolidation, domains
"""
Tools: approve_fact, add_hierarchical_fact, delete_fact,
       refresh_fact, get_facts_by_domain, list_domains,
       get_hierarchy_stats, get_stale_facts, set_ttl,
       index_embeddings, consolidate_facts
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ._common import ToolComponents, ServerType
from ..v2.hierarchical import MemoryLevel, TTLAction


def register_facts_tools(
    server: ServerType,
    c: ToolComponents,
) -> None:
    """Register fact management MCP tools."""

    store = c.store
    router = c.router
    ttl_manager = c.ttl_manager
    causal_tracker = c.causal_tracker

    @server.tool(
        name="rlm_approve_fact",
        description="Approve and store an extracted fact " "candidate.",
    )
    async def rlm_approve_fact(
        content: str,
        level: int = 1,
        domain: Optional[str] = None,
        module: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve and store a fact candidate."""
        try:
            fact_id = store.add_fact(
                content=content,
                level=MemoryLevel(level),
                domain=domain,
                module=module,
                source="approved",
                confidence=1.0,
            )
            return {
                "status": "success",
                "fact_id": fact_id,
                "content": content,
                "level": level,
                "domain": domain,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_add_hierarchical_fact",
        description="Add fact with hierarchical levels (L0-L3).",
    )
    async def rlm_add_hierarchical_fact(
        content: str,
        level: int = 0,
        domain: Optional[str] = None,
        module: Optional[str] = None,
        code_ref: Optional[str] = None,
        parent_id: Optional[str] = None,
        ttl_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a fact with full hierarchy support."""
        try:
            from ..v2.hierarchical import TTLConfig

            ttl_config = None
            if ttl_days:
                ttl_config = TTLConfig(
                    ttl_seconds=ttl_days * 24 * 3600,
                    on_expire=TTLAction.MARK_STALE,
                )

            fact_id = store.add_fact(
                content=content,
                level=MemoryLevel(level),
                domain=domain,
                module=module,
                code_ref=code_ref,
                parent_id=parent_id,
                ttl_config=ttl_config,
                source="manual",
                confidence=1.0,
            )

            return {
                "status": "success",
                "fact_id": fact_id,
                "content": content,
                "level": MemoryLevel(level).name,
                "domain": domain,
                "module": module,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_set_ttl",
        description="Set TTL (Time-To-Live) configuration " "for a fact.",
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
            success = ttl_manager.set_ttl(
                fact_id=fact_id,
                ttl_seconds=ttl_days * 24 * 3600,
                refresh_trigger=refresh_trigger,
                on_expire=action,
            )
            return {
                "status": "success" if success else "error",
                "fact_id": fact_id,
                "ttl_days": ttl_days,
                "refresh_trigger": refresh_trigger,
                "on_expire": on_expire,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_stale_facts",
        description="Get facts that have expired or need " "review.",
    )
    async def rlm_get_stale_facts(
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        """Get stale/expired facts."""
        try:
            report = ttl_manager.process_expired()
            all_facts = store.get_all_facts(include_stale=True)
            stale_facts = [f for f in all_facts if f.is_stale]

            return {
                "status": "success",
                "stale_count": len(stale_facts),
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
                    for f in stale_facts[:20]
                ],
                "ttl_report": report.to_dict(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_index_embeddings",
        description="Generate embeddings for all facts "
        "without embeddings. "
        "Required for semantic routing.",
    )
    async def rlm_index_embeddings() -> Dict[str, Any]:
        """Index all facts with embeddings."""
        try:
            indexed = router.index_all_facts()
            return {
                "status": "success",
                "indexed_count": indexed,
                "message": (f"Indexed {indexed} facts with embeddings"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_hierarchy_stats",
        description="Get statistics about the hierarchical " "memory store.",
    )
    async def rlm_get_hierarchy_stats() -> Dict[str, Any]:
        """Get memory store statistics."""
        try:
            stats = store.get_stats()
            causal_stats = causal_tracker.get_stats()
            return {
                "status": "success",
                "memory_store": stats,
                "causal_chains": causal_stats,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_facts_by_domain",
        description="Get all facts for a specific domain.",
    )
    async def rlm_get_facts_by_domain(
        domain: str,
        include_stale: bool = False,
    ) -> Dict[str, Any]:
        """Get facts for a domain."""
        try:
            facts = store.get_domain_facts(domain)
            if not include_stale:
                facts = [f for f in facts if not f.is_stale]
            return {
                "status": "success",
                "domain": domain,
                "facts_count": len(facts),
                "facts": [
                    {
                        "id": f.id,
                        "content": f.content,
                        "level": f.level.name,
                        "module": f.module,
                        "is_stale": f.is_stale,
                    }
                    for f in facts
                ],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_list_domains",
        description="List all discovered domains in the " "memory store.",
    )
    async def rlm_list_domains() -> Dict[str, Any]:
        """List all domains."""
        try:
            domains = store.get_domains()
            domain_counts = {}
            for domain in domains:
                facts = store.get_domain_facts(domain)
                domain_counts[domain] = len(facts)
            return {
                "status": "success",
                "domains": domains,
                "domain_counts": domain_counts,
                "total_domains": len(domains),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_refresh_fact",
        description="Refresh TTL for a fact, resetting its " "expiration timer.",
    )
    async def rlm_refresh_fact(
        fact_id: str,
    ) -> Dict[str, Any]:
        """Refresh TTL for a fact."""
        try:
            success = ttl_manager.refresh_ttl(fact_id)
            return {
                "status": ("success" if success else "error"),
                "fact_id": fact_id,
                "message": ("TTL refreshed" if success else "Fact not found"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_delete_fact",
        description="Delete a fact from the hierarchical " "memory store.",
    )
    async def rlm_delete_fact(
        fact_id: str,
    ) -> Dict[str, Any]:
        """Delete a fact."""
        try:
            success = store.delete_fact(fact_id)
            return {
                "status": ("success" if success else "error"),
                "fact_id": fact_id,
                "message": ("Fact deleted" if success else "Fact not found"),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_consolidate_facts",
        description="Consolidate granular facts into "
        "higher-level summaries. "
        "Aggregates L3→L2→L1 and deduplicates similar facts.",
    )
    async def rlm_consolidate_facts(
        min_facts: int = 5,
    ) -> Dict[str, Any]:
        """Run fact consolidation."""
        try:
            from ..v2.consolidator import FactConsolidator

            consolidator = FactConsolidator(
                store=store,
                min_facts_to_consolidate=min_facts,
            )
            result = consolidator.consolidate()
            return {
                "status": "success",
                "merged_count": result.merged_count,
                "promoted_count": result.promoted_count,
                "archived_count": result.archived_count,
                "new_summaries": result.new_summaries,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
