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
from .tools import register_memory_bridge_v2_tools

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
    # MCP Integration (unified v1+v2)
    "register_memory_bridge_v2_tools",
]

__version__ = "2.1.0"
