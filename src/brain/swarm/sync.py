"""
SwarmSync — Pattern Synchronization

Handles threat pattern synchronization across the swarm
using CollectiveImmunity's federation mechanism.
"""

from typing import Optional
import json

from .node import SwarmNode
from .transport import SwarmTransport

# Import CollectiveImmunity from core
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brain.core.collective_immunity import CollectiveImmunity


class SwarmSync:
    """
    Synchronizes threat patterns across the swarm.

    Uses CollectiveImmunity's federated learning mechanism
    to share threat patterns while preserving privacy.
    """

    SUBJECT_PATTERNS = "brain.threat.patterns"

    def __init__(
        self,
        transport: SwarmTransport,
        collective: CollectiveImmunity,
        node: Optional[SwarmNode] = None,
    ):
        """
        Initialize sync.

        Args:
            transport: Transport layer
            collective: CollectiveImmunity instance
            node: Optional node identity (for filtering own messages)
        """
        self._transport = transport
        self._collective = collective
        self._node = node
        self._deployment_id = collective.export_for_federation()["deployment_id"]

    async def subscribe_to_patterns(self) -> None:
        """Subscribe to pattern updates."""
        await self._transport.subscribe(self.SUBJECT_PATTERNS, self._on_patterns)

    async def _on_patterns(self, msg) -> None:
        """Handle incoming patterns."""
        await self.on_patterns_received(msg.data)

    async def on_patterns_received(self, data: bytes) -> None:
        """Process received pattern data."""
        try:
            payload = json.loads(data.decode())
        except json.JSONDecodeError:
            return

        # Ignore own patterns
        if payload.get("deployment_id") == self._deployment_id:
            return

        # Import patterns via CollectiveImmunity
        self._collective.import_federation_data(payload)

    async def broadcast_patterns(self) -> None:
        """Broadcast local patterns to the swarm."""
        data = self._collective.export_for_federation()
        await self._transport.publish(self.SUBJECT_PATTERNS, json.dumps(data).encode())

    async def start_periodic_broadcast(self, interval: float = 60.0) -> None:
        """Start periodic pattern broadcast."""
        import asyncio

        while True:
            await self.broadcast_patterns()
            await asyncio.sleep(interval)

    def get_stats(self) -> dict:
        """Get sync statistics."""
        return {
            "deployment_id": self._deployment_id,
            "patterns": len(self._collective._patterns),
            "global_immunity": len(self._collective.get_global_immunity()),
            "privacy_status": self._collective.get_privacy_status(),
        }
