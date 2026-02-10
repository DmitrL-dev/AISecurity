"""
SafeClaw Router — Core Engine.

Orchestrates provider selection, routing strategies, failover,
and model alias resolution.
Per router_spec.md v1.0.
"""

from __future__ import annotations

import logging
from typing import Any

from .providers.base import (
    BaseProvider,
    CompletionResult,
    MODEL_ALIASES,
    ProviderHealth,
    RoutingStrategy,
)

logger = logging.getLogger(__name__)


class RouterEngine:
    """Core routing engine — selects provider and routes requests."""

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}

    # ----- Provider registry ----- #

    def register(self, provider: BaseProvider) -> None:
        """Register a provider."""
        self._providers[provider.name] = provider
        logger.info(
            "Registered provider %s with models %s",
            provider.name,
            provider.models,
        )

    def get_provider(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    @property
    def providers(self) -> dict[str, BaseProvider]:
        return dict(self._providers)

    @property
    def available_models(self) -> list[dict[str, Any]]:
        """List all available models across providers."""
        result = []
        for prov in self._providers.values():
            for model in prov.models:
                result.append(
                    {
                        "provider": prov.name,
                        "model": model,
                        "cost_per_1k_input": prov.cost_per_1k_input,
                        "cost_per_1k_output": prov.cost_per_1k_output,
                    }
                )
        return result

    # ----- Model alias resolution ----- #

    def resolve_alias(self, model_or_alias: str) -> list[tuple[str, str]]:
        """Resolve model alias to [(provider, model)] candidates.

        If not an alias, returns all providers that support the model.
        """
        if model_or_alias in MODEL_ALIASES:
            # Filter to registered providers
            return [
                (prov, mdl)
                for prov, mdl in MODEL_ALIASES[model_or_alias]
                if prov in self._providers
            ]

        # Direct model name — find which providers have it
        candidates = []
        for prov in self._providers.values():
            if prov.has_model(model_or_alias):
                candidates.append((prov.name, model_or_alias))
        return candidates

    # ----- Routing ----- #

    def route(
        self,
        messages: list[dict],
        model: str = "fast",
        strategy: str | RoutingStrategy = RoutingStrategy.COST,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        provider_key: str | None = None,
        **kwargs,
    ) -> CompletionResult:
        """Route a chat request to a provider.

        Args:
            messages: Chat messages in OpenAI format.
            model: Model name or alias (fast/smart/cheap).
            strategy: Routing strategy.
            temperature: LLM temperature.
            max_tokens: Max output tokens.
            provider_key: BYOK — override provider API key.
        """
        if isinstance(strategy, str):
            strategy = RoutingStrategy(strategy)

        candidates = self.resolve_alias(model)
        if not candidates:
            raise ValueError(
                f"No provider found for model {model!r}. "
                f"Available: {list(self._providers.keys())}"
            )

        # Sort candidates by strategy
        candidates = self._sort_by_strategy(candidates, strategy)

        # Try candidates with failover
        last_error: Exception | None = None
        for prov_name, model_name in candidates:
            provider = self._providers[prov_name]
            try:
                logger.info(
                    "Routing to %s/%s (strategy=%s)",
                    prov_name,
                    model_name,
                    strategy.value,
                )
                result = provider.complete(
                    messages=messages,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                return result
            except Exception as exc:
                logger.warning(
                    "Provider %s/%s failed: %s. Trying next.",
                    prov_name,
                    model_name,
                    exc,
                )
                last_error = exc
                continue

        raise RuntimeError(
            f"All providers failed for model {model!r}. " f"Last error: {last_error}"
        )

    def _sort_by_strategy(
        self,
        candidates: list[tuple[str, str]],
        strategy: RoutingStrategy,
    ) -> list[tuple[str, str]]:
        """Sort candidates by routing strategy."""
        if strategy == RoutingStrategy.COST:
            return sorted(
                candidates,
                key=lambda c: self._providers[c[0]].cost_per_1k_output,
            )
        elif strategy == RoutingStrategy.QUALITY:
            # Reverse cost — most expensive = highest quality
            return sorted(
                candidates,
                key=lambda c: self._providers[c[0]].cost_per_1k_output,
                reverse=True,
            )
        # FAILOVER and LATENCY — keep original order
        return candidates

    # ----- Health ----- #

    def health_check_all(self) -> list[ProviderHealth]:
        """Check health of all providers."""
        results = []
        for provider in self._providers.values():
            try:
                health = provider.health_check()
            except Exception as e:
                health = ProviderHealth(
                    name=provider.name,
                    available=False,
                    error=str(e),
                )
            results.append(health)
        return results


# ---------------------------------------------------------------------------
# Singleton engine — initialized from Django settings
# ---------------------------------------------------------------------------

_engine: RouterEngine | None = None


def get_engine() -> RouterEngine:
    """Get or create the singleton RouterEngine."""
    global _engine
    if _engine is not None:
        return _engine

    _engine = RouterEngine()
    _register_from_settings(_engine)
    return _engine


def _register_from_settings(engine: RouterEngine) -> None:
    """Register providers from Django settings."""
    try:
        from django.conf import settings

        providers_config = getattr(settings, "ROUTER_PROVIDERS", {})
    except Exception:
        providers_config = {}

    from .providers.deepseek import DeepSeekProvider
    from .providers.gigachat import GigaChatProvider
    from .providers.openai_compat import (
        OpenAICompatProvider,
    )
    from .providers.yandexgpt import YandexGPTProvider

    native_classes = {
        "deepseek": DeepSeekProvider,
        "gigachat": GigaChatProvider,
        "yandexgpt": YandexGPTProvider,
    }

    for name, config in providers_config.items():
        if not config.get("enabled", True):
            continue
        if not config.get("api_key"):
            logger.warning(
                "Provider %s has no API key, skipping.",
                name,
            )
            continue

        prov_type = config.get("type", name)

        if prov_type == "openai_compat":
            provider = OpenAICompatProvider(
                name=name,
                api_key=config["api_key"],
                base_url=config.get("base_url", ""),
                models=config.get("models"),
                rate_limit=config.get("rate_limit", 60),
                cost_per_1k_input=config.get("cost_per_1k_input", 0),
                cost_per_1k_output=config.get("cost_per_1k_output", 0),
            )
        else:
            cls = native_classes.get(prov_type)
            if not cls:
                logger.warning(
                    "Unknown provider %s, skipping.",
                    name,
                )
                continue
            provider = cls(
                api_key=config["api_key"],
                base_url=config.get("base_url", ""),
                models=config.get("models"),
                rate_limit=config.get("rate_limit", 60),
                cost_per_1k_input=config.get("cost_per_1k_input", 0),
                cost_per_1k_output=config.get("cost_per_1k_output", 0),
                folder_id=config.get("folder_id", ""),
            )
        engine.register(provider)
