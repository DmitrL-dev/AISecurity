#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Python SDK

Простой программный интерфейс для запуска атак.

Usage:
    from sentinel_strike import Strike
    
    # Simple usage
    results = await Strike("https://api.target.com").attack()
    
    # Advanced usage
    strike = Strike(
        target="https://api.target.com",
        api_key="sk-...",
        stealth=True,
    )
    
    async for finding in strike.stream():
        print(f"Found: {finding}")
"""

from strike.orchestrator import StrikeOrchestrator, StrikeConfig, StrikeReport
import asyncio
from typing import Optional, AsyncIterator, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


@dataclass
class Finding:
    """Single vulnerability finding."""
    vector: str
    category: str
    severity: str
    response: str
    timestamp: str

    def __str__(self):
        return f"[{self.severity.upper()}] {self.vector} ({self.category})"


class Strike:
    """
    SENTINEL Strike Python SDK.

    Simple, Pythonic interface for LLM red teaming.

    Example:
        >>> strike = Strike("https://api.openai.com/v1/chat/completions")
        >>> results = await strike.attack(duration=30)
        >>> print(f"Found {len(results.vulnerabilities)} vulnerabilities")
    """

    def __init__(
        self,
        target: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        stealth: bool = True,
        duration: int = 60,
    ):
        """
        Initialize Strike client.

        Args:
            target: Target API URL (e.g., https://api.openai.com/v1/chat/completions)
            api_key: API key for authentication
            model: Target model name (e.g., gpt-4)
            stealth: Enable stealth mode (VPN rotation, fingerprint masking)
            duration: Default attack duration in minutes
        """
        self.target = target
        self.api_key = api_key
        self.model = model
        self.stealth = stealth
        self.duration = duration

        self._orchestrator: Optional[StrikeOrchestrator] = None
        self._findings: List[Finding] = []

    def _create_config(self, **overrides) -> StrikeConfig:
        """Create orchestrator config."""
        return StrikeConfig(
            target_url=self.target,
            target_api_key=self.api_key,
            target_model=self.model,
            stealth_enabled=self.stealth,
            duration_minutes=overrides.get("duration", self.duration),
            **{k: v for k, v in overrides.items() if k != "duration"}
        )

    async def attack(
        self,
        duration: Optional[int] = None,
        max_iterations: int = 1000,
    ) -> StrikeReport:
        """
        Run attack and return full report.

        Args:
            duration: Attack duration in minutes (overrides default)
            max_iterations: Maximum number of attack iterations

        Returns:
            StrikeReport with all findings
        """
        config = self._create_config(
            duration=duration or self.duration,
            max_iterations=max_iterations,
        )

        self._orchestrator = StrikeOrchestrator(config)
        return await self._orchestrator.run()

    async def stream(
        self,
        duration: Optional[int] = None,
    ) -> AsyncIterator[Finding]:
        """
        Stream findings as they are discovered.

        Args:
            duration: Attack duration in minutes

        Yields:
            Finding objects as discovered
        """
        config = self._create_config(duration=duration or self.duration)
        self._orchestrator = StrikeOrchestrator(config)

        # Start attack in background
        task = asyncio.create_task(self._orchestrator.run())

        last_count = 0
        while not task.done():
            await asyncio.sleep(1)

            # Check for new findings
            current_count = len(self._orchestrator.results)
            if current_count > last_count:
                for result in self._orchestrator.results[last_count:]:
                    if result.success:
                        yield Finding(
                            vector=result.vector_name,
                            category="unknown",
                            severity="high",
                            response=result.response[:500],
                            timestamp=str(result),
                        )
                last_count = current_count

        # Final results
        await task

    async def quick_scan(self, vectors: int = 10) -> List[Finding]:
        """
        Quick scan with limited vectors.

        Args:
            vectors: Number of vectors to try

        Returns:
            List of findings
        """
        config = self._create_config(
            duration=5,
            max_iterations=vectors,
        )

        self._orchestrator = StrikeOrchestrator(config)
        report = await self._orchestrator.run()

        return [
            Finding(
                vector=v.get("vector", "unknown"),
                category=v.get("category", "unknown"),
                severity=v.get("severity", "medium"),
                response=v.get("response", "")[:500],
                timestamp=v.get("timestamp", ""),
            )
            for v in report.vulnerabilities
        ]

    def pause(self):
        """Pause attack."""
        if self._orchestrator:
            self._orchestrator.pause()

    def resume(self):
        """Resume attack."""
        if self._orchestrator:
            self._orchestrator.resume()

    def stop(self):
        """Stop attack."""
        if self._orchestrator:
            self._orchestrator.stop()

    @property
    def status(self) -> Dict[str, Any]:
        """Get current attack status."""
        if self._orchestrator:
            return self._orchestrator.get_status()
        return {"state": "idle"}

    @property
    def findings(self) -> List[Finding]:
        """Get current findings."""
        return self._findings


# Convenience functions

async def attack(target: str, **kwargs) -> StrikeReport:
    """
    Quick attack function.

    Example:
        >>> from sentinel_strike import attack
        >>> results = await attack("https://api.target.com", duration=30)
    """
    return await Strike(target, **kwargs).attack()


async def quick_scan(target: str, vectors: int = 10) -> List[Finding]:
    """
    Quick scan function.

    Example:
        >>> from sentinel_strike import quick_scan
        >>> findings = await quick_scan("https://api.target.com")
    """
    return await Strike(target).quick_scan(vectors)


# CLI entry point for SDK
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SENTINEL Strike SDK")
    parser.add_argument("target", help="Target API URL")
    parser.add_argument("--duration", "-d", type=int, default=60)
    parser.add_argument("--no-stealth", action="store_true")

    args = parser.parse_args()

    async def main():
        strike = Strike(args.target, stealth=not args.no_stealth)
        report = await strike.attack(duration=args.duration)

        print("\n🎯 Attack completed!")
        print(f"   Vulnerabilities: {report.successful_attacks}")
        print(f"   Success rate: {report.success_rate:.1%}")

    asyncio.run(main())
