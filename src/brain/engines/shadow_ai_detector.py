"""
Shadow AI Detector Engine - Unauthorized AI Usage Detection

Detects and governs unauthorized AI usage in enterprise:
- AI provider domain detection
- API key pattern recognition
- Traffic analysis for AI calls
- Policy enforcement
- Usage reporting

Addresses: Enterprise AI Governance
Research: shadow_ai_detection_deep_dive.md
Invention: Shadow AI Detector (#47)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ShadowAIDetector")


# ============================================================================
# Data Classes
# ============================================================================


class AIProvider(Enum):
    """Known AI providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    MISTRAL = "mistral"
    UNKNOWN = "unknown"


class ViolationType(Enum):
    """Types of Shadow AI violations."""

    UNAPPROVED_PROVIDER = "unapproved_provider"
    LEAKED_API_KEY = "leaked_api_key"
    POLICY_VIOLATION = "policy_violation"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class DetectionResult:
    """Result from Shadow AI detection."""

    detected: bool
    provider: Optional[AIProvider] = None
    violation_type: Optional[ViolationType] = None
    confidence: float = 0.0
    evidence: str = ""
    recommendation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "detected": self.detected,
            "provider": self.provider.value if self.provider else None,
            "violation_type": (
                self.violation_type.value if self.violation_type else None
            ),
            "confidence": self.confidence,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Domain Detector
# ============================================================================


class DomainDetector:
    """
    Detects AI provider domains in traffic.
    """

    AI_DOMAINS = {
        AIProvider.OPENAI: [
            "api.openai.com",
            "openai.azure.com",
        ],
        AIProvider.ANTHROPIC: [
            "api.anthropic.com",
        ],
        AIProvider.GOOGLE: [
            "generativelanguage.googleapis.com",
            "aiplatform.googleapis.com",
            "vertexai.googleapis.com",
        ],
        AIProvider.AZURE_OPENAI: [
            ".openai.azure.com",
        ],
        AIProvider.COHERE: [
            "api.cohere.ai",
        ],
        AIProvider.HUGGINGFACE: [
            "api-inference.huggingface.co",
        ],
        AIProvider.MISTRAL: [
            "api.mistral.ai",
        ],
    }

    def detect(self, url: str) -> Tuple[bool, Optional[AIProvider]]:
        """
        Detect AI provider from URL.

        Returns:
            (detected, provider)
        """
        url_lower = url.lower()

        for provider, domains in self.AI_DOMAINS.items():
            for domain in domains:
                if domain in url_lower:
                    return True, provider

        return False, None


# ============================================================================
# API Key Detector
# ============================================================================


class APIKeyDetector:
    """
    Detects leaked API keys in content.
    """

    KEY_PATTERNS = {
        AIProvider.OPENAI: [
            r"sk-[a-zA-Z0-9]{48}",  # OpenAI key
            r"sk-proj-[a-zA-Z0-9]{48}",  # Project key
        ],
        AIProvider.ANTHROPIC: [
            r"sk-ant-[a-zA-Z0-9]{40,}",  # Anthropic key
        ],
        AIProvider.GOOGLE: [
            r"AIza[a-zA-Z0-9_-]{35}",  # Google API key
        ],
        AIProvider.COHERE: [
            r"[a-zA-Z0-9]{40}",  # Generic (needs context)
        ],
        AIProvider.HUGGINGFACE: [
            r"hf_[a-zA-Z0-9]{34}",  # HuggingFace token
        ],
    }

    def __init__(self):
        self._compiled = {}
        for provider, patterns in self.KEY_PATTERNS.items():
            self._compiled[provider] = [re.compile(p) for p in patterns]

    def detect(self, text: str) -> Tuple[bool, Optional[AIProvider], str]:
        """
        Detect API keys in text.

        Returns:
            (detected, provider, masked_key)
        """
        for provider, patterns in self._compiled.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    key = match.group()
                    masked = key[:8] + "..." + key[-4:]
                    return True, provider, masked

        return False, None, ""


# ============================================================================
# Policy Engine
# ============================================================================


