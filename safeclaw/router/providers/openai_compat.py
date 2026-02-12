"""
SafeClaw Router — OpenAI-Compatible Provider.

Universal adapter for any provider that exposes
an OpenAI-compatible REST API:
  - T-Pro 2.0 (via vLLM)
  - Qwen 2.5 (via vLLM)
  - Llama 3.x (via vLLM / Ollama)
  - Any self-hosted or third-party OpenAI-compat server
"""

from __future__ import annotations

import logging

import requests

from .base import BaseProvider, CompletionResult, ProviderHealth

logger = logging.getLogger(__name__)


class OpenAICompatProvider(BaseProvider):
    """Universal OpenAI-compatible adapter.

    Works with:
      - vLLM (--api-key token / --served-model-name)
      - Ollama (http://localhost:11434/v1)
      - text-generation-inference
      - LiteLLM proxy
      - Any OpenAI-format server
    """

    name = "openai_compat"

    def __init__(self, name: str = "openai_compat", **kw):
        super().__init__(**kw)
        self.name = name  # allow custom naming

    def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        """Send chat completion."""
        if model is None:
            model = self.models[0] if self.models else ""

        if model and not self.has_model(model):
            raise ValueError(
                f"Model {model!r} not in {self.name}. " f"Available: {self.models}"
            )

        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

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
                headers=headers,
                timeout=120,
            )

        if resp.status_code != 200:
            logger.error(
                "%s API error: %d %s",
                self.name,
                resp.status_code,
                resp.text[:500],
            )
            raise RuntimeError(
                f"{self.name} API error: " f"{resp.status_code} " f"{resp.text[:200]}"
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
        """Check availability via /models endpoint."""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            with self._measure_latency() as timer:
                resp = requests.get(
                    f"{self.base_url}/models",
                    headers=headers,
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
