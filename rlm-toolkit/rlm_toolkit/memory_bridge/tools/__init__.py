"""
Memory Bridge v2.x MCP Tools — Domain Modules.

Decomposed from mcp_tools_v2.py monolith into focused modules:
- pending_store: Pending candidates SQLite store
- context_events: Anti-Amnesia context change tracking
- discovery: Project discovery + deep discovery + reindex
- routing: Semantic routing + auto-inject + enterprise context
- facts: Fact CRUD, extraction, approval, consolidation
- lifecycle: TTL management, stale facts, refresh, delete
- infra: Stats, domains, health, enforcement, git hooks, embeddings
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..v2.hierarchical import HierarchicalMemoryStore
from ..v2.router import SemanticRouter, EmbeddingService
from ..v2.extractor import AutoExtractionEngine
from ..v2.ttl import TTLManager
from ..v2.causal import CausalChainTracker
from ..v2.coldstart import ColdStartOptimizer
from ..v2.automode import DiscoveryOrchestrator, EnterpriseContextBuilder

from .pending_store import InlinePendingStore
from .context_events import ContextEventTracker


@dataclass
class ToolComponents:
    """Shared components injected into all ToolGroup classes."""

    store: HierarchicalMemoryStore
    router: SemanticRouter
    extractor: AutoExtractionEngine
    ttl_manager: TTLManager
    causal_tracker: CausalChainTracker
    cold_start: ColdStartOptimizer
    orchestrator: DiscoveryOrchestrator
    context_builder: EnterpriseContextBuilder
    events: ContextEventTracker
    pending: InlinePendingStore
    project_root: Path = field(default_factory=Path.cwd)

    def to_dict(self):
        """Legacy compat — returns dict for register_memory_bridge_v2_tools."""
        return {
            "store": self.store,
            "router": self.router,
            "extractor": self.extractor,
            "ttl_manager": self.ttl_manager,
            "causal_tracker": self.causal_tracker,
            "cold_start": self.cold_start,
            "orchestrator": self.orchestrator,
            "context_builder": self.context_builder,
        }


def init_components(
    store: HierarchicalMemoryStore,
    project_root: Optional[Path] = None,
    on_context_change: Optional[callable] = None,
) -> ToolComponents:
    """Initialize all components for MCP tool registration."""
    project_root = project_root or Path.cwd()

    embedding_service = EmbeddingService()
    router = SemanticRouter(store=store, embedding_service=embedding_service)
    extractor = AutoExtractionEngine(project_root=project_root)
    ttl_manager = TTLManager(store=store, project_root=project_root)
    causal_tracker = CausalChainTracker(
        db_path=store.db_path.parent / "causal_chains.db"
    )
    cold_start = ColdStartOptimizer(store=store, project_root=project_root)
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
    events = ContextEventTracker(
        db_path=store.db_path.parent / "context_events.db",
        on_context_change=on_context_change,
    )
    pending = InlinePendingStore(db_path=store.db_path.parent / "pending_candidates.db")

    return ToolComponents(
        store=store,
        router=router,
        extractor=extractor,
        ttl_manager=ttl_manager,
        causal_tracker=causal_tracker,
        cold_start=cold_start,
        orchestrator=orchestrator,
        context_builder=context_builder,
        events=events,
        pending=pending,
        project_root=project_root,
    )


__all__ = [
    "ToolComponents",
    "init_components",
    "InlinePendingStore",
    "ContextEventTracker",
]
