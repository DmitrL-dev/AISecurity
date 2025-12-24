"""
SENTINEL Strike — HYDRA Message Bus

Inter-head communication system.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict
from typing import Callable, Any
from enum import Enum


class EventType(str, Enum):
    """Event types for inter-head communication."""

    ENDPOINT_DISCOVERED = "endpoint_discovered"
    TRAFFIC_CAPTURED = "traffic_captured"
    VULN_DETECTED = "vuln_detected"
    HEAD_BLOCKED = "head_blocked"
    ATTACK_SUCCESS = "attack_success"
    ATTACK_FAILED = "attack_failed"
    EVIDENCE_COLLECTED = "evidence_collected"
    IDENTITY_ROTATED = "identity_rotated"


@dataclass
class HydraEvent:
    """Event for communication between heads."""

    type: EventType
    source: str  # Head name
    data: Any
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HydraMessageBus:
    """Async message bus for head communication."""

    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.subscribers: dict[EventType, list[Callable]] = defaultdict(list)
        self._running = False
        self._task = None

    def subscribe(self, event_type: EventType, handler: Callable):
        """Subscribe to event type."""
        self.subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Unsubscribe from event type."""
        if handler in self.subscribers[event_type]:
            self.subscribers[event_type].remove(handler)

    async def publish(self, event: HydraEvent):
        """Publish event to all subscribers."""
        await self.queue.put(event)

    async def start(self):
        """Start processing events."""
        self._running = True
        self._task = asyncio.create_task(self._process_events())

    async def stop(self):
        """Stop processing events."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_events(self):
        """Process events from queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _dispatch(self, event: HydraEvent):
        """Dispatch event to subscribers."""
        handlers = self.subscribers.get(event.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception:
                # Log but don't crash on handler errors
                pass
