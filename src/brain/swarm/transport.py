"""
SwarmTransport — Abstract Transport Layer

Defines the interface for swarm communication.
Includes MockTransport for testing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
import asyncio


@dataclass
class Message:
    """Transport message wrapper."""

    subject: str
    data: bytes
    reply: Optional[str] = None


class SwarmTransport(ABC):
    """
    Abstract base class for swarm transport.

    Implementations must support pub/sub messaging.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the transport."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the transport."""
        pass

    @abstractmethod
    async def publish(self, subject: str, data: bytes) -> None:
        """Publish a message to a subject."""
        pass

    @abstractmethod
    async def subscribe(self, subject: str, handler: Callable[[Message], Any]) -> None:
        """Subscribe to a subject with a handler."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the transport connection."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        pass


class MockTransport(SwarmTransport):
    """
    Mock transport for testing.

    Stores published messages and allows simulating incoming messages.
    """

    def __init__(self):
        self._connected = False
        self._published: Dict[str, List[bytes]] = {}
        self._subscriptions: Dict[str, List[Callable]] = {}

    async def connect(self) -> None:
        """Connect to mock transport."""
        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from mock transport."""
        self._connected = False

    async def publish(self, subject: str, data: bytes) -> None:
        """Store published message."""
        if subject not in self._published:
            self._published[subject] = []
        self._published[subject].append(data)

    async def subscribe(self, subject: str, handler: Callable) -> None:
        """Register subscription handler."""
        if subject not in self._subscriptions:
            self._subscriptions[subject] = []
        self._subscriptions[subject].append(handler)

    async def close(self) -> None:
        """Close mock transport."""
        self._connected = False
        self._subscriptions.clear()

    @property
    def is_connected(self) -> bool:
        """Check connection status."""
        return self._connected

    def get_published_messages(self, subject: str) -> List[bytes]:
        """Get all messages published to a subject."""
        return self._published.get(subject, [])

    async def simulate_message(self, subject: str, data: bytes) -> None:
        """Simulate receiving a message from the network."""
        message = Message(subject=subject, data=data)
        handlers = self._subscriptions.get(subject, [])
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)

    def clear(self) -> None:
        """Clear all published messages."""
        self._published.clear()
