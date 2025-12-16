"""
SENTINEL SDK Core — Cross-Platform Client Library

Core SDK for integrating SENTINEL into applications.

Features:
- Simple API for prompt analysis
- Async/sync support
- Caching
- Offline mode with signatures

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import hashlib
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger("SENTINEL.SDK")


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class SDKConfig:
    """SDK configuration."""

    api_key: str
    base_url: str = "https://api.sentinel.security"
    timeout_seconds: float = 30.0
    retry_count: int = 3
    cache_ttl_seconds: int = 300
    offline_mode: bool = False
    log_level: str = "WARNING"


# ============================================================================
# Result Types
# ============================================================================


class RiskLevel(Enum):
    """Risk level classification."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnalysisResult:
    """Result of prompt analysis."""

    is_safe: bool
    risk_score: float
    risk_level: RiskLevel
    threats: List[str]
    blocked: bool
    latency_ms: float
    cached: bool = False
    analysis_id: str = ""

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "threats": self.threats,
            "blocked": self.blocked,
            "latency_ms": self.latency_ms,
            "analysis_id": self.analysis_id,
        }


@dataclass
class BatchResult:
    """Result of batch analysis."""

    results: List[AnalysisResult]
    total: int
    blocked_count: int
    avg_risk: float
    latency_ms: float


# ============================================================================
# Cache
# ============================================================================


class ResultCache:
    """Simple in-memory cache for results."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache: Dict[str, tuple] = {}  # hash -> (result, timestamp)

    def get(self, prompt: str) -> Optional[AnalysisResult]:
        """Get cached result."""
        key = self._hash(prompt)
        if key in self._cache:
            result, timestamp = self._cache[key]
            if datetime.utcnow() - timestamp < timedelta(seconds=self.ttl):
                result.cached = True
                return result
            else:
                del self._cache[key]
        return None

    def set(self, prompt: str, result: AnalysisResult) -> None:
        """Cache result."""
        key = self._hash(prompt)
        self._cache[key] = (result, datetime.utcnow())

        # Cleanup old entries
        self._cleanup()

    def _hash(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()

    def _cleanup(self, max_size: int = 1000):
        """Remove old entries if cache too large."""
        if len(self._cache) > max_size:
            now = datetime.utcnow()
            expired = [
                k for k, (_, ts) in self._cache.items()
                if now - ts > timedelta(seconds=self.ttl)
            ]
            for k in expired:
                del self._cache[k]


# ============================================================================
# Offline Signatures
# ============================================================================


class OfflineDetector:
    """Simple offline detection using signatures."""

    # Basic signatures for offline mode
    SIGNATURES = [
        ("ignore previous", 80, "jailbreak"),
        ("ignore instructions", 80, "jailbreak"),
        ("pretend you are", 60, "role_play"),
        ("act as", 40, "role_play"),
        ("system prompt", 70, "prompt_leak"),
        ("reveal instructions", 75, "prompt_leak"),
        ("password", 50, "sensitive"),
        ("api_key", 60, "sensitive"),
        ("sudo", 70, "privilege"),
        ("admin mode", 70, "privilege"),
    ]

    def analyze(self, prompt: str) -> AnalysisResult:
        """Offline analysis using signatures."""
        prompt_lower = prompt.lower()
        threats = []
        max_score = 0

        for pattern, score, threat_type in self.SIGNATURES:
            if pattern in prompt_lower:
                threats.append(threat_type)
                max_score = max(max_score, score)

        risk_level = self._score_to_level(max_score)

        return AnalysisResult(
            is_safe=max_score < 50,
            risk_score=float(max_score),
            risk_level=risk_level,
            threats=threats[:5],
            blocked=max_score >= 70,
            latency_ms=0.1,
            analysis_id="offline",
        )

    def _score_to_level(self, score: float) -> RiskLevel:
        if score < 25:
            return RiskLevel.SAFE
        elif score < 50:
            return RiskLevel.LOW
        elif score < 70:
            return RiskLevel.MEDIUM
        elif score < 85:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


# ============================================================================
# Main SDK Client
# ============================================================================


class SentinelClient:
    """
    SENTINEL SDK Client.

    Main entry point for integrating SENTINEL.

    Usage:
        client = SentinelClient(api_key="sk_sentinel_xxx")
        result = await client.analyze("Your prompt here")

        if result.blocked:
            print("Prompt blocked!")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.sentinel.security",
        **kwargs,
    ):
        """
        Initialize SENTINEL client.

        Args:
            api_key: Your SENTINEL API key
            base_url: API endpoint (default: production)
            **kwargs: Additional config options
        """
        self.config = SDKConfig(
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )

        self._cache = ResultCache(self.config.cache_ttl_seconds)
        self._offline = OfflineDetector()

        self._stats = {
            "requests": 0,
            "cache_hits": 0,
            "failures": 0,
        }

        logger.info(
            f"SENTINEL SDK initialized (offline={self.config.offline_mode})")

    async def analyze(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> AnalysisResult:
        """
        Analyze a prompt for security threats.

        Args:
            prompt: The prompt to analyze
            context: Optional context (user_id, etc)
            use_cache: Whether to use cached results

        Returns:
            AnalysisResult with risk assessment
        """
        self._stats["requests"] += 1

        # Check cache
        if use_cache:
            cached = self._cache.get(prompt)
            if cached:
                self._stats["cache_hits"] += 1
                return cached

        # Offline mode
        if self.config.offline_mode:
            result = self._offline.analyze(prompt)
            self._cache.set(prompt, result)
            return result

        # Online analysis
        try:
            result = await self._call_api(prompt, context)
            self._cache.set(prompt, result)
            return result

        except Exception as e:
            logger.error(f"API call failed: {e}")
            self._stats["failures"] += 1

            # Fallback to offline
            return self._offline.analyze(prompt)

    def analyze_sync(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """Synchronous version of analyze."""
        return asyncio.run(self.analyze(prompt, context))

    async def analyze_batch(
        self,
        prompts: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        """
        Analyze multiple prompts.

        Args:
            prompts: List of prompts
            context: Shared context

        Returns:
            BatchResult with all results
        """
        import time
        start = time.time()

        results = await asyncio.gather(*[
            self.analyze(p, context)
            for p in prompts
        ])

        total_time = (time.time() - start) * 1000

        blocked_count = sum(1 for r in results if r.blocked)
        avg_risk = sum(r.risk_score for r in results) / \
            len(results) if results else 0

        return BatchResult(
            results=results,
            total=len(results),
            blocked_count=blocked_count,
            avg_risk=round(avg_risk, 1),
            latency_ms=round(total_time, 1),
        )

    async def _call_api(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]],
    ) -> AnalysisResult:
        """Call SENTINEL API."""
        import time

        # Simulated API call (would use httpx in production)
        start = time.time()

        # In production, this would be:
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.config.base_url}/v1/analyze",
        #         headers={"Authorization": f"Bearer {self.config.api_key}"},
        #         json={"prompt": prompt, "context": context},
        #     )
        #     data = response.json()

        # For now, use offline detector
        result = self._offline.analyze(prompt)
        result.latency_ms = (time.time() - start) * 1000

        return result

    def is_safe(self, prompt: str) -> bool:
        """Quick check if prompt is safe (sync)."""
        result = self.analyze_sync(prompt)
        return result.is_safe

    def get_statistics(self) -> Dict[str, Any]:
        """Get SDK statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


def create_client(
    api_key: str,
    **kwargs,
) -> SentinelClient:
    """Create SENTINEL client."""
    return SentinelClient(api_key=api_key, **kwargs)
