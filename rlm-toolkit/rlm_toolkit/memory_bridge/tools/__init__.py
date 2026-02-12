# tools/__init__.py — Orchestrator: register all domain tools
"""
Unified registration entrypoint for all Memory Bridge MCP tools.
Re-exports `register_memory_bridge_v2_tools` for backward compat.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from ..v2.hierarchical import HierarchicalMemoryStore
from ._common import ToolComponents

logger = logging.getLogger(__name__)


def register_memory_bridge_v2_tools(
    server: Union[Any, Any, Any],
    store: HierarchicalMemoryStore,
    project_root: Optional[Path] = None,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Unified registration for all Memory Bridge v2+v1 tools.

    Args:
        server: MCP server (FastMCP or Server)
        store: HierarchicalMemoryStore instance
        project_root: Project root path
        manager: Optional v1 MemoryBridgeManager

    Returns:
        Dict of component instances
    """
    from ..v2.router import SemanticRouter
    from ..v2.extractor import AutoExtractionEngine
    from ..v2.ttl import TTLManager
    from ..v2.causal import CausalChainTracker
    from ..v2.coldstart import ColdStartOptimizer
    from ..v2.automode import (
        DiscoveryOrchestrator,
        EnterpriseContextBuilder,
    )

    if project_root is None:
        project_root = Path(os.getenv("RLM_PROJECT_ROOT", os.getcwd()))

    router = SemanticRouter(store=store)
    extractor = AutoExtractionEngine(
        project_root=project_root,
    )
    ttl_manager = TTLManager(store=store)
    causal_tracker = CausalChainTracker(
        db_path=store.db_path.parent / "causal_chains.db",
    )
    cold_start = ColdStartOptimizer(
        store=store,
        project_root=project_root,
    )
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

    components: Dict[str, Any] = {
        "store": store,
        "router": router,
        "extractor": extractor,
        "ttl_manager": ttl_manager,
        "causal_tracker": causal_tracker,
        "cold_start": cold_start,
        "orchestrator": orchestrator,
        "context_builder": context_builder,
    }

    # Build shared ToolComponents
    tc = ToolComponents(
        store=store,
        router=router,
        extractor=extractor,
        ttl_manager=ttl_manager,
        causal_tracker=causal_tracker,
        cold_start=cold_start,
        orchestrator=orchestrator,
        context_builder=context_builder,
        project_root=project_root,
    )

    # Register all domain tool groups
    from .discovery import register_discovery_tools
    from .context import register_context_tools
    from .facts import register_facts_tools
    from .causal import register_causal_tools
    from .candidates import register_candidates_tools
    from .system import register_system_tools
    from .session import register_session_tools

    register_discovery_tools(server, tc)
    register_context_tools(server, tc)
    register_facts_tools(server, tc)
    register_causal_tools(server, tc)
    register_candidates_tools(server, tc)
    register_system_tools(server, tc)

    # V1 session tools (only if manager provided)
    if manager is not None:
        register_session_tools(server, manager)

    logger.info("Memory Bridge tools registered " "(modular v2+v1, 7 domains)")

    return components