class PolicyEngine:
    """
    Enforces AI usage policies.
    """

    def __init__(self):
        self._approved_providers: Set[AIProvider] = set()
        self._blocked_providers: Set[AIProvider] = set()
        self._require_approval = True

    def approve_provider(self, provider: AIProvider) -> None:
        """Approve a provider for use."""
        self._approved_providers.add(provider)
        self._blocked_providers.discard(provider)

    def block_provider(self, provider: AIProvider) -> None:
        """Block a provider."""
        self._blocked_providers.add(provider)
        self._approved_providers.discard(provider)

    def set_require_approval(self, require: bool) -> None:
        """Set whether approval is required."""
        self._require_approval = require

    def check(self, provider: AIProvider) -> Tuple[bool, str]:
        """
        Check if provider is allowed.

        Returns:
            (allowed, reason)
        """
        if provider in self._blocked_providers:
            return False, f"Provider {provider.value} is blocked"

        if self._require_approval:
            if provider not in self._approved_providers:
                return False, f"Provider {provider.value} not approved"

        return True, ""


# ============================================================================
# Traffic Analyzer
# ============================================================================


class TrafficAnalyzer:
    """
    Analyzes traffic patterns for AI usage.
    """

    def __init__(self):
        self._usage: Dict[str, Dict[AIProvider, int]] = defaultdict(
            lambda: defaultdict(int)
        )

    def record(self, user_id: str, provider: AIProvider) -> None:
        """Record AI usage."""
        self._usage[user_id][provider] += 1

    def get_usage(self, user_id: str) -> Dict[AIProvider, int]:
        """Get usage for user."""
        return dict(self._usage[user_id])

    def get_top_users(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get top users by total AI calls."""
        totals = [(user, sum(provs.values()))
                  for user, provs in self._usage.items()]
        return sorted(totals, key=lambda x: x[1], reverse=True)[:limit]


# ============================================================================
# Main Engine
# ============================================================================


class ShadowAIDetector:
    """
    Shadow AI Detector - Unauthorized AI Usage Detection

    Comprehensive detection and governance:
    - Domain detection
    - API key detection
    - Policy enforcement
    - Traffic analysis

    Invention #47 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self):
        self.domain_detector = DomainDetector()
        self.key_detector = APIKeyDetector()
        self.policy_engine = PolicyEngine()
        self.traffic_analyzer = TrafficAnalyzer()

        logger.info("ShadowAIDetector initialized")

    def analyze_request(
        self,
        url: str,
        content: str,
        user_id: str,
    ) -> DetectionResult:
        """
        Analyze request for Shadow AI.

        Args:
            url: Request URL
            content: Request content
            user_id: User identifier

        Returns:
            DetectionResult
        """
        start = time.time()

        # 1. Check domain
        domain_detected, provider = self.domain_detector.detect(url)

        if domain_detected and provider:
            # Record usage
            self.traffic_analyzer.record(user_id, provider)

            # Check policy
            allowed, reason = self.policy_engine.check(provider)

            if not allowed:
                return DetectionResult(
                    detected=True,
                    provider=provider,
                    violation_type=ViolationType.UNAPPROVED_PROVIDER,
                    confidence=0.95,
                    evidence=f"AI call to {provider.value}",
                    recommendation=reason,
                    latency_ms=(time.time() - start) * 1000,
                )

        # 2. Check for API keys in content
        key_detected, key_provider, masked = self.key_detector.detect(content)

        if key_detected:
            return DetectionResult(
                detected=True,
                provider=key_provider,
                violation_type=ViolationType.LEAKED_API_KEY,
                confidence=0.9,
                evidence=f"API key found: {masked}",
                recommendation="Remove API key from content",
                latency_ms=(time.time() - start) * 1000,
            )

        # No violations
        return DetectionResult(
            detected=False,
            provider=provider,
            latency_ms=(time.time() - start) * 1000,
        )

    def get_report(self) -> Dict:
        """Get usage report."""
        top_users = self.traffic_analyzer.get_top_users()
        return {
            "top_users": [{"user": u, "calls": c} for u, c in top_users],
        }


# ============================================================================
# Convenience
# ============================================================================

_default_detector: Optional[ShadowAIDetector] = None


def get_detector() -> ShadowAIDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = ShadowAIDetector()
    return _default_detector
