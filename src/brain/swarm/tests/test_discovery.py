"""
Unit tests for SwarmDiscovery.

TDD: These tests are written BEFORE implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import asyncio
import json


class TestSwarmDiscovery:
    """Tests for SwarmDiscovery component."""

    @pytest.mark.asyncio
    async def test_register_node(self):
        """Discovery registers node on startup."""
        from brain.swarm.discovery import SwarmDiscovery
        from brain.swarm.node import SwarmNode
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        node = SwarmNode(hostname="brain-1.local", port=8000)
        discovery = SwarmDiscovery(transport=transport, node=node)

        await discovery.register()

        # Check registration message was published
        messages = transport.get_published_messages("brain.swarm.register")
        assert len(messages) == 1

        # Verify message content
        data = json.loads(messages[0].decode())
        assert data["hostname"] == "brain-1.local"
        assert data["port"] == 8000

    @pytest.mark.asyncio
    async def test_heartbeat_sent(self):
        """Discovery sends heartbeat at interval."""
        from brain.swarm.discovery import SwarmDiscovery
        from brain.swarm.node import SwarmNode
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        node = SwarmNode(hostname="brain-1.local", port=8000)
        discovery = SwarmDiscovery(transport=transport, node=node)

        # Start heartbeat in background (with very short interval for test)
        task = asyncio.create_task(discovery.start_heartbeat(interval=0.1))

        # Wait for a few heartbeats
        await asyncio.sleep(0.35)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Should have at least 3 heartbeats
        messages = transport.get_published_messages("brain.swarm.heartbeat")
        assert len(messages) >= 3

    @pytest.mark.asyncio
    async def test_node_timeout(self):
        """Discovery marks node as offline after timeout."""
        from brain.swarm.discovery import SwarmDiscovery
        from brain.swarm.node import SwarmNode, NodeStatus
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        node = SwarmNode(hostname="brain-1.local", port=8000)
        discovery = SwarmDiscovery(transport=transport, node=node, dead_timeout=0.2)

        # Add a remote node
        remote_node = SwarmNode(hostname="brain-2.local", port=8001)
        discovery.register_remote_node(remote_node)

        assert discovery.get_node("brain-2.local").status == NodeStatus.ONLINE

        # Wait for timeout
        await asyncio.sleep(0.3)
        await discovery.check_dead_nodes()

        # Remote node should be offline
        assert discovery.get_node("brain-2.local").status == NodeStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_known_nodes_update(self):
        """Discovery updates known nodes on registration message."""
        from brain.swarm.discovery import SwarmDiscovery
        from brain.swarm.node import SwarmNode
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        node = SwarmNode(hostname="brain-1.local", port=8000)
        discovery = SwarmDiscovery(transport=transport, node=node)

        # Simulate receiving registration from another node
        remote_data = {
            "node_id": "remote-node-1",
            "hostname": "brain-2.local",
            "port": 8001,
            "version": "1.0.0",
            "status": "online",
        }
        await transport.simulate_message(
            "brain.swarm.register", json.dumps(remote_data).encode()
        )

        # Trigger subscription handler
        await discovery.handle_registration_message(json.dumps(remote_data))

        # Should know about remote node
        known = discovery.get_known_nodes()
        assert len(known) == 1
        assert known[0].hostname == "brain-2.local"

    @pytest.mark.asyncio
    async def test_ignore_own_registration(self):
        """Discovery ignores own registration messages."""
        from brain.swarm.discovery import SwarmDiscovery
        from brain.swarm.node import SwarmNode
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        node = SwarmNode(hostname="brain-1.local", port=8000)
        discovery = SwarmDiscovery(transport=transport, node=node)

        # Simulate receiving own registration
        own_data = node.to_dict()
        await discovery.handle_registration_message(json.dumps(own_data))

        # Should NOT add self to known nodes
        known = discovery.get_known_nodes()
        assert len(known) == 0
