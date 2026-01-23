# Memory Bridge Module
"""
External Model Memory Bridge — сохранение и восстановление когнитивного состояния агента.

Prior Art: Graphiti/Zep (arXiv:2501.13956) bi-temporal model
"""

from .models import (
    EntityType,
    HypothesisStatus,
    Hypothesis,
    Decision,
    Goal,
    Fact,
    FactCommunity,
    CognitiveStateVector,
)
from .storage import StateStorage, AuditAction, AuditLogEntry
from .manager import MemoryBridgeManager
from .mcp_tools import register_memory_bridge_tools

__all__ = [
    # Enums
    "EntityType",
    "HypothesisStatus",
    "AuditAction",
    # Data Models
    "Hypothesis",
    "Decision",
    "Goal",
    "Fact",
    "FactCommunity",
    "CognitiveStateVector",
    "AuditLogEntry",
    # Core Classes
    "StateStorage",
    "MemoryBridgeManager",
    # MCP Integration
    "register_memory_bridge_tools",
]

__version__ = "1.1.0"
