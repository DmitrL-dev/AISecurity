"""
BRAIN Swarm — Distributed Multi-Node Architecture

Enables multiple BRAIN instances to:
- Discover and register with each other
- Share threat intelligence via federated learning
- Maintain health status via heartbeat
- Sync configuration across the cluster

Transport: NATS JetStream
"""

from .node import SwarmNode, NodeStatus
from .transport import SwarmTransport, MockTransport
from .discovery import SwarmDiscovery
from .sync import SwarmSync
from .manager import SwarmManager, get_swarm_manager, init_swarm_manager

__all__ = [
    "SwarmNode",
    "NodeStatus",
    "SwarmTransport",
    "MockTransport",
    "SwarmDiscovery",
    "SwarmSync",
    "SwarmManager",
    "get_swarm_manager",
    "init_swarm_manager",
]
