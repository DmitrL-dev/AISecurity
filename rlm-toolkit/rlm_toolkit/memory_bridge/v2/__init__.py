"""
Memory Bridge v2.1: Enterprise Amnesia Elimination

This module provides hierarchical memory, semantic routing, auto-extraction,
TTL management, causal chains, smart cold start, and auto-mode for
enterprise-scale AI context persistence.

Components:
- HierarchicalMemoryStore: L0-L3 memory hierarchy
- SemanticRouter: Intelligent context routing
- AutoExtractionEngine: Automatic fact extraction
- TTLManager: Temporal fact management
- CausalChainTracker: Decision reasoning preservation
- ColdStartOptimizer: Smart project discovery
- DiscoveryOrchestrator: Auto-discovery decisions (v2.1)
- EnterpriseContextBuilder: One-call context builder (v2.1)

Usage:
    from rlm_toolkit.memory_bridge.v2 import (
        HierarchicalMemoryStore,
        SemanticRouter,
        MemoryLevel,
        EnterpriseContextBuilder,  # v2.1
    )
"""

__version__ = "2.1.0"
__author__ = "SENTINEL Team"

from .hierarchical import (
    MemoryLevel,
    HierarchicalFact,
    TTLConfig,
    TTLAction,
    HierarchicalMemoryStore,
)
from .router import SemanticRouter, RoutingResult
from .extractor import AutoExtractionEngine, CandidateFact
from .ttl import TTLManager, TTLDefaults
from .causal import CausalChainTracker, CausalNode, CausalEdge
from .coldstart import ColdStartOptimizer, ProjectType
from .automode import (
    DiscoveryOrchestrator,
    EnterpriseContextBuilder,
    EnterpriseContext,
    Suggestion,
)

__all__ = [
    # Version
    "__version__",
    # Hierarchical
    "MemoryLevel",
    "HierarchicalFact",
    "TTLConfig",
    "TTLAction",
    "HierarchicalMemoryStore",
    # Router
    "SemanticRouter",
    "RoutingResult",
    # Extractor
    "AutoExtractionEngine",
    "CandidateFact",
    # TTL
    "TTLManager",
    "TTLDefaults",
    # Causal
    "CausalChainTracker",
    "CausalNode",
    "CausalEdge",
    # Cold Start
    "ColdStartOptimizer",
    "ProjectType",
    # Auto-Mode (v2.1)
    "DiscoveryOrchestrator",
    "EnterpriseContextBuilder",
    "EnterpriseContext",
    "Suggestion",
]
