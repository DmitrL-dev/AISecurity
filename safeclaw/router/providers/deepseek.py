"""
SafeClaw Router — DeepSeek Provider.

OpenAI-compatible adapter for DeepSeek API.
Per router_spec.md v1.0 — first provider (cheapest, OpenAI-compatible).
"""

from __future__ import annotations

import logging

import requests

from .base import BaseProvider, CompletionResult, ProviderHealth

logger = logging.getLogger(__name__)


class DeepSeekProvider(BaseProvider):
    """DeepSeek adapter — OpenAI-compatible REST API."""

    name = "deepseek"
    models = ["deepseek-chat", "deepseek-reasoner"]

    def complete(
        self,
        messages: list[dict],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        """Send chat completion to DeepSeek API."""
        if not self.has_model(model):
            raise ValueError(
                f"Model {model!r} not supported by {self.name}. "
                f"Available: {self.models}"
            )

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,  # streaming handled separately
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
                "DeepSeek API error: %d %s",
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(
                f"DeepSeek API error: {resp.status_code} " f"{resp.text[:200]}"
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
        """Check DeepSeek API availability via models endpoint."""
        try:
            with self._measure_latency() as timer:
                resp = requests.get(
                    f"{self.base_url}/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    timeout=10,
                )
            available = resp.status_code == 200
            return ProviderHealth(
                name=self.name,
                available=available,
                latency_ms=round(timer.elapsed_ms, 1),
                models=self.models,
            )
        except Exception as e:
            return ProviderHealth(
                name=self.name,
                available=False,
                error=str(e),
            )
