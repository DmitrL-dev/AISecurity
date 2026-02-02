"""
Unit tests for SwarmTransport.

TDD: These tests are written BEFORE implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestSwarmTransport:
    """Tests for SwarmTransport interface and mock implementation."""

    @pytest.mark.asyncio
    async def test_transport_connect(self):
        """Transport connects successfully."""
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        assert transport.is_connected

    @pytest.mark.asyncio
    async def test_transport_publish(self):
        """Transport publishes messages."""
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        await transport.publish("brain.swarm.test", b'{"test": true}')

        # Verify message was published
        messages = transport.get_published_messages("brain.swarm.test")
        assert len(messages) == 1
        assert messages[0] == b'{"test": true}'

    @pytest.mark.asyncio
    async def test_transport_subscribe(self):
        """Transport receives subscribed messages."""
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        received = []

        async def handler(msg):
            received.append(msg)

        await transport.subscribe("brain.swarm.test", handler)

        # Simulate message arrival
        await transport.simulate_message("brain.swarm.test", b'{"hello": "world"}')

        assert len(received) == 1
        assert received[0].data == b'{"hello": "world"}'

    @pytest.mark.asyncio
    async def test_transport_reconnect(self):
        """Transport reconnects after disconnection."""
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()
        assert transport.is_connected

        # Simulate disconnect
        await transport.disconnect()
        assert not transport.is_connected

        # Reconnect
        await transport.connect()
        assert transport.is_connected

    @pytest.mark.asyncio
    async def test_transport_close(self):
        """Transport closes cleanly."""
        from brain.swarm.transport import MockTransport

        transport = MockTransport()
        await transport.connect()

        await transport.close()

        assert not transport.is_connected


class TestNatsTransport:
    """Tests for NATS transport implementation (requires mocking)."""

    @pytest.mark.asyncio
    async def test_nats_connect_with_servers(self):
        """NATS transport connects to specified servers."""
        from brain.swarm.nats_transport import NatsTransport

        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nc = MagicMock()
            mock_nc.jetstream = MagicMock(return_value=MagicMock())
            mock_connect.return_value = mock_nc

            transport = NatsTransport(servers=["nats://localhost:4222"])
            await transport.connect()

            mock_connect.assert_called_once()
            assert transport.is_connected

    @pytest.mark.asyncio
    async def test_nats_publish(self):
        """NATS transport publishes to subject."""
        from brain.swarm.nats_transport import NatsTransport

        with patch("nats.connect", new_callable=AsyncMock) as mock_connect:
            mock_nc = AsyncMock()
            mock_js = AsyncMock()
            mock_nc.jetstream = MagicMock(return_value=mock_js)
            mock_connect.return_value = mock_nc

            transport = NatsTransport(servers=["nats://localhost:4222"])
            await transport.connect()

            await transport.publish("brain.swarm.test", b'{"test": 1}')

            mock_js.publish.assert_called_once_with("brain.swarm.test", b'{"test": 1}')
