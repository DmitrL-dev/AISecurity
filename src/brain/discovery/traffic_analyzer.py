"""
AI API Traffic Analyzer — SENTINEL AI Discovery

Analyzes network traffic for AI API communications:
- OpenAI, Anthropic, Google AI endpoints
- Request/response patterns
- Token usage estimation
- Data exfiltration detection

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("AITrafficAnalyzer")


# ============================================================================
# Data Classes
# ============================================================================


class TrafficDirection(Enum):
    """Direction of AI API traffic."""

    OUTBOUND = "outbound"  # To AI API
    INBOUND = "inbound"  # From AI API


class AIProvider(Enum):
    """Known AI API providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"
    HUGGINGFACE = "huggingface"
    COHERE = "cohere"
    MISTRAL = "mistral"
    UNKNOWN = "unknown"


@dataclass
class AIAPICall:
    """Single AI API call detected."""

    timestamp: datetime
    provider: AIProvider
    endpoint: str
    method: str
    request_size_bytes: int
    response_size_bytes: int
    latency_ms: float
    source_ip: str
    source_process: Optional[str] = None
    token_estimate: int = 0
    is_suspicious: bool = False
    flags: List[str] = field(default_factory=list)


@dataclass
class TrafficSummary:
    """Summary of AI API traffic."""

    total_calls: int = 0
    total_request_bytes: int = 0
    total_response_bytes: int = 0
    estimated_tokens: int = 0
    calls_by_provider: Dict[str, int] = field(default_factory=dict)
    suspicious_calls: int = 0
    time_range_minutes: float = 0.0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_request_mb": self.total_request_bytes / 1_000_000,
            "total_response_mb": self.total_response_bytes / 1_000_000,
            "estimated_tokens": self.estimated_tokens,
            "calls_by_provider": self.calls_by_provider,
            "suspicious_calls": self.suspicious_calls,
            "calls_per_minute": (
                self.total_calls / max(self.time_range_minutes, 1)
            ),
        }


# ============================================================================
# Endpoint Patterns
# ============================================================================


class AIEndpointPatterns:
    """Patterns for identifying AI API endpoints."""

    ENDPOINTS = {
        AIProvider.OPENAI: [
            r"api\.openai\.com",
            r".*\.openai\.azure\.com",
        ],
        AIProvider.ANTHROPIC: [
            r"api\.anthropic\.com",
        ],
        AIProvider.GOOGLE: [
            r"generativelanguage\.googleapis\.com",
            r"aiplatform\.googleapis\.com",
            r".*\.aiplatform\.googleusercontent\.com",
        ],
        AIProvider.AZURE: [
            r".*\.cognitiveservices\.azure\.com",
            r".*\.openai\.azure\.com",
        ],
        AIProvider.AWS: [
            r"bedrock.*\.amazonaws\.com",
            r"sagemaker.*\.amazonaws\.com",
        ],
        AIProvider.HUGGINGFACE: [
            r"api-inference\.huggingface\.co",
        ],
        AIProvider.COHERE: [
            r"api\.cohere\.ai",
        ],
        AIProvider.MISTRAL: [
            r"api\.mistral\.ai",
        ],
    }

    # API paths that indicate LLM usage
    LLM_PATHS = [
        r"/v1/chat/completions",
        r"/v1/completions",
        r"/v1/embeddings",
        r"/v1/messages",
        r"/generateContent",
        r"/streamGenerateContent",
        r"/predict",
        r"/invoke",
    ]

    # Suspicious patterns
    SUSPICIOUS = [
        r"\.txt$",  # Sending raw files
        r"\.csv$",  # Sending data files
        r"\.json.*bulk",  # Bulk data
        r"password",
        r"secret",
        r"api.?key",
    ]


# ============================================================================
# Main Analyzer
# ============================================================================


