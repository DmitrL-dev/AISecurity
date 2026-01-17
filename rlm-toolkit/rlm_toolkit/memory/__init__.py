"""Memory module - persistent context across RLM runs."""

from rlm_toolkit.memory.base import Memory, MemoryEntry
from rlm_toolkit.memory.buffer import BufferMemory
from rlm_toolkit.memory.episodic import EpisodicMemory
from rlm_toolkit.memory.hierarchical import (
    HierarchicalMemory,
    HMEMConfig,
    MemoryLevel,
    MemoryEntry as HMEMEntry,
    create_hierarchical_memory,
)
from rlm_toolkit.memory.secure import (
    SecureHierarchicalMemory,
    SecurityPolicy,
    TrustLevel,
    AccessType,
    AccessLogEntry,
    create_secure_memory,
)

__all__ = [
    "Memory",
    "MemoryEntry",
    "BufferMemory",
    "EpisodicMemory",
    # H-MEM (Track B)
    "HierarchicalMemory",
    "HMEMConfig",
    "MemoryLevel",
    "HMEMEntry",
    "create_hierarchical_memory",
    # Secure H-MEM (Track B.4)
    "SecureHierarchicalMemory",
    "SecurityPolicy",
    "TrustLevel",
    "AccessType",
    "AccessLogEntry",
    "create_secure_memory",
]

