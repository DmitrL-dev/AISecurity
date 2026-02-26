"""
SENTINEL Strike — External Mode

Testing external/public-facing AI endpoints via API.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import httpx

from ..target import Target, TargetCapability, ModelType
from ..executor import AttackExecutor, AttackResult, AttackStatus
from ..config import ScanConfig


@dataclass
class ExternalScanResult:
    """Result of an external scan."""
    target_url: str
    scan_start: datetime
    scan_end: datetime
    model_detected: Optional[str] = None
    provider_detected: Optional[str] = None
    rate_limit_detected: Optional[int] = None
    attacks_run: int = 0
    attacks_successful: int = 0
    attacks_blocked: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    results: list[AttackResult] = field(default_factory=list)


class ExternalScanner:
    """
    External Mode Scanner

    Tests public-facing AI endpoints:
    - Cloud LLM APIs (OpenAI, Anthropic, Google)
    - Customer chatbots
    - AI-powered customer support
    - Public API gateways
    """

    def __init__(self, target: Target, config: Optional[ScanConfig] = None):
        self.target = target
        self.config = config or ScanConfig()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def probe_target(self) -> TargetCapability:
        """Probe target to detect capabilities and model type."""
        caps = await self.target.probe()

        # Additional external-specific probing
        caps = await self._detect_provider(caps)
        caps = await self._detect_rate_limits(caps)

        return caps

    async def _detect_provider(self, caps: TargetCapability) -> TargetCapability:
        """Detect cloud provider from response patterns."""
        try:
            response = await self.target.send([{"role": "user", "content": "Hi"}])
            response_str = str(response)

            # Provider detection heuristics
            if "gpt" in response_str.lower():
                caps.model_type = ModelType.OPENAI
            elif "claude" in response_str.lower():
                caps.model_type = ModelType.ANTHROPIC
            elif "gemini" in response_str.lower():
                caps.model_type = ModelType.GOOGLE
            elif "mistral" in response_str.lower():
                caps.model_type = ModelType.MISTRAL

        except Exception:
            pass

        return caps

    async def _detect_rate_limits(self, caps: TargetCapability) -> TargetCapability:
        """Detect rate limiting by making rapid requests."""
        rate_limited = False
        requests_before_limit = 0

        for i in range(10):
            try:
                response = await self.target.send([{"role": "user", "content": f"Test {i}"}])
                if "rate" in str(response).lower() or "limit" in str(response).lower():
                    rate_limited = True
                    requests_before_limit = i
                    break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    rate_limited = True
                    requests_before_limit = i
                    break
            except Exception:
                break

            await asyncio.sleep(0.1)

        if rate_limited:
            caps.rate_limit = requests_before_limit

        return caps

    async def run_scan(
        self,
        categories: Optional[list[str]] = None,
        attack_ids: Optional[list[str]] = None,
    ) -> ExternalScanResult:
        """Run external vulnerability scan."""
        scan_start = datetime.now()

        # Probe target first
        caps = await self.probe_target()

        # Run attacks
        executor = AttackExecutor(self.target, self.config)
        results = await executor.run_campaign(categories, attack_ids)

        scan_end = datetime.now()

        # Calculate statistics
        successful = [r for r in results if r.status == AttackStatus.SUCCESS]
        blocked = [r for r in results if r.status == AttackStatus.BLOCKED]

        return ExternalScanResult(
            target_url=self.target.url,
            scan_start=scan_start,
            scan_end=scan_end,
            model_detected=caps.model_name,
            provider_detected=caps.model_type.value if caps.model_type else None,
            rate_limit_detected=caps.rate_limit,
            attacks_run=len(results),
            attacks_successful=len(successful),
            attacks_blocked=len(blocked),
            critical_findings=sum(
                1 for r in successful if r.severity.value == "CRITICAL"),
            high_findings=sum(
                1 for r in successful if r.severity.value == "HIGH"),
            results=results,
        )


async def run_external_scan(
    url: str,
    api_key: Optional[str] = None,
    categories: Optional[list[str]] = None,
) -> ExternalScanResult:
    """Convenience function to run external scan."""
    target = Target(url=url, api_key=api_key, mode="external")

    async with ExternalScanner(target) as scanner:
        return await scanner.run_scan(categories=categories)
