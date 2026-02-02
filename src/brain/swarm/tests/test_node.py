"""
Unit tests for SwarmNode.

TDD: These tests are written BEFORE implementation.
"""

import pytest
from datetime import datetime, timedelta
import json


class TestSwarmNode:
    """Tests for SwarmNode dataclass."""

    def test_swarm_node_creation(self):
        """Node ID is auto-generated on creation."""
        from brain.swarm.node import SwarmNode

        node = SwarmNode(hostname="brain-1.local", port=8000)

        assert node.node_id is not None
        assert len(node.node_id) == 12  # UUID prefix
        assert node.hostname == "brain-1.local"
        assert node.port == 8000

    def test_swarm_node_to_json(self):
        """Node serializes to JSON correctly."""
        from brain.swarm.node import SwarmNode

        node = SwarmNode(
            hostname="brain-1.local",
            port=8000,
            version="1.0.0",
        )

        data = node.to_json()
        parsed = json.loads(data)

        assert parsed["hostname"] == "brain-1.local"
        assert parsed["port"] == 8000
        assert parsed["version"] == "1.0.0"
        assert "node_id" in parsed

    def test_swarm_node_from_json(self):
        """Node deserializes from JSON correctly."""
        from brain.swarm.node import SwarmNode

        original = SwarmNode(hostname="brain-2.local", port=8001)
        json_str = original.to_json()

        restored = SwarmNode.from_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.hostname == original.hostname
        assert restored.port == original.port

    def test_node_status_transitions(self):
        """Node status transitions correctly."""
        from brain.swarm.node import SwarmNode, NodeStatus

        node = SwarmNode(hostname="brain-1.local", port=8000)

        # Default is online
        assert node.status == NodeStatus.ONLINE

        # Transition to degraded
        node.status = NodeStatus.DEGRADED
        assert node.status == NodeStatus.DEGRADED

        # Transition to offline
        node.status = NodeStatus.OFFLINE
        assert node.status == NodeStatus.OFFLINE


class TestNodeStatus:
    """Tests for NodeStatus enum."""

    def test_node_status_values(self):
        """NodeStatus has expected values."""
        from brain.swarm.node import NodeStatus

        assert NodeStatus.ONLINE.value == "online"
        assert NodeStatus.DEGRADED.value == "degraded"
        assert NodeStatus.OFFLINE.value == "offline"

    def test_node_status_from_string(self):
        """NodeStatus can be created from string."""
        from brain.swarm.node import NodeStatus

        assert NodeStatus("online") == NodeStatus.ONLINE
        assert NodeStatus("degraded") == NodeStatus.DEGRADED
        assert NodeStatus("offline") == NodeStatus.OFFLINE
