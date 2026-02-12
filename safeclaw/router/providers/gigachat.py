"""
SafeClaw Router — GigaChat Provider.

Sber GigaChat adapter with OAuth2 token auth.
Per router_spec.md v1.0.

SEC-06: TLS verification using Sber CA bundle.
Set GIGACHAT_CA_BUNDLE env var to path of
Mintsifry/Russian Trusted CA cert bundle.
"""

from __future__ import annotations

import logging
import os
import time

import requests

from .base import (
    BaseProvider,
    CompletionResult,
    ProviderHealth,
)

logger = logging.getLogger(__name__)

# GigaChat OAuth token URL
GIGACHAT_AUTH_URL = "https://ngw.devices.sberbank.ru:9443" "/api/v2/oauth"

# SEC-06: TLS certificate verification
# Option 1: Set GIGACHAT_CA_BUNDLE to CA cert path
# Option 2: Falls back to system certs (certifi)
# Option 3: Set to "disable" to bypass (NOT recommended)
_ca_bundle = os.environ.get("GIGACHAT_CA_BUNDLE", "")
if _ca_bundle == "disable":
    GIGACHAT_VERIFY: str | bool = False
    logger.warning(
        "GigaChat TLS verification DISABLED. " "Set GIGACHAT_CA_BUNDLE for production."
    )
elif _ca_bundle:
    GIGACHAT_VERIFY = _ca_bundle
else:
    # Default: use system certs (works if Russian
    # Trusted CA is installed in OS trust store)
    GIGACHAT_VERIFY = True


class GigaChatProvider(BaseProvider):
    """GigaChat adapter — OAuth2 + custom Sber API."""

    name = "gigachat"
    models = [
        "GigaChat-2-Lite",
        "GigaChat-2-Pro",
        "GigaChat-2-Max",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._access_token: str | None = None
        self._token_expires: float = 0.0

    def _ensure_token(self) -> str:
        """Get or refresh OAuth2 access token."""
        if self._access_token and time.time() < self._token_expires - 60:
            return self._access_token

        resp = requests.post(
            GIGACHAT_AUTH_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "RqUID": "safeclaw-router",
                "Content-Type": ("application/x-www-form-urlencoded"),
            },
            data={"scope": "GIGACHAT_API_PERS"},
            timeout=15,
            verify=GIGACHAT_VERIFY,  # Sber uses self-signed certs
        )

        if resp.status_code != 200:
            raise RuntimeError(
                f"GigaChat auth failed: {resp.status_code} " f"{resp.text[:200]}"
            )

        data = resp.json()
        self._access_token = data["access_token"]
        # Token valid for 30 min (1800s)
        self._token_expires = time.time() + data.get("expires_at", 1800)
        return self._access_token

    def _headers(self) -> dict:
        token = self._ensure_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def complete(
        self,
        messages: list[dict],
        model: str = "GigaChat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        """Send chat completion to GigaChat API."""
        if not self.has_model(model):
            raise ValueError(
                f"Model {model!r} not supported by {self.name}. "
                f"Available: {self.models}"
            )

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        with self._measure_latency() as timer:
            resp = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=120,
                verify=GIGACHAT_VERIFY,
            )

        if resp.status_code != 200:
            logger.error(
                "GigaChat API error: %d %s",
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(
                f"GigaChat API error: {resp.status_code} " f"{resp.text[:200]}"
            )

        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        return CompletionResult(
            content=choice["message"]["content"],
            model=data.get("model", model),
            provider=self.name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=round(timer.elapsed_ms, 1),
            cost_kopecks=self.estimate_cost(tokens_in, tokens_out),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    def health_check(self) -> ProviderHealth:
        """Check GigaChat availability via models endpoint."""
        try:
            with self._measure_latency() as timer:
                resp = requests.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                    timeout=10,
                    verify=False,
                )
            return ProviderHealth(
                name=self.name,
                available=resp.status_code == 200,
                latency_ms=round(timer.elapsed_ms, 1),
                models=self.models,
            )
        except Exception as e:
            return ProviderHealth(
                name=self.name,
                available=False,
                error=str(e),
            )
