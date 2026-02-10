"""
SafeClaw Router — YandexGPT Provider.

Yandex Foundation Models adapter with IAM token auth.
Per router_spec.md v1.0.
"""

from __future__ import annotations

import logging

import requests

from .base import BaseProvider, CompletionResult, ProviderHealth

logger = logging.getLogger(__name__)


class YandexGPTProvider(BaseProvider):
    """YandexGPT adapter — REST API with IAM/API-key auth."""

    name = "yandexgpt"
    models = ["yandexgpt-lite", "yandexgpt"]

    def __init__(self, folder_id: str = "", **kwargs):
        super().__init__(**kwargs)
        self.folder_id = folder_id or self._extra.get("folder_id", "")

    def _model_uri(self, model: str) -> str:
        """Build Yandex model URI."""
        return f"gpt://{self.folder_id}/{model}/latest"

    def complete(
        self,
        messages: list[dict],
        model: str = "yandexgpt-lite",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        """Send completion to YandexGPT API."""
        if not self.has_model(model):
            raise ValueError(
                f"Model {model!r} not supported by {self.name}. "
                f"Available: {self.models}"
            )

        url = f"{self.base_url}/completion"
        headers = {
            "Authorization": f"Api-Key {self.api_key}",
            "Content-Type": "application/json",
            "x-folder-id": self.folder_id,
        }

        # YandexGPT uses different message format
        yandex_messages = []
        for msg in messages:
            yandex_messages.append(
                {
                    "role": msg["role"],
                    "text": msg.get("content", msg.get("text", "")),
                }
            )

        payload = {
            "modelUri": self._model_uri(model),
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens),
            },
            "messages": yandex_messages,
        }

        with self._measure_latency() as timer:
            resp = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=120,
            )

        if resp.status_code != 200:
            logger.error(
                "YandexGPT API error: %d %s",
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(
                f"YandexGPT API error: {resp.status_code} " f"{resp.text[:200]}"
            )

        data = resp.json()
        result = data.get("result", data)
        alternatives = result.get("alternatives", [{}])
        message = alternatives[0].get("message", {})
        usage = result.get("usage", {})

        tokens_in = int(usage.get("inputTextTokens", 0))
        tokens_out = int(usage.get("completionTokens", 0))

        return CompletionResult(
            content=message.get("text", ""),
            model=model,
            provider=self.name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            latency_ms=round(timer.elapsed_ms, 1),
            cost_kopecks=self.estimate_cost(tokens_in, tokens_out),
            finish_reason=alternatives[0].get("status", "stop"),
        )

    def health_check(self) -> ProviderHealth:
        """Check YandexGPT API availability."""
        try:
            with self._measure_latency() as timer:
                resp = requests.post(
                    f"{self.base_url}/completion",
                    json={
                        "modelUri": self._model_uri("yandexgpt-lite"),
                        "completionOptions": {
                            "stream": False,
                            "maxTokens": "1",
                        },
                        "messages": [{"role": "user", "text": "ping"}],
                    },
                    headers={
                        "Authorization": (f"Api-Key {self.api_key}"),
                        "x-folder-id": self.folder_id,
                    },
                    timeout=10,
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