class AITrafficAnalyzer:
    """
    Analyzes network traffic for AI API communications.

    Features:
    - Real-time traffic monitoring
    - Provider identification
    - Token estimation
    - Anomaly detection
    - Usage reporting
    """

    # Approximate chars per token for estimation
    CHARS_PER_TOKEN = 4

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.patterns = AIEndpointPatterns()

        # Call history for analysis
        self._call_history: List[AIAPICall] = []
        self._max_history = config.get("max_history", 10000)

        # Rate limiting detection
        self._rate_windows: Dict[str, List[datetime]] = defaultdict(list)

        self._stats = {
            "packets_analyzed": 0,
            "ai_calls_detected": 0,
            "suspicious_detected": 0,
        }

        logger.info("AITrafficAnalyzer initialized")

    def analyze_connection(
        self,
        remote_host: str,
        remote_port: int,
        method: str = "POST",
        path: str = "/",
        request_size: int = 0,
        response_size: int = 0,
        latency_ms: float = 0.0,
        source_ip: str = "",
        source_process: Optional[str] = None,
    ) -> Optional[AIAPICall]:
        """
        Analyze a single network connection for AI API activity.

        Args:
            remote_host: Remote hostname or IP
            remote_port: Remote port
            method: HTTP method
            path: Request path
            request_size: Request body size in bytes
            response_size: Response body size in bytes
            latency_ms: Request latency
            source_ip: Source IP address
            source_process: Source process name

        Returns:
            AIAPICall if AI API detected, None otherwise
        """
        self._stats["packets_analyzed"] += 1

        # Identify provider
        provider = self._identify_provider(remote_host)
        if provider == AIProvider.UNKNOWN:
            return None

        # Check if it's an LLM-related path
        is_llm_path = any(
            re.search(pattern, path, re.IGNORECASE)
            for pattern in self.patterns.LLM_PATHS
        )

        if not is_llm_path and remote_port not in [443, 80]:
            return None

        # Create API call record
        call = AIAPICall(
            timestamp=datetime.now(),
            provider=provider,
            endpoint=f"{remote_host}{path}",
            method=method,
            request_size_bytes=request_size,
            response_size_bytes=response_size,
            latency_ms=latency_ms,
            source_ip=source_ip,
            source_process=source_process,
            token_estimate=self._estimate_tokens(request_size, response_size),
        )

        # Check for suspicious patterns
        self._check_suspicious(call, path)

        # Record call
        self._record_call(call)

        self._stats["ai_calls_detected"] += 1
        if call.is_suspicious:
            self._stats["suspicious_detected"] += 1

        return call

    def _identify_provider(self, host: str) -> AIProvider:
        """Identify AI provider from hostname."""
        host_lower = host.lower()

        for provider, patterns in self.patterns.ENDPOINTS.items():
            for pattern in patterns:
                if re.search(pattern, host_lower):
                    return provider

        return AIProvider.UNKNOWN

    def _estimate_tokens(
        self,
        request_size: int,
        response_size: int,
    ) -> int:
        """Estimate token count from byte sizes."""
        # Rough estimation: ~4 chars per token
        total_chars = request_size + response_size
        return total_chars // self.CHARS_PER_TOKEN

    def _check_suspicious(self, call: AIAPICall, path: str) -> None:
        """Check for suspicious patterns in the call."""
        for pattern in self.patterns.SUSPICIOUS:
            if re.search(pattern, path, re.IGNORECASE):
                call.is_suspicious = True
                call.flags.append(f"Suspicious pattern: {pattern}")

        # Large request might be data exfiltration
        if call.request_size_bytes > 100_000:  # >100KB request
            call.flags.append("Large request body")
            call.is_suspicious = True

        # Check rate limiting
        window_key = f"{call.source_ip}:{call.provider.value}"
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        self._rate_windows[window_key] = [
            t for t in self._rate_windows[window_key]
            if t > cutoff
        ]
        self._rate_windows[window_key].append(now)

        if len(self._rate_windows[window_key]) > 100:  # >100 calls/min
            call.flags.append("High request rate")
            call.is_suspicious = True

    def _record_call(self, call: AIAPICall) -> None:
        """Record call to history."""
        self._call_history.append(call)

        # Trim history if needed
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history:]

    def get_summary(
        self,
        minutes: int = 60,
    ) -> TrafficSummary:
        """
        Get summary of AI API traffic.

        Args:
            minutes: Time window in minutes

        Returns:
            TrafficSummary with aggregated metrics
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        recent_calls = [c for c in self._call_history if c.timestamp > cutoff]

        summary = TrafficSummary()
        summary.total_calls = len(recent_calls)
        summary.time_range_minutes = minutes

        for call in recent_calls:
            summary.total_request_bytes += call.request_size_bytes
            summary.total_response_bytes += call.response_size_bytes
            summary.estimated_tokens += call.token_estimate

            provider = call.provider.value
            summary.calls_by_provider[provider] = (
                summary.calls_by_provider.get(provider, 0) + 1
            )

            if call.is_suspicious:
                summary.suspicious_calls += 1

        return summary

    def get_recent_calls(
        self,
        limit: int = 50,
        provider: Optional[AIProvider] = None,
        suspicious_only: bool = False,
    ) -> List[AIAPICall]:
        """Get recent AI API calls."""
        calls = list(reversed(self._call_history))

        if provider:
            calls = [c for c in calls if c.provider == provider]

        if suspicious_only:
            calls = [c for c in calls if c.is_suspicious]

        return calls[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


def create_traffic_analyzer(
    config: Optional[Dict[str, Any]] = None
) -> AITrafficAnalyzer:
    """Create an AI Traffic Analyzer instance."""
    return AITrafficAnalyzer(config)
