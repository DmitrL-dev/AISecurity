"""
SENTINEL Strike — HYDRA Head Base Class

Abstract base for all attack heads.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from ..core import Target
    from ..bus import HydraMessageBus


@dataclass
class HeadResult:
    """Result from head execution."""

    head_name: str
    success: bool
    started_at: datetime
    completed_at: Optional[datetime] = None
    data: Any = None
    vulnerabilities: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0


class HydraHead(ABC):
    """Abstract base for all Hydra heads."""

    name: str = "BaseHead"
    priority: int = 5  # 1-10 (10 = highest)
    stealth_level: int = 5  # 1-10 (10 = most stealthy)
    min_mode: int = 1  # Minimum OperationMode required

    def __init__(self, bus: Optional["HydraMessageBus"] = None):
        self.bus = bus
        self.pending_tasks: list = []
        self._blocked = False

    @abstractmethod
    async def execute(self, target: "Target") -> HeadResult:
        """
        Execute head's main function.

        Must be implemented by all heads.
        """
        pass

    async def fallback(self, target: "Target") -> HeadResult:
        """
        Alternative execution if primary blocked.

        Override in subclasses for head-specific fallback.
        """
        return HeadResult(
            head_name=self.name,
            success=False,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            errors=["No fallback available"],
        )

    def is_blocked(self) -> bool:
        """Check if head is blocked."""
        return self._blocked

    def block(self, reason: str = ""):
        """Mark head as blocked."""
        self._blocked = True

    def unblock(self):
        """Unblock head."""
        self._blocked = False

    async def assume_tasks(self, tasks: list):
        """Take over tasks from blocked head."""
        self.pending_tasks.extend(tasks)

    async def emit(self, event_type, data: Any):
        """Emit event to message bus."""
        if self.bus:
            from ..bus import HydraEvent

            event = HydraEvent(type=event_type, source=self.name, data=data)
            await self.bus.publish(event)

    def _create_result(self, success: bool = True) -> HeadResult:
        """Create base result object."""
        return HeadResult(
            head_name=self.name, success=success, started_at=datetime.now()
        )
