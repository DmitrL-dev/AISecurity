"""
SENTINEL Strike — Target Management
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum
import httpx


class ModelType(str, Enum):
    """Detected model types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    LLAMA = "llama"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class TargetCapability(BaseModel):
    """Detected target capabilities."""
    model_type: ModelType = ModelType.UNKNOWN
    model_name: Optional[str] = None
    supports_system_prompt: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    max_tokens: Optional[int] = None
    rate_limit: Optional[int] = None
    is_mcp: bool = False
    is_a2a: bool = False


class Target(BaseModel):
    """Target for penetration testing."""
    url: str
    api_key: Optional[str] = None
    mode: Literal["external", "internal"] = "external"
    headers: dict[str, str] = Field(default_factory=dict)
    capabilities: Optional[TargetCapability] = None

    async def probe(self) -> TargetCapability:
        """Probe target to detect capabilities."""
        caps = TargetCapability()

        async with httpx.AsyncClient(timeout=10) as client:
            # Try to detect model type from URL
            if "openai" in self.url.lower():
                caps.model_type = ModelType.OPENAI
            elif "anthropic" in self.url.lower():
                caps.model_type = ModelType.ANTHROPIC
            elif "googleapis" in self.url.lower() or "gemini" in self.url.lower():
                caps.model_type = ModelType.GOOGLE

            # Try health check
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                headers.update(self.headers)

                # Probe with minimal request
                response = await client.post(
                    self.url,
                    headers=headers,
                    json={"messages": [{"role": "user", "content": "Hi"}]},
                )

                if response.status_code == 200:
                    data = response.json()
                    # Try to extract model info
                    if "model" in data:
                        caps.model_name = data["model"]

                # Check rate limit headers
                if "x-ratelimit-limit" in response.headers:
                    caps.rate_limit = int(
                        response.headers["x-ratelimit-limit"])

            except Exception:
                pass

        self.capabilities = caps
        return caps

    async def send(self, messages: list[dict], **kwargs) -> dict:
        """Send request to target."""
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            headers.update(self.headers)
            headers["Content-Type"] = "application/json"

            response = await client.post(
                self.url,
                headers=headers,
                json={"messages": messages, **kwargs},
            )
            return response.json()
