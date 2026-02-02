"""
SwarmManager — Orchestrator

Manages the complete swarm lifecycle:
- Transport connection
- Node registration
- Discovery subscription
- Pattern synchronization
- Graceful shutdown
"""

from typing import Optional, List
import asyncio

from .node import SwarmNode, NodeStatus
from .transport import SwarmTransport
from .nats_transport import NatsTransport
from .discovery import SwarmDiscovery
from .sync import SwarmSync

# Import CollectiveImmunity
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.collective_immunity import CollectiveImmunity, get_collective_immunity


class SwarmManager:
    """
    Orchestrates all swarm components.

    Usage:
        manager = SwarmManager(
            hostname="brain-1.local",
            port=8000,
            nats_servers=["nats://localhost:4222"]
        )
        await manager.start()
        # ... application runs ...
        await manager.stop()
    """

    def __init__(
        self,
        hostname: str,
        port: int,
        nats_servers: Optional[List[str]] = None,
        transport: Optional[SwarmTransport] = None,
        collective: Optional[CollectiveImmunity] = None,
    ):
        """
        Initialize swarm manager.

        Args:
            hostname: This node's hostname
            port: This node's API port
            nats_servers: List of NATS server URLs
            transport: Optional custom transport (for testing)
            collective: Optional CollectiveImmunity instance
        """
        self._node = SwarmNode(hostname=hostname, port=port)

        # Use provided transport or create NATS transport
        if transport:
            self._transport = transport
        elif nats_servers:
            self._transport = NatsTransport(servers=nats_servers)
        else:
            raise ValueError("Either nats_servers or transport must be provided")

        # Use provided or singleton CollectiveImmunity
        self._collective = collective or get_collective_immunity()

        # Create components
        self._discovery = SwarmDiscovery(
            transport=self._transport,
            node=self._node,
        )
        self._sync = SwarmSync(
            transport=self._transport,
            collective=self._collective,
            node=self._node,
        )

        # Background tasks
        self._tasks: List[asyncio.Task] = []
        self._running = False

    @property
    def node(self) -> SwarmNode:
        """Get this node's identity."""
        return self._node

    @property
    def discovery(self) -> SwarmDiscovery:
        """Get discovery component."""
        return self._discovery

    @property
    def sync(self) -> SwarmSync:
        """Get sync component."""
        return self._sync

    async def start(self) -> None:
        """Start the swarm manager."""
        if self._running:
            return

        # Connect transport
        await self._transport.connect()

        # Subscribe to updates
        await self._discovery.subscribe_to_discovery()
        await self._sync.subscribe_to_patterns()

        # Register this node
        await self._discovery.register()

        # Start background tasks
        self._tasks.append(asyncio.create_task(self._discovery.start_heartbeat()))
        self._tasks.append(
            asyncio.create_task(self._sync.start_periodic_broadcast(interval=60))
        )
        self._tasks.append(asyncio.create_task(self._dead_node_checker()))

        self._running = True

    async def stop(self) -> None:
        """Stop the swarm manager gracefully."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        # Unregister and disconnect
        try:
            await self._discovery.unregister()
        except Exception:
            pass

        await self._transport.close()

    async def _dead_node_checker(self) -> None:
        """Periodically check for dead nodes."""
        while self._running:
            await asyncio.sleep(10)
            await self._discovery.check_dead_nodes()

    def get_known_nodes(self) -> List[SwarmNode]:
        """Get all known nodes."""
        return self._discovery.get_known_nodes()

    def get_online_nodes(self) -> List[SwarmNode]:
        """Get online nodes."""
        return self._discovery.get_online_nodes()

    def get_stats(self) -> dict:
        """Get swarm statistics."""
        return {
            "node": self._node.to_dict(),
            "discovery": self._discovery.get_stats(),
            "sync": self._sync.get_stats(),
            "running": self._running,
        }


# Singleton instance
_manager: Optional[SwarmManager] = None


def get_swarm_manager() -> Optional[SwarmManager]:
    """Get singleton swarm manager."""
    return _manager


async def init_swarm_manager(
    hostname: str,
    port: int,
    nats_servers: List[str],
) -> SwarmManager:
    """Initialize and start singleton swarm manager."""
    global _manager
    if _manager is None:
        _manager = SwarmManager(
            hostname=hostname,
            port=port,
            nats_servers=nats_servers,
        )
        await _manager.start()
    return _manager


async def shutdown_swarm_manager() -> None:
    """Shutdown singleton swarm manager."""
    global _manager
    if _manager:
        await _manager.stop()
        _manager = None
