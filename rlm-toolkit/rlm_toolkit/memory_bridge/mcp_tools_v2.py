# Memory Bridge v2.0/v2.1 — MCP Tools
"""
MCP tools for Memory Bridge v2.x Enterprise features.

v2.0 Tools:
- rlm_discover_project: Smart cold start discovery
- rlm_route_context: Semantic context routing
- rlm_extract_facts: Auto-extract facts from changes
- rlm_get_causal_chain: Query decision reasoning
- rlm_set_ttl: Configure fact TTL
- rlm_get_stale_facts: List expired facts
- rlm_index_embeddings: Generate embeddings for semantic search

v2.1 Auto-Mode:
- rlm_enterprise_context: One-call zero-friction context (recommended)
- rlm_install_git_hooks: Install git hooks for auto-extraction
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

from .v2.hierarchical import HierarchicalMemoryStore, MemoryLevel, TTLAction
from .v2.router import SemanticRouter, EmbeddingService
from .v2.extractor import AutoExtractionEngine
from .v2.ttl import TTLManager
from .v2.causal import CausalChainTracker
from .v2.coldstart import ColdStartOptimizer
from .v2.automode import (
    DiscoveryOrchestrator,
    EnterpriseContextBuilder,
)


# ============================================================================
# Inline Pending Candidates Store (avoids import path issues in subprocess)
# ============================================================================
class InlinePendingStore:
    """Minimal SQLite store for pending fact candidates."""

    def __init__(self, db_path: Path):
        import sqlite3

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_candidates (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    domain TEXT,
                    level INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """
            )
            conn.commit()
        finally:
            conn.close()

    def add(self, candidate_id, content, source, confidence, domain, level):
        import sqlite3
        from datetime import datetime

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO pending_candidates
                (id, content, source, confidence, domain, level, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
                (
                    candidate_id,
                    content,
                    source,
                    confidence,
                    domain,
                    level,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_pending(self, limit=50):
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates
                WHERE status = 'pending'
                ORDER BY confidence DESC LIMIT ?
            """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def approve_all(self):
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                SELECT * FROM pending_candidates WHERE status = 'pending'
            """
            )
            conn.row_factory = sqlite3.Row
            pending = [dict(row) for row in cursor.fetchall()]
            conn.execute(
                """
                UPDATE pending_candidates SET status = 'approved'
                WHERE status = 'pending'
            """
            )
            conn.commit()
            return pending
        finally:
            conn.close()

    def get_stats(self):
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) FROM pending_candidates GROUP BY status
            """
            )
            stats = {row[0]: row[1] for row in cursor.fetchall()}
            return {
                "pending": stats.get("pending", 0),
                "approved": stats.get("approved", 0),
                "rejected": stats.get("rejected", 0),
            }
        finally:
            conn.close()


def register_memory_bridge_v2_tools(
    server: Union["Server", "FastMCP", Any],
    store: HierarchicalMemoryStore,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Register Memory Bridge v2.0 MCP tools on the server.

    Returns dict with initialized components for external access.
    """
    # Initialize components
    project_root = project_root or Path.cwd()

    embedding_service = EmbeddingService()
    router = SemanticRouter(store=store, embedding_service=embedding_service)
    extractor = AutoExtractionEngine(project_root=project_root)
    ttl_manager = TTLManager(store=store, project_root=project_root)
    causal_tracker = CausalChainTracker(
        db_path=store.db_path.parent / "causal_chains.db"
    )
    cold_start = ColdStartOptimizer(store=store, project_root=project_root)

    # v2.1 Auto-Mode components
    orchestrator = DiscoveryOrchestrator(
        store=store,
        cold_start=cold_start,
        project_root=project_root,
    )
    context_builder = EnterpriseContextBuilder(
        store=store,
        router=router,
        causal_tracker=causal_tracker,
        orchestrator=orchestrator,
    )

    # Store components for external access
    components = {
        "store": store,
        "router": router,
        "extractor": extractor,
        "ttl_manager": ttl_manager,
        "causal_tracker": causal_tracker,
        "cold_start": cold_start,
        "orchestrator": orchestrator,
        "context_builder": context_builder,
    }

    @server.tool(
        name="rlm_discover_project",
        description="Smart cold start discovery for new projects. "
        "Detects project type, seeds template facts, discovers domains.",
    )
    async def rlm_discover_project(
        project_root: Optional[str] = None,
        task_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform smart project discovery."""
        try:
            if project_root:
                root = Path(project_root)
            else:
                root = cold_start.project_root
            result = cold_start.discover_project(
                root=root,
                task_hint=task_hint,
            )

            return {
                "status": "success",
                "project_type": result.project_info.project_type.value,
                "project_name": result.project_info.name,
                "framework": result.project_info.framework,
                "facts_created": result.facts_created,
                "discovery_tokens": result.discovery_tokens,
                "suggested_domains": result.suggested_domains,
                "loc_estimate": result.project_info.loc_estimate,
                "file_count": result.project_info.file_count,
                "warnings": result.warnings,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_route_context",
        description="Semantic routing to get only relevant facts for a query. "
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

            # Format for injection
            formatted = router.format_context_for_injection(result)

            return {
                "status": "success",
                "facts_count": len(result.facts),
                "total_tokens": result.total_tokens,
                "routing_confidence": result.routing_confidence,
                "routing_explanation": result.routing_explanation,
                "domains_loaded": result.domains_loaded,
                "fallback_used": result.fallback_used,
                "context": formatted,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_extract_facts",
        description="Auto-extract facts from git diff or file changes. "
        "Returns candidates for approval.",
    )
    async def rlm_extract_facts(
        source: str = "git_diff",  # git_diff | staged | file
        file_path: Optional[str] = None,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """Extract facts from code changes."""
        try:
            if source == "file" and file_path:
                path = Path(file_path)
                if path.exists():
                    content = path.read_text(
                        encoding="utf-8",
                        errors="ignore",
                    )
                    result = extractor.extract_from_file(
                        path,
                        new_content=content,
                    )
                else:
                    return {
                        "status": "error",
                        "message": f"File not found: {file_path}",
                    }
            else:
                staged_only = source == "staged"
                result = extractor.extract_from_git_diff(
                    staged_only=staged_only,
                )

            # Auto-approve high-confidence candidates
            if auto_approve:
                for candidate in result.candidates:
                    if candidate.confidence >= 0.8:
                        candidate.approved = True
                        candidate.requires_approval = False
                        # Add to store
                        store.add_fact(
                            content=candidate.content,
                            level=candidate.suggested_level,
                            domain=candidate.suggested_domain,
                            source=candidate.source,
                            confidence=candidate.confidence,
                        )

            return {
                "status": "success",
                "candidates": [c.to_dict() for c in result.candidates],
                "auto_approved": result.auto_approved,
                "pending_approval": result.pending_approval,
                "total_changes": result.total_changes,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_approve_fact",
        description="Approve and store an extracted fact candidate.",
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
        level: int = 0,  # 0=L0_PROJECT, 1=L1_DOMAIN, 2=L2_MODULE, 3=L3_CODE
        domain: Optional[str] = None,
        module: Optional[str] = None,
        code_ref: Optional[str] = None,
        parent_id: Optional[str] = None,
        ttl_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a fact with full hierarchy support."""
        try:
            from .v2.hierarchical import TTLConfig, TTLAction

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
        name="rlm_get_causal_chain",
        description="Query reasoning history for a decision. "
        "Returns full causal chain with reasons and consequences.",
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
                    "message": f"No decision found matching: {query}",
                }

            # Generate visualization
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
        description="Record a decision with full causal context: "
        "reasons, consequences, constraints, alternatives.",
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

    @server.tool(
        name="rlm_set_ttl",
        description="Set TTL (Time-To-Live) configuration for a fact.",
    )
    async def rlm_set_ttl(
        fact_id: str,
        ttl_days: int,
        refresh_trigger: Optional[str] = None,
        on_expire: str = "mark_stale",  # mark_stale | archive | delete
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
        description="Get facts that have expired or need review.",
    )
    async def rlm_get_stale_facts(
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        """Get stale/expired facts."""
        try:
            # Process any newly expired facts first
            report = ttl_manager.process_expired()

            # Get stale facts
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
                        "created_at": f.created_at.isoformat(),
                    }
                    for f in stale_facts[:20]
                ],
                "ttl_report": report.to_dict(),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_index_embeddings",
        description="Generate embeddings for all facts without embeddings. "
        "Required for semantic routing.",
    )
    async def rlm_index_embeddings() -> Dict[str, Any]:
        """Index all facts with embeddings."""
        try:
            indexed = router.index_all_facts()

            return {
                "status": "success",
                "indexed_count": indexed,
                "message": f"Indexed {indexed} facts with embeddings",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_get_hierarchy_stats",
        description="Get statistics about the hierarchical memory store.",
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
        description="List all discovered domains in the memory store.",
    )
    async def rlm_list_domains() -> Dict[str, Any]:
        """List all domains."""
        try:
            domains = store.get_domains()

            # Get fact counts per domain
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
        description="Refresh TTL for a fact, resetting its expiration timer.",
    )
    async def rlm_refresh_fact(
        fact_id: str,
    ) -> Dict[str, Any]:
        """Refresh TTL for a fact."""
        try:
            success = ttl_manager.refresh_ttl(fact_id)
            return {
                "status": "success" if success else "error",
                "fact_id": fact_id,
                "message": "TTL refreshed" if success else "Fact not found",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_delete_fact",
        description="Delete a fact from the hierarchical memory store.",
    )
    async def rlm_delete_fact(
        fact_id: str,
    ) -> Dict[str, Any]:
        """Delete a fact."""
        try:
            success = store.delete_fact(fact_id)
            return {
                "status": "success" if success else "error",
                "fact_id": fact_id,
                "message": "Fact deleted" if success else "Fact not found",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ═══════════════════════════════════════════════════════════════════════
    # v2.1 Auto-Mode Tools
    # ═══════════════════════════════════════════════════════════════════════

    @server.tool(
        name="rlm_enterprise_context",
        description="One-call enterprise context with auto-discovery, "
        "semantic routing, and causal chains. Zero configuration. "
        "RECOMMENDED: Use this instead of individual tools.",
    )
    async def rlm_enterprise_context(
        query: str,
        max_tokens: int = 3000,
        mode: str = "auto",  # auto | discovery | route
        include_causal: bool = True,
        task_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enterprise context in one call.

        Modes:
        - auto: Auto-detect what's needed (recommended)
        - discovery: Force project discovery
        - route: Only route context (skip discovery check)
        """
        try:
            # Mode handling
            if mode == "discovery":
                orchestrator.force_discovery(task_hint=task_hint)
            elif mode == "auto":
                orchestrator.discover_or_restore(task_hint=task_hint)
            # mode == "route" skips discovery

            # Build context
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
                "discovery_performed": context.discovery_performed,
                "causal_included": bool(context.causal_summary),
                "suggestions": [s.to_dict() for s in context.suggestions],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @server.tool(
        name="rlm_install_git_hooks",
        description="Install git hooks for automatic fact extraction. "
        "Extracts facts from commits automatically.",
    )
    async def rlm_install_git_hooks(
        hook_type: str = "post-commit",
    ) -> Dict[str, Any]:
        """Install git hooks for auto-extraction."""
        try:
            git_dir = project_root / ".git"
            if not git_dir.exists():
                return {
                    "status": "error",
                    "message": "Not a git repository",
                }

            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(exist_ok=True)

            hook_path = hooks_dir / hook_type

            # Check if hook exists
            if hook_path.exists():
                content = hook_path.read_text()
                if "rlm_toolkit" in content:
                    return {
                        "status": "success",
                        "message": "Hook already installed",
                        "hook_path": str(hook_path),
                    }
                # Append to existing hook
                hook_script = "\n# Memory Bridge Auto-Extract\n"
            else:
                hook_script = "#!/bin/sh\n# Memory Bridge Auto-Extract\n"

            hook_script += (
                'python -c "'
                "from rlm_toolkit.memory_bridge.v2.extractor import "
                "AutoExtractionEngine; "
                "e = AutoExtractionEngine(); "
                "r = e.extract_from_git_diff(); "
                f"print(f'Extracted {{len(r.candidates)}} facts')"
                '" 2>/dev/null || true\n'
            )

            if hook_path.exists():
                with open(hook_path, "a") as f:
                    f.write(hook_script)
            else:
                hook_path.write_text(hook_script)

            # Make executable (Unix)
            try:
                import stat

                mode = hook_path.stat().st_mode
                hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP)
            except Exception:
                pass  # Windows doesn't need this

            return {
                "status": "success",
                "message": f"Installed {hook_type} hook",
                "hook_path": str(hook_path),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 18: Health Check (Observability)
    # =========================================================================
    @server.tool(
        name="rlm_health_check",
        description="Health check for Memory Bridge. Returns component "
        "status, metrics, and system info.",
    )
    async def rlm_health_check() -> Dict[str, Any]:
        """Perform health check on all Memory Bridge components."""
        from datetime import datetime

        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {},
        }

        # Check store
        try:
            stats = store.get_stats()
            health["components"]["store"] = {
                "status": "healthy",
                "facts_count": stats.get("total_facts", 0),
                "domains": stats.get("domains", 0),
            }
        except Exception as e:
            health["components"]["store"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        # Check router
        try:
            health["components"]["router"] = {
                "status": "healthy",
                "embeddings_enabled": router.embeddings_enabled,
            }
        except Exception as e:
            health["components"]["router"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        # Check causal tracker
        try:
            causal_stats = causal_tracker.get_stats()
            health["components"]["causal"] = {
                "status": "healthy",
                "decisions": causal_stats.get("total_decisions", 0),
            }
        except Exception as e:
            health["components"]["causal"] = {
                "status": "unhealthy",
                "error": str(e),
            }
            health["status"] = "degraded"

        # Check orchestrator
        try:
            health["components"]["orchestrator"] = {
                "status": "healthy",
                "project_root": str(orchestrator.project_root),
            }
        except Exception as e:
            health["components"]["orchestrator"] = {
                "status": "unhealthy",
                "error": str(e),
            }
        # Add L0 context for auto-injection (v2.1 fix)
        health["l0_context"] = store.get_l0_context(max_tokens=500)

        return health

    # =========================================================================
    # Tool 19: Deep Discover (v2.2 — Enhanced Auto-Population)
    # =========================================================================
    @server.tool(
        name="rlm_discover_deep",
        description="Deep discovery using multiple extractors: "
        "code (README, docstrings), config (package.json, pyproject), "
        "git (conventional commits), conversation. "
        "Extracts 10x more facts than basic discover.",
    )
    async def rlm_discover_deep(
        extractors_list: Optional[List[str]] = None,
        auto_approve: bool = False,
        max_facts: int = 100,
    ) -> Dict[str, Any]:
        """
        Deep discovery with multiple extractors.

        Args:
            extractors_list: Which extractors to run
                           ["code", "config", "git", "conversation"]
            auto_approve: Auto-approve all facts (ignore confidence)
            max_facts: Maximum facts to return

        Returns:
            Discovery result with candidates and stats
        """
        try:
            # Import extractors (lazy to avoid circular imports)
            import sys
            from pathlib import Path as PathLib

            # Add extractors path - extractors are in rlm-toolkit/src/
            rlm_toolkit_root = PathLib(__file__).parent.parent.parent
            extractors_src = rlm_toolkit_root / "src"

            if extractors_src.exists():
                if str(extractors_src) not in sys.path:
                    sys.path.insert(0, str(extractors_src))

            try:
                from rlm_mcp_server.extractors import (
                    ExtractionOrchestrator,
                )
            except ImportError as import_err:
                # Fallback — extractors might not be installed yet
                return {
                    "status": "error",
                    "message": f"Extractors import failed: {import_err}. "
                    f"Path checked: {extractors_src}",
                }

            orchestrator_ext = ExtractionOrchestrator(project_root)
            result = await orchestrator_ext.discover_deep(
                extractors=extractors_list,
                auto_approve=auto_approve,
                max_facts=max_facts,
            )

            # Initialize pending store for low-confidence candidates
            from pathlib import Path as PathLib2
            import sys as sys2

            pending_db = PathLib2(project_root) / ".rlm" / "pending_candidates.db"
            pending_db.parent.mkdir(parents=True, exist_ok=True)

            # src is already in sys.path from mcpClient.ts
            # Just try the import directly
            pending_store = None
            try:
                from rlm_mcp_server.pending_store import (
                    PendingCandidatesStore,
                    PendingCandidate,
                )

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                pass  # Continue without pending store

            auto_approved_count = 0
            pending_count = 0

            for candidate in result.get("candidates", []):
                confidence = candidate.get("confidence", 0)

                if confidence > 0.9 or auto_approve:
                    # Auto-approve high confidence or when forced
                    store.add_fact(
                        content=candidate["content"],
                        level=MemoryLevel(candidate.get("level", 1)),
                        domain=candidate.get("domain"),
                        source=f"discover_deep:{candidate.get('source')}",
                        confidence=confidence,
                    )
                    auto_approved_count += 1

                elif confidence >= 0.5 and pending_store:
                    # Store in pending for user approval
                    import uuid

                    pending_store.add(
                        PendingCandidate(
                            id=str(uuid.uuid4()),
                            content=candidate["content"],
                            source=candidate.get("source", "unknown"),
                            confidence=confidence,
                            domain=candidate.get("domain"),
                            level=candidate.get("level", 1),
                            file_path=candidate.get("file_path"),
                            line_number=candidate.get("line_number"),
                        )
                    )
                    pending_count += 1
                # Below 0.5 confidence — dropped

            # Update result with counts
            result["auto_approved"] = auto_approved_count
            result["pending_review"] = pending_count

            return result

        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 20: Get Pending Candidates (v2.2 — Approval UI)
    # =========================================================================
    @server.tool(
        name="rlm_get_pending_candidates",
        description="Get pending fact candidates awaiting user approval. "
        "Returns candidates with confidence 0.5-0.8 for review.",
    )
    async def rlm_get_pending_candidates(
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get pending candidates for review."""
        try:
            from pathlib import Path as PathLib3

            pending_db = PathLib3(project_root) / ".rlm" / "pending_candidates.db"

            if not pending_db.exists():
                return {
                    "status": "success",
                    "candidates": [],
                    "count": 0,
                }

            try:
                from rlm_mcp_server.pending_store import PendingCandidatesStore

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {"status": "error", "message": "Pending store not found"}

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

    # =========================================================================
    # Tool 21: Approve Candidate (v2.2 — Approval UI)
    # =========================================================================
    @server.tool(
        name="rlm_approve_candidate",
        description="Approve a pending fact candidate and add it to facts store.",
    )
    async def rlm_approve_candidate(
        candidate_id: str,
    ) -> Dict[str, Any]:
        """Approve a pending candidate."""
        try:
            from pathlib import Path as PathLib4

            pending_db = PathLib4(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import PendingCandidatesStore

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {"status": "error", "message": "Pending store not found"}

            candidate = pending_store.approve(candidate_id)

            if not candidate:
                return {"status": "error", "message": "Candidate not found"}

            # Add to main facts store
            fact_id = store.add_fact(
                content=candidate.content,
                level=MemoryLevel(candidate.level),
                domain=candidate.domain,
                source=f"approved:{candidate.source}",
                confidence=1.0,  # User-approved = full confidence
            )

            return {
                "status": "success",
                "fact_id": fact_id,
                "content": candidate.content[:100],
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 22: Reject Candidate (v2.2 — Approval UI)
    # =========================================================================
    @server.tool(
        name="rlm_reject_candidate",
        description="Reject a pending fact candidate.",
    )
    async def rlm_reject_candidate(
        candidate_id: str,
    ) -> Dict[str, Any]:
        """Reject a pending candidate."""
        try:
            from pathlib import Path as PathLib5

            pending_db = PathLib5(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import PendingCandidatesStore

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {"status": "error", "message": "Pending store not found"}

            success = pending_store.reject(candidate_id)

            return {
                "status": "success" if success else "error",
                "message": "Candidate rejected" if success else "Not found",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 23: Approve All Candidates (v2.2 — Batch Approval)
    # =========================================================================
    @server.tool(
        name="rlm_approve_all_candidates",
        description="Approve all pending fact candidates at once.",
    )
    async def rlm_approve_all_candidates() -> Dict[str, Any]:
        """Approve all pending candidates."""
        try:
            from pathlib import Path as PathLib6

            pending_db = PathLib6(project_root) / ".rlm" / "pending_candidates.db"

            try:
                from rlm_mcp_server.pending_store import PendingCandidatesStore

                pending_store = PendingCandidatesStore(pending_db)
            except ImportError:
                return {"status": "error", "message": "Pending store not found"}

            candidates = pending_store.approve_all()

            # Add all to main facts store
            for candidate in candidates:
                store.add_fact(
                    content=candidate.content,
                    level=MemoryLevel(candidate.level),
                    domain=candidate.domain,
                    source=f"approved:{candidate.source}",
                    confidence=1.0,
                )

            return {
                "status": "success",
                "approved_count": len(candidates),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 24: Enforcement Check (v2.1 — TDD Iron Law)
    # =========================================================================
    @server.tool(
        name="rlm_check_enforcement",
        description="Check L0 enforcement rules before implementation. "
        "Returns warnings if TDD Iron Law or other L0 rules are violated. "
        "Call BEFORE writing implementation code.",
    )
    async def rlm_check_enforcement(
        task_description: str,
    ) -> Dict[str, Any]:
        """
        Check L0 enforcement rules before implementation.

        Args:
            task_description: What you're about to implement

        Returns:
            Warnings list if rules violated, empty if OK to proceed
        """
        try:
            warnings = store.check_before_implementation(task_description)

            if warnings:
                return {
                    "status": "blocked",
                    "warnings": warnings,
                    "message": "⚠️ STOP! Fix these issues before proceeding:",
                    "action_required": True,
                }
            else:
                return {
                    "status": "ok",
                    "warnings": [],
                    "message": "✅ No enforcement violations. Proceed.",
                    "action_required": False,
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 25: Extract from Conversation (v2.3 — SFS Detection)
    # =========================================================================
    @server.tool(
        name="rlm_extract_from_conversation",
        description="Extract facts from conversation text using SFS "
        "(Significant Factual Shifts) detection. "
        "Identifies decisions, implementations, fixes, discoveries.",
    )
    async def rlm_extract_from_conversation(
        text: str,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract facts from conversation text.

        Args:
            text: Conversation text to analyze
            auto_approve: Auto-approve high-confidence facts

        Returns:
            Extracted candidates with confidence scores
        """
        try:
            from .v2.extractor import ConversationExtractor

            extractor = ConversationExtractor()
            result = extractor.extract_from_text(text)

            # Auto-approve if requested
            if auto_approve:
                for candidate in result.candidates:
                    if not candidate.requires_approval:
                        store.add_fact(
                            content=candidate.content,
                            level=candidate.suggested_level,
                            domain=candidate.suggested_domain,
                            source="conversation_sfs",
                            confidence=candidate.confidence,
                        )

            return {
                "status": "success",
                "candidates": [c.to_dict() for c in result.candidates],
                "auto_approved": result.auto_approved,
                "pending_approval": result.pending_approval,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # =========================================================================
    # Tool 26: Consolidate Facts (v2.3 — Aggregation)
    # =========================================================================
    @server.tool(
        name="rlm_consolidate_facts",
        description="Consolidate granular facts into higher-level summaries. "
        "Aggregates L3→L2→L1 and deduplicates similar facts.",
    )
    async def rlm_consolidate_facts(
        min_facts: int = 5,
    ) -> Dict[str, Any]:
        """
        Run fact consolidation: L3→L2→L1 aggregation + dedup.

        Args:
            min_facts: Minimum facts in group to trigger consolidation

        Returns:
            Consolidation result with stats
        """
        try:
            from .v2.consolidator import FactConsolidator

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

    return components
