"""
SENTINEL Hybrid Search Agent.

Tree-based search for proactive defense combining:
- AIDE ML: Draft → Debug → Improve cycle with greedy search
- AI-Scientist: Multi-stage pipeline (explore → exploit → polish)

Usage:
    from src.brain.hybrid_search import SentinelHybridAgent, HybridConfig

    config = HybridConfig(num_drafts=5, debug_prob=0.3)
    agent = SentinelHybridAgent(config)
    best_attack = agent.run(max_steps=20)
"""

from .node import SearchNode
from .journal import SearchJournal
from .config import HybridConfig
from .search_policy import HybridSearchPolicy
from .hybrid_agent import SentinelHybridAgent

__all__ = [
    "SearchNode",
    "SearchJournal",
    "HybridConfig",
    "HybridSearchPolicy",
    "SentinelHybridAgent",
]

__version__ = "1.0.0"
