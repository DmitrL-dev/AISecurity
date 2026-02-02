"""
Unit tests for SwarmSync.

TDD: These tests are written BEFORE implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestSwarmSync:
    """Tests for SwarmSync component."""

    @pytest.mark.asyncio
    async def test_broadcast_patterns(self):
        """SwarmSync broadcasts threat patterns."""
        from brain.swarm.sync import SwarmSync
        from brain.swarm.transport import MockTransport
        from brain.core.collective_immunity import CollectiveImmunity

        transport = MockTransport()
        await transport.connect()

        collective = CollectiveImmunity()
        # Add some patterns to broadcast
        collective.contribute_pattern("jailbreak prompt", 0.9)
        collective.contribute_pattern("jailbreak prompt", 0.85)  # Second contributor
        collective.contribute_pattern("jailbreak prompt", 0.88)  # Third - promotion

        sync = SwarmSync(transport=transport, collective=collective)
        await sync.broadcast_patterns()

        # Verify patterns were published
        messages = transport.get_published_messages("brain.threat.patterns")
        assert len(messages) == 1

        data = json.loads(messages[0].decode())
        assert "global_patterns" in data
        assert len(data["global_patterns"]) >= 1  # Promoted pattern

    @pytest.mark.asyncio
    async def test_receive_patterns(self):
        """SwarmSync imports patterns from other nodes."""
        from brain.swarm.sync import SwarmSync
        from brain.swarm.transport import MockTransport
        from brain.core.collective_immunity import CollectiveImmunity

        transport = MockTransport()
        await transport.connect()

        collective = CollectiveImmunity()
        sync = SwarmSync(transport=transport, collective=collective)

        # Simulate receiving patterns from another node
        remote_data = {
            "deployment_id": "remote-node",
            "global_patterns": ["hash1234567890", "hash0987654321"],
            "pattern_count": 10,
            "privacy_epsilon": 1.0,
        }

        await sync.on_patterns_received(json.dumps(remote_data).encode())

        # Verify patterns were imported
        immunity = collective.get_global_immunity()
        assert "hash1234567890" in immunity
        assert "hash0987654321" in immunity

    @pytest.mark.asyncio
    async def test_ignore_own_patterns(self):
        """SwarmSync ignores patterns broadcast by self."""
        from brain.swarm.sync import SwarmSync
        from brain.swarm.node import SwarmNode
        from brain.swarm.transport import MockTransport
        from brain.core.collective_immunity import CollectiveImmunity

        transport = MockTransport()
        await transport.connect()

        collective = CollectiveImmunity()
        node = SwarmNode(hostname="brain-1.local", port=8000)
        sync = SwarmSync(transport=transport, collective=collective, node=node)

        # Simulate receiving own patterns
        own_data = {
            "deployment_id": collective.export_for_federation()["deployment_id"],
            "global_patterns": ["hash_should_not_import"],
            "pattern_count": 1,
            "privacy_epsilon": 1.0,
        }

        initial_count = len(collective.get_global_immunity())
        await sync.on_patterns_received(json.dumps(own_data).encode())

        # Should NOT import own patterns
        final_count = len(collective.get_global_immunity())
        assert final_count == initial_count

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """SwarmSync deduplicates already known patterns."""
        from brain.swarm.sync import SwarmSync
        from brain.swarm.transport import MockTransport
        from brain.core.collective_immunity import CollectiveImmunity

        transport = MockTransport()
        await transport.connect()

        collective = CollectiveImmunity()
        sync = SwarmSync(transport=transport, collective=collective)

        # Import same patterns twice
        remote_data = {
            "deployment_id": "remote-node",
            "global_patterns": ["hash123"],
            "pattern_count": 1,
            "privacy_epsilon": 1.0,
        }

        await sync.on_patterns_received(json.dumps(remote_data).encode())
        await sync.on_patterns_received(json.dumps(remote_data).encode())

        # Should only have one pattern
        immunity = collective.get_global_immunity()
        assert len([p for p in immunity if p == "hash123"]) == 1
