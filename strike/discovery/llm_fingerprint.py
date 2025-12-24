"""
SENTINEL Strike — LLM Fingerprinter

Detect LLM providers and endpoints.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class LLMProvider(str, Enum):
    """Known LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    AWS_BEDROCK = "aws_bedrock"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


@dataclass
class LLMEndpoint:
    """Discovered LLM endpoint."""

    url: str
    provider: LLMProvider = LLMProvider.UNKNOWN
    model: Optional[str] = None
    auth_required: bool = True
    features: list[str] = field(default_factory=list)


# API path patterns by provider
PROVIDER_PATTERNS = {
    LLMProvider.OPENAI: [
        "/v1/chat/completions",
        "/v1/completions",
        "/v1/embeddings",
        "/v1/models",
    ],
    LLMProvider.ANTHROPIC: [
        "/v1/messages",
        "/v1/complete",
    ],
    LLMProvider.GOOGLE: [
        "/v1/models",
        "/v1beta/models",
    ],
    LLMProvider.AZURE_OPENAI: [
        "/openai/deployments",
    ],
    LLMProvider.HUGGINGFACE: [
        "/api/inference",
        "/models",
    ],
    LLMProvider.OLLAMA: [
        "/api/generate",
        "/api/chat",
    ],
}

# Common LLM API paths to probe
COMMON_PATHS = [
    "/api/chat",
    "/api/v1/chat",
    "/v1/chat/completions",
    "/v1/messages",
    "/api/generate",
    "/assistant",
    "/ask",
    "/query",
    "/ai/query",
    "/llm/generate",
    "/chatbot/query",
]


class LLMFingerprinter:
    """Fingerprint LLM endpoints."""

    def __init__(self):
        self.timeout = 5.0

    async def probe_endpoints(
        self, base_url: str, paths: list[str] = None
    ) -> list[LLMEndpoint]:
        """Probe for LLM endpoints."""
        paths = paths or COMMON_PATHS
        endpoints = []

        for path in paths:
            url = f"{base_url.rstrip('/')}{path}"
            endpoint = await self._probe_single(url)
            if endpoint:
                endpoints.append(endpoint)

        return endpoints

    async def _probe_single(self, url: str) -> Optional[LLMEndpoint]:
        """Probe single endpoint."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # OPTIONS request first (less intrusive)
                try:
                    resp = await client.options(url)
                    if resp.status_code in [200, 204, 405]:
                        # Endpoint exists
                        provider = self._detect_provider(url, resp.headers)
                        return LLMEndpoint(
                            url=url,
                            provider=provider,
                            auth_required=resp.status_code == 401,
                        )
                except Exception:
                    pass

                # HEAD request as fallback
                try:
                    resp = await client.head(url)
                    if resp.status_code not in [404, 500, 502, 503]:
                        provider = self._detect_provider(url, resp.headers)
                        return LLMEndpoint(
                            url=url,
                            provider=provider,
                            auth_required=resp.status_code == 401,
                        )
                except Exception:
                    pass

        except ImportError:
            pass  # httpx not installed

        return None

    def _detect_provider(self, url: str, headers: dict) -> LLMProvider:
        """Detect provider from URL and headers."""
        url_lower = url.lower()

        # Check URL patterns
        for provider, patterns in PROVIDER_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower:
                    return provider

        # Check headers
        server = headers.get("server", "").lower()
        if "openai" in server:
            return LLMProvider.OPENAI
        if "anthropic" in server:
            return LLMProvider.ANTHROPIC

        return LLMProvider.UNKNOWN

    def classify_response(self, response: dict) -> LLMProvider:
        """Classify provider from response structure."""
        # OpenAI style
        if "choices" in response and "message" in str(response):
            return LLMProvider.OPENAI

        # Anthropic style
        if "content" in response and "stop_reason" in response:
            return LLMProvider.ANTHROPIC

        # Google style
        if "candidates" in response:
            return LLMProvider.GOOGLE

        return LLMProvider.UNKNOWN
