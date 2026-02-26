"""
SENTINEL Strike — HYDRA Core

Multi-head attack orchestrator.
"""

import asyncio
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


class OperationMode(IntEnum):
    """Operation modes with increasing aggression."""

    GHOST = 1  # Observer only
    PHANTOM = 2  # Soft attacker
    SHADOW = 3  # Full aggressor


@dataclass
class Target:
    """Target company information."""

    name: str
    domain: str
    inn: Optional[str] = None  # Company ID
    endpoints: list[str] = field(default_factory=list)
    discovered_llms: list[str] = field(default_factory=list)


@dataclass
class HydraReport:
    """Combined report from all heads."""

    target: Target
    mode: OperationMode
    started_at: datetime
    completed_at: Optional[datetime] = None
    heads_results: dict = field(default_factory=dict)
    blocked_heads: set = field(default_factory=set)
    vulnerabilities: list = field(default_factory=list)
    evidence: list = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = len(self.heads_results)
        if total == 0:
            return 0.0
        blocked = len(self.blocked_heads)
        return (total - blocked) / total


class HydraCore:
    """Multi-head attack orchestrator."""

    def __init__(self, mode: OperationMode = OperationMode.GHOST):
        self.mode = mode
        self.heads: list = []
        self.blocked_heads: set = set()
        self.bus = None  # HydraMessageBus
        self.resilience = None  # ResilienceManager

    def _init_heads(self):
        """Initialize heads based on mode."""
        from .heads.recon import ReconHead
        from .heads.capture import CaptureHead
        from .heads.analyze import AnalyzeHead
        from .heads.inject import InjectHead
        from .heads.exfil import ExfilHead
        from .heads.persist import PersistHead

        # Always active (Ghost+)
        self.heads = [
            ReconHead(self.bus),
            CaptureHead(self.bus),
            AnalyzeHead(self.bus),
        ]

        # Phantom mode adds injection
        if self.mode >= OperationMode.PHANTOM:
            self.heads.append(InjectHead(self.bus))

        # Shadow mode adds exfil and persistence
        if self.mode >= OperationMode.SHADOW:
            self.heads.extend(
                [
                    ExfilHead(self.bus),
                    PersistHead(self.bus),
                ]
            )

    async def attack(self, target: Target) -> HydraReport:
        """Execute multi-head attack on target."""
        from .bus import HydraMessageBus
        from .resilience import ResilienceManager

        # Initialize components
        self.bus = HydraMessageBus()
        self.resilience = ResilienceManager(self)
        self._init_heads()

        # Create report
        report = HydraReport(
            target=target,
            mode=self.mode,
            started_at=datetime.now(),
        )

        # Execute all heads in parallel
        tasks = [self._execute_head(head, target) for head in self.heads]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for head, result in zip(self.heads, results):
            if isinstance(result, Exception):
                report.blocked_heads.add(head.name)
                await self.resilience.on_head_blocked(head, str(result))
            else:
                report.heads_results[head.name] = result
                if hasattr(result, "vulnerabilities"):
                    report.vulnerabilities.extend(result.vulnerabilities)
                if hasattr(result, "evidence"):
                    report.evidence.extend(result.evidence)

        report.completed_at = datetime.now()
        return report

    async def _execute_head(self, head, target: Target):
        """Execute single head with error handling."""
        try:
            return await head.execute(target)
        except Exception:
            # Try fallback
            if hasattr(head, "fallback"):
                return await head.fallback(target)
            raise

    def get_active_heads(self) -> list:
        """Get list of non-blocked heads."""
        return [h for h in self.heads if h.name not in self.blocked_heads]
