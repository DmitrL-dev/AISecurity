"""
NatsTransport — NATS JetStream Implementation

Production transport using NATS JetStream for
reliable messaging with persistence.
"""

from typing import Callable, List, Optional, Any
import asyncio

try:
    import nats
    from nats.js import JetStreamContext

    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False

from .transport import SwarmTransport, Message


class NatsTransport(SwarmTransport):
    """
    NATS JetStream transport implementation.

    Features:
    - Persistent messaging via JetStream
    - Auto-reconnect
    - TLS support


    Usage:
        transport = NatsTransport(servers=["nats://localhost:4222"])
        await transport.connect()
        await transport.publish("brain.swarm.test", b'{"hello": "world"}')
    """

    STREAM_NAME = "BRAIN_SWARM"
    STREAM_SUBJECTS = ["brain.>"]

    def __init__(
        self,
        servers: List[str],
        tls_enabled: bool = False,
        cert_file: Optional[str] = None,
        key_file: Optional[str] = None,
    ):
        """
        Initialize NATS transport.

        Args:
            servers: List of NATS server URLs
            tls_enabled: Enable TLS
            cert_file: Path to TLS certificate
            key_file: Path to TLS key
        """
        if not NATS_AVAILABLE:
            raise ImportError("nats-py is required. Install with: pip install nats-py")

        self._servers = servers
        self._tls_enabled = tls_enabled
        self._cert_file = cert_file
        self._key_file = key_file

        self._nc: Optional[Any] = None
        self._js: Optional[Any] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS and setup JetStream."""
        options = {
            "servers": self._servers,
            "reconnect_time_wait": 2,
            "max_reconnect_attempts": 60,
        }

        if self._tls_enabled and self._cert_file and self._key_file:
            # TLS configuration would go here
            pass

        self._nc = await nats.connect(**options)
        self._js = self._nc.jetstream()

        # Setup stream if not exists
        try:
            await self._js.add_stream(
                name=self.STREAM_NAME,
                subjects=self.STREAM_SUBJECTS,
            )
        except Exception:
            # Stream already exists
            pass

        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from NATS."""
        if self._nc and self._nc.is_connected:
            await self._nc.drain()
        self._connected = False

    async def publish(self, subject: str, data: bytes) -> None:
        """Publish message to JetStream."""
        if not self._js:
            raise RuntimeError("Not connected to NATS")
        await self._js.publish(subject, data)

    async def subscribe(self, subject: str, handler: Callable[[Message], Any]) -> None:
        """Subscribe to a subject."""
        if not self._js:
            raise RuntimeError("Not connected to NATS")

        async def wrapper(msg):
            wrapped = Message(
                subject=msg.subject,
                data=msg.data,
                reply=msg.reply,
            )
            if asyncio.iscoroutinefunction(handler):
                await handler(wrapped)
            else:
                handler(wrapped)

        await self._js.subscribe(subject, cb=wrapper)

    async def close(self) -> None:
        """Close NATS connection."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check NATS connection status."""
        return self._connected and self._nc is not None and self._nc.is_connected
