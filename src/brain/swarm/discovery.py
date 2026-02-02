"""
SwarmDiscovery — Node Discovery and Heartbeat

Handles node registration, discovery, and health monitoring.
"""

from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional
import asyncio
import json

from .node import SwarmNode, NodeStatus
from .transport import SwarmTransport


class SwarmDiscovery:
    """
    Manages node discovery and health monitoring.

    Features:
    - Node registration on startup
    - Periodic heartbeat
    - Dead node detection
    - Known nodes tracking
    """

    # NATS subjects
    SUBJECT_REGISTER = "brain.swarm.register"
    SUBJECT_HEARTBEAT = "brain.swarm.heartbeat"
    SUBJECT_UNREGISTER = "brain.swarm.unregister"

    def __init__(
        self,
        transport: SwarmTransport,
        node: SwarmNode,
        heartbeat_interval: float = 5.0,
        dead_timeout: float = 30.0,
    ):
        """
        Initialize discovery.

        Args:
            transport: Transport layer
            node: This node's identity
            heartbeat_interval: Seconds between heartbeats
            dead_timeout: Seconds before marking node as dead
        """
        self._transport = transport
        self._node = node
        self._heartbeat_interval = heartbeat_interval
        self._dead_timeout = dead_timeout

        self._known_nodes: Dict[str, SwarmNode] = {}
        self._running = False

    async def register(self) -> None:
        """Publish registration message."""
        data = self._node.to_json().encode()
        await self._transport.publish(self.SUBJECT_REGISTER, data)

    async def unregister(self) -> None:
        """Publish unregistration message (graceful shutdown)."""
        data = json.dumps({"node_id": self._node.node_id}).encode()
        await self._transport.publish(self.SUBJECT_UNREGISTER, data)

    async def start_heartbeat(self, interval: Optional[float] = None) -> None:
        """Start heartbeat loop."""
        interval = interval or self._heartbeat_interval
        self._running = True

        while self._running:
            await self._send_heartbeat()
            await asyncio.sleep(interval)

    async def stop_heartbeat(self) -> None:
        """Stop heartbeat loop."""
        self._running = False

    async def _send_heartbeat(self) -> None:
        """Send a single heartbeat."""
        data = json.dumps(
            {
                "node_id": self._node.node_id,
                "hostname": self._node.hostname,
                "ts": datetime.now().isoformat(),
            }
        ).encode()
        await self._transport.publish(self.SUBJECT_HEARTBEAT, data)

    async def subscribe_to_discovery(self) -> None:
        """Subscribe to discovery subjects."""
        await self._transport.subscribe(self.SUBJECT_REGISTER, self._on_registration)
        await self._transport.subscribe(self.SUBJECT_HEARTBEAT, self._on_heartbeat)
        await self._transport.subscribe(self.SUBJECT_UNREGISTER, self._on_unregister)

    async def _on_registration(self, msg) -> None:
        """Handle registration message."""
        await self.handle_registration_message(msg.data.decode())

    async def handle_registration_message(self, json_str: str) -> None:
        """Process registration data."""
        data = json.loads(json_str)

        # Ignore self
        if data.get("node_id") == self._node.node_id:
            return

        # Add or update known node
        remote = SwarmNode.from_dict(data)
        remote.status = NodeStatus.ONLINE
        remote.last_heartbeat = datetime.now()
        self._known_nodes[remote.hostname] = remote

    async def _on_heartbeat(self, msg) -> None:
        """Handle heartbeat message."""
        data = json.loads(msg.data.decode())

        # Ignore self
        if data.get("node_id") == self._node.node_id:
            return

        hostname = data.get("hostname")
        if hostname and hostname in self._known_nodes:
            self._known_nodes[hostname].update_heartbeat()
            self._known_nodes[hostname].status = NodeStatus.ONLINE

    async def _on_unregister(self, msg) -> None:
        """Handle unregistration message."""
        data = json.loads(msg.data.decode())
        node_id = data.get("node_id")

        # Find and remove node
        for hostname, node in list(self._known_nodes.items()):
            if node.node_id == node_id:
                node.status = NodeStatus.OFFLINE
                break

    def register_remote_node(self, node: SwarmNode) -> None:
        """Manually register a remote node (for testing)."""
        node.last_heartbeat = datetime.now()
        self._known_nodes[node.hostname] = node

    async def check_dead_nodes(self) -> List[SwarmNode]:
        """Check for nodes that have timed out."""
        now = datetime.now()
        dead = []

        for node in self._known_nodes.values():
            if node.status == NodeStatus.OFFLINE:
                continue

            elapsed = (now - node.last_heartbeat).total_seconds()
            if elapsed > self._dead_timeout:
                node.status = NodeStatus.OFFLINE
                dead.append(node)

        return dead

    def get_known_nodes(self) -> List[SwarmNode]:
        """Get all known nodes (excluding self)."""
        return list(self._known_nodes.values())

    def get_node(self, hostname: str) -> Optional[SwarmNode]:
        """Get node by hostname."""
        return self._known_nodes.get(hostname)

    def get_online_nodes(self) -> List[SwarmNode]:
        """Get only online nodes."""
        return [n for n in self._known_nodes.values() if n.status == NodeStatus.ONLINE]

    def get_stats(self) -> Dict:
        """Get discovery statistics."""
        nodes = self.get_known_nodes()
        return {
            "known_nodes": len(nodes),
            "online": len([n for n in nodes if n.status == NodeStatus.ONLINE]),
            "offline": len([n for n in nodes if n.status == NodeStatus.OFFLINE]),
            "heartbeat_interval": self._heartbeat_interval,
            "dead_timeout": self._dead_timeout,
        }
