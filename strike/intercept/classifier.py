"""
SENTINEL Strike — LLM Traffic Classifier

Classify and parse LLM API traffic.
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from enum import Enum
import json
import re


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@dataclass
class LLMRequest:
    """Parsed LLM API request."""

    url: str
    method: str
    headers: dict
    body: Optional[dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    provider: LLMProvider = LLMProvider.CUSTOM
    model: Optional[str] = None
    messages: list = field(default_factory=list)
    system_prompt: Optional[str] = None

    @property
    def user_message(self) -> Optional[str]:
        """Get last user message."""
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                return msg.get("content")
        return None


@dataclass
class LLMResponse:
    """Parsed LLM API response."""

    status_code: int
    headers: dict
    body: Optional[dict] = None
    timestamp: datetime = field(default_factory=datetime.now)
    provider: LLMProvider = LLMProvider.CUSTOM
    content: Optional[str] = None
    model: Optional[str] = None
    tokens_used: int = 0

    @property
    def assistant_message(self) -> Optional[str]:
        """Get assistant response content."""
        return self.content


class LLMClassifier:
    """Classify LLM traffic by provider and structure."""

    # URL patterns
    PATTERNS = {
        LLMProvider.OPENAI: [
            r"api\.openai\.com",
            r"/v1/chat/completions",
            r"/v1/completions",
        ],
        LLMProvider.ANTHROPIC: [
            r"api\.anthropic\.com",
            r"/v1/messages",
        ],
        LLMProvider.GOOGLE: [
            r"generativelanguage\.googleapis\.com",
            r"aiplatform\.googleapis\.com",
        ],
        LLMProvider.AZURE: [
            r"\.openai\.azure\.com",
        ],
        LLMProvider.OLLAMA: [
            r"localhost:11434",
            r"/api/generate",
            r"/api/chat",
        ],
    }

    def classify_request(
        self, url: str, method: str, headers: dict, body: bytes
    ) -> Optional[LLMRequest]:
        """Classify and parse request."""
        # Check if this is LLM traffic
        provider = self._detect_provider(url, headers)
        if not provider:
            return None

        # Parse body
        parsed_body = self._parse_body(body)

        # Extract messages
        messages = self._extract_messages(parsed_body, provider)
        system_prompt = self._extract_system_prompt(parsed_body, provider)
        model = self._extract_model(parsed_body, provider)

        return LLMRequest(
            url=url,
            method=method,
            headers=dict(headers),
            body=parsed_body,
            provider=provider,
            model=model,
            messages=messages,
            system_prompt=system_prompt,
        )

    def classify_response(
        self,
        status_code: int,
        headers: dict,
        body: bytes,
        request: Optional[LLMRequest] = None,
    ) -> Optional[LLMResponse]:
        """Classify and parse response."""
        parsed_body = self._parse_body(body)
        provider = request.provider if request else LLMProvider.CUSTOM

        content = self._extract_response_content(parsed_body, provider)
        model = self._extract_model(parsed_body, provider)
        tokens = self._extract_tokens(parsed_body, provider)

        return LLMResponse(
            status_code=status_code,
            headers=dict(headers),
            body=parsed_body,
            provider=provider,
            content=content,
            model=model,
            tokens_used=tokens,
        )

    def _detect_provider(self, url: str, headers: dict) -> Optional[LLMProvider]:
        """Detect LLM provider from URL/headers."""
        url_lower = url.lower()

        for provider, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return provider

        # Check headers for API keys
        auth = headers.get("Authorization", "")
        if "sk-" in auth:
            return LLMProvider.OPENAI
        if headers.get("x-api-key"):
            return LLMProvider.ANTHROPIC

        return None

    def _parse_body(self, body: bytes) -> Optional[dict]:
        """Parse JSON body."""
        try:
            return json.loads(body.decode("utf-8"))
        except Exception:
            return None

    def _extract_messages(self, body: Optional[dict], provider: LLMProvider) -> list:
        """Extract messages from request."""
        if not body:
            return []

        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE]:
            return body.get("messages", [])
        elif provider == LLMProvider.ANTHROPIC:
            return body.get("messages", [])
        elif provider == LLMProvider.GOOGLE:
            contents = body.get("contents", [])
            return [
                {"role": c.get("role"), "content": c.get("parts", [{}])[0].get("text")}
                for c in contents
            ]

        return []

    def _extract_system_prompt(
        self, body: Optional[dict], provider: LLMProvider
    ) -> Optional[str]:
        """Extract system prompt."""
        if not body:
            return None

        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE]:
            for msg in body.get("messages", []):
                if msg.get("role") == "system":
                    return msg.get("content")
        elif provider == LLMProvider.ANTHROPIC:
            return body.get("system")

        return None

    def _extract_model(
        self, body: Optional[dict], provider: LLMProvider
    ) -> Optional[str]:
        """Extract model name."""
        if not body:
            return None
        return body.get("model")

    def _extract_response_content(
        self, body: Optional[dict], provider: LLMProvider
    ) -> Optional[str]:
        """Extract response content."""
        if not body:
            return None

        if provider in [LLMProvider.OPENAI, LLMProvider.AZURE]:
            choices = body.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content")
        elif provider == LLMProvider.ANTHROPIC:
            content = body.get("content", [])
            if content:
                return content[0].get("text")
        elif provider == LLMProvider.GOOGLE:
            candidates = body.get("candidates", [])
            if candidates:
                return (
                    candidates[0].get("content", {}).get("parts", [{}])[0].get("text")
                )

        return None

    def _extract_tokens(self, body: Optional[dict], provider: LLMProvider) -> int:
        """Extract token usage."""
        if not body:
            return 0

        usage = body.get("usage", {})
        return usage.get("total_tokens", 0)
