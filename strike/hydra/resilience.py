"""
SENTINEL Strike — HYDRA Resilience Manager

Handle head failures and adapt strategy.
"""

import asyncio
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import HydraCore
    from .heads.base import HydraHead


class ResilienceManager:
    """Handle head failures gracefully."""

    def __init__(self, hydra: "HydraCore"):
        self.hydra = hydra
        self.blocked_count = 0
        self.backoff_base = 1.0  # seconds
        self.max_backoff = 30.0
        self.aggression_level = 1.0  # 0.0 - 1.0

    @property
    def backoff_time(self) -> float:
        """Calculate exponential backoff with jitter."""
        backoff = min(self.backoff_base * (2**self.blocked_count), self.max_backoff)
        jitter = random.uniform(0.5, 1.5)
        return backoff * jitter

    async def on_head_blocked(self, head: "HydraHead", reason: str):
        """Handle blocked head."""
        self.blocked_count += 1

        # 1. Log incident (local only, no external)
        self._log_blocked(head.name, reason)

        # 2. Rotate identity if stealth module available
        if hasattr(self.hydra, "stealth"):
            await self.hydra.stealth.rotate_identity()

        # 3. Redistribute tasks to backup head
        backup = self._get_backup_head(head)
        if backup and hasattr(head, "pending_tasks"):
            await self._redistribute_tasks(head, backup)

        # 4. Reduce aggression
        self._reduce_aggression()

        # 5. Wait with backoff
        await asyncio.sleep(self.backoff_time)

    def _log_blocked(self, head_name: str, reason: str):
        """Log blocked head (local only)."""
        # In-memory only, no disk/network
        self.hydra.blocked_heads.add(head_name)

    def _get_backup_head(self, blocked_head: "HydraHead"):
        """Find backup head for blocked one."""
        backup_map = {
            "ReconHead": "CaptureHead",
            "CaptureHead": "ReconHead",
            "InjectHead": "AnalyzeHead",
            "AnalyzeHead": "InjectHead",
            "ExfilHead": "PersistHead",
            "PersistHead": "ExfilHead",
        }

        backup_name = backup_map.get(blocked_head.name)
        if backup_name:
            for head in self.hydra.heads:
                if head.name == backup_name:
                    return head
        return None

    async def _redistribute_tasks(self, from_head, to_head):
        """Move pending tasks from blocked head."""
        if hasattr(from_head, "pending_tasks"):
            tasks = from_head.pending_tasks
            if hasattr(to_head, "assume_tasks"):
                await to_head.assume_tasks(tasks)

    def _reduce_aggression(self):
        """Reduce attack aggression after blocks."""
        self.aggression_level = max(0.1, self.aggression_level * 0.8)

    def reset(self):
        """Reset resilience state."""
        self.blocked_count = 0
        self.aggression_level = 1.0
