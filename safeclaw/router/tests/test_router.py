"""
SafeClaw Router — Tests.

Comprehensive tests for provider adapters, router engine,
serializers, and API views.
Per router_spec.md v1.0.
"""

import hashlib
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from billing.models import Subscription, User
from billing.plans import PlanType, SubscriptionStatus
from router.engine import RouterEngine, get_engine
from router.providers.base import (
    MODEL_ALIASES,
    BaseProvider,
    CompletionResult,
    ProviderHealth,
    RoutingStrategy,
)
from router.providers.deepseek import DeepSeekProvider
from router.providers.gigachat import GigaChatProvider
from router.providers.yandexgpt import YandexGPTProvider
from router.serializers import ChatRequestSerializer


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


class MockProvider(BaseProvider):
    """Deterministic mock provider for testing."""

    name = "mock"
    models = ["mock-model"]

    def complete(self, messages, model="mock-model", **kw):
        return CompletionResult(
            content="Hello from mock!",
            model=model,
            provider=self.name,
            tokens_input=10,
            tokens_output=5,
            latency_ms=42.0,
            cost_kopecks=1.0,
        )

    def health_check(self):
        return ProviderHealth(
            name=self.name,
            available=True,
            latency_ms=1.0,
            models=self.models,
        )


class FailingProvider(BaseProvider):
    """Provider that always fails (for failover tests)."""

    name = "failing"
    models = ["fail-model"]

    def complete(self, messages, model="fail-model", **kw):
        raise RuntimeError("Provider unavailable")

    def health_check(self):
        return ProviderHealth(
            name=self.name,
            available=False,
            error="Down",
        )


# ---------------------------------------------------------------
# BaseProvider tests
# ---------------------------------------------------------------


class BaseProviderTest(TestCase):
    """Tests for BaseProvider ABC and dataclasses."""

    def test_completion_result_tokens_total(self):
        r = CompletionResult(
            content="x",
            model="m",
            provider="p",
            tokens_input=10,
            tokens_output=5,
            latency_ms=1.0,
        )
        self.assertEqual(r.tokens_total, 15)

    def test_completion_result_frozen(self):
        r = CompletionResult(
            content="x",
            model="m",
            provider="p",
            tokens_input=1,
            tokens_output=1,
            latency_ms=1.0,
        )
        with self.assertRaises(AttributeError):
            r.content = "y"

    def test_provider_health_defaults(self):
        h = ProviderHealth(name="test", available=True)
        self.assertEqual(h.latency_ms, 0.0)
        self.assertEqual(h.models, [])
        self.assertIsNone(h.error)

    def test_routing_strategy_enum(self):
        self.assertEqual(RoutingStrategy.COST.value, "cost")
        self.assertEqual(RoutingStrategy.QUALITY.value, "quality")

    def test_model_aliases_structure(self):
        self.assertIn("fast", MODEL_ALIASES)
        self.assertIn("smart", MODEL_ALIASES)
        self.assertIn("cheap", MODEL_ALIASES)
        for alias, candidates in MODEL_ALIASES.items():
            for prov, mdl in candidates:
                self.assertIsInstance(prov, str)
                self.assertIsInstance(mdl, str)

    def test_estimate_cost(self):
        p = MockProvider(
            api_key="k",
            base_url="http://x",
            cost_per_1k_input=10,
            cost_per_1k_output=20,
        )
        cost = p.estimate_cost(1000, 1000)
        self.assertEqual(cost, 30.0)

    def test_has_model(self):
        p = MockProvider(api_key="k", base_url="http://x")
        self.assertTrue(p.has_model("mock-model"))
        self.assertFalse(p.has_model("nonexistent"))

    def test_count_tokens_approx(self):
        p = MockProvider(api_key="k", base_url="http://x")
        tokens = p.count_tokens_approx("Hello world!")
        self.assertGreater(tokens, 0)

    def test_repr(self):
        p = MockProvider(api_key="k", base_url="http://x")
        r = repr(p)
        self.assertIn("MockProvider", r)
        self.assertIn("mock-model", r)


# ---------------------------------------------------------------
# RouterEngine tests
# ---------------------------------------------------------------


class RouterEngineTest(TestCase):
    """Tests for the core routing engine."""

    def setUp(self):
        self.engine = RouterEngine()
        self.mock = MockProvider(
            api_key="k",
            base_url="http://mock",
            cost_per_1k_output=10,
        )
        self.engine.register(self.mock)

    def test_register_provider(self):
        self.assertIn("mock", self.engine.providers)

    def test_get_provider(self):
        p = self.engine.get_provider("mock")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "mock")

    def test_get_provider_not_found(self):
        p = self.engine.get_provider("nonexistent")
        self.assertIsNone(p)

    def test_available_models(self):
        models = self.engine.available_models
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["model"], "mock-model")
        self.assertEqual(models[0]["provider"], "mock")

    def test_resolve_direct_model(self):
        candidates = self.engine.resolve_alias("mock-model")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0], ("mock", "mock-model"))

    def test_resolve_unknown_model(self):
        candidates = self.engine.resolve_alias("nonexistent-model")
        self.assertEqual(len(candidates), 0)

    def test_route_success(self):
        messages = [{"role": "user", "content": "Hi"}]
        result = self.engine.route(messages=messages, model="mock-model")
        self.assertEqual(result.provider, "mock")
        self.assertEqual(result.content, "Hello from mock!")
        self.assertEqual(result.tokens_input, 10)
        self.assertEqual(result.tokens_output, 5)

    def test_route_no_provider_raises(self):
        with self.assertRaises(ValueError):
            self.engine.route(
                messages=[{"role": "user", "content": "x"}],
                model="nonexistent",
            )

    def test_failover(self):
        """Failing → mock should succeed."""
        failing = FailingProvider(
            api_key="k",
            base_url="http://fail",
            cost_per_1k_output=5,
        )
        self.engine.register(failing)

        # Both providers support the model
        failing.models = ["shared-model"]
        self.mock.models = ["shared-model"]

        result = self.engine.route(
            messages=[{"role": "user", "content": "x"}],
            model="shared-model",
            strategy=RoutingStrategy.COST,
        )
        # Should have fallen back to mock
        self.assertEqual(result.provider, "mock")

    def test_all_fail_raises(self):
        engine = RouterEngine()
        failing = FailingProvider(
            api_key="k",
            base_url="http://fail",
        )
        engine.register(failing)
        with self.assertRaises(RuntimeError):
            engine.route(
                messages=[{"role": "user", "content": "x"}],
                model="fail-model",
            )

    def test_cost_strategy_sorting(self):
        """Cost strategy: cheapest first."""
        cheap = MockProvider(
            api_key="k",
            base_url="http://cheap",
            cost_per_1k_output=1,
        )
        cheap.name = "cheap_prov"
        cheap.models = ["m"]

        expensive = MockProvider(
            api_key="k",
            base_url="http://exp",
            cost_per_1k_output=100,
        )
        expensive.name = "expensive_prov"
        expensive.models = ["m"]

        engine = RouterEngine()
        engine.register(expensive)  # registered first
        engine.register(cheap)

        result = engine.route(
            messages=[{"role": "user", "content": "x"}],
            model="m",
            strategy=RoutingStrategy.COST,
        )
        self.assertEqual(result.provider, "cheap_prov")

    def test_quality_strategy_sorting(self):
        """Quality strategy: most expensive first."""
        cheap = MockProvider(
            api_key="k",
            base_url="http://cheap",
            cost_per_1k_output=1,
        )
        cheap.name = "cheap_prov"
        cheap.models = ["m"]

        expensive = MockProvider(
            api_key="k",
            base_url="http://exp",
            cost_per_1k_output=100,
        )
        expensive.name = "expensive_prov"
        expensive.models = ["m"]

        engine = RouterEngine()
        engine.register(cheap)
        engine.register(expensive)

        result = engine.route(
            messages=[{"role": "user", "content": "x"}],
            model="m",
            strategy=RoutingStrategy.QUALITY,
        )
        self.assertEqual(result.provider, "expensive_prov")

    def test_health_check_all(self):
        results = self.engine.health_check_all()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].available)


# ---------------------------------------------------------------
# Provider initialization tests
# ---------------------------------------------------------------


class ProviderInitTest(TestCase):
    """Test provider instantiation."""

    def test_deepseek_init(self):
        p = DeepSeekProvider(
            api_key="test",
            base_url="https://api.deepseek.com/v1",
        )
        self.assertEqual(p.name, "deepseek")
        self.assertIn("deepseek-chat", p.models)

    def test_gigachat_init(self):
        p = GigaChatProvider(
            api_key="test",
            base_url=("https://gigachat.devices.sberbank.ru" "/api/v1"),
        )
        self.assertEqual(p.name, "gigachat")
        self.assertIn("GigaChat-2-Lite", p.models)

    def test_yandexgpt_init(self):
        p = YandexGPTProvider(
            api_key="test",
            base_url=("https://llm.api.cloud.yandex.net" "/foundationModels/v1"),
            folder_id="test-folder",
        )
        self.assertEqual(p.name, "yandexgpt")
        self.assertIn("yandexgpt-lite", p.models)
        self.assertEqual(p.folder_id, "test-folder")

    def test_deepseek_unsupported_model(self):
        p = DeepSeekProvider(
            api_key="test",
            base_url="https://api.deepseek.com/v1",
        )
        with self.assertRaises(ValueError):
            p.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="nonexistent-model",
            )

    def test_gigachat_unsupported_model(self):
        p = GigaChatProvider(
            api_key="test",
            base_url=("https://gigachat.devices.sberbank.ru" "/api/v1"),
        )
        with self.assertRaises(ValueError):
            p.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="nonexistent-model",
            )

    def test_yandexgpt_unsupported_model(self):
        p = YandexGPTProvider(
            api_key="test",
            base_url=("https://llm.api.cloud.yandex.net" "/foundationModels/v1"),
        )
        with self.assertRaises(ValueError):
            p.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="nonexistent-model",
            )


# ---------------------------------------------------------------
# Serializer tests
# ---------------------------------------------------------------


class SerializerTest(TestCase):
    """Tests for DRF serializers."""

    def test_chat_request_valid(self):
        data = {
            "messages": [{"role": "user", "content": "Hello!"}],
            "model": "fast",
        }
        ser = ChatRequestSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_chat_request_defaults(self):
        data = {
            "messages": [{"role": "user", "content": "Hi"}],
        }
        ser = ChatRequestSerializer(data=data)
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data["model"], "fast")
        self.assertEqual(ser.validated_data["strategy"], "cost")
        self.assertEqual(ser.validated_data["temperature"], 0.7)

    def test_chat_request_invalid_role(self):
        data = {
            "messages": [{"role": "hacker", "content": "Hi"}],
        }
        ser = ChatRequestSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_chat_request_no_messages(self):
        data = {}
        ser = ChatRequestSerializer(data=data)
        self.assertFalse(ser.is_valid())

    def test_chat_request_temperature_bounds(self):
        data = {
            "messages": [{"role": "user", "content": "Hi"}],
            "temperature": 3.0,
        }
        ser = ChatRequestSerializer(data=data)
        self.assertFalse(ser.is_valid())


# ---------------------------------------------------------------
# API tests
# ---------------------------------------------------------------


class APITest(TestCase):
    """Tests for the router API views."""

    def setUp(self):
        self.client = APIClient()
        # Create user + subscription for auth
        raw_key = "test-router-api-key-12345"
        self.user = User.objects.create(
            email="router@test.com",
            api_key_hash=hashlib.sha256(raw_key.encode()).hexdigest(),
        )
        self.sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=100000,
            tokens_used=0,
        )
        self.auth_headers = {
            "HTTP_X_API_KEY": raw_key,
        }

    def test_providers_list_no_auth_required(self):
        """GET /api/providers/ is public."""
        resp = self.client.get("/api/providers/")
        self.assertEqual(resp.status_code, 200)

    def test_chat_no_auth_returns_401(self):
        resp = self.client.post(
            "/api/chat/",
            data={
                "messages": [{"role": "user", "content": "Hi"}],
            },
            format="json",
        )
        self.assertIn(resp.status_code, [401, 403])

    @patch("router.engine._engine", None)
    @patch("router.engine._register_from_settings")
    def test_chat_with_mock_provider(self, mock_reg):
        """POST /api/chat/ with mock provider."""
        # Manually register mock
        from router.engine import _engine, get_engine

        import router.engine

        router.engine._engine = None
        engine = get_engine()
        mock_prov = MockProvider(
            api_key="k",
            base_url="http://mock",
        )
        engine.register(mock_prov)

        resp = self.client.post(
            "/api/chat/",
            data={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "mock-model",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["content"], "Hello from mock!")
        self.assertEqual(data["provider"], "mock")
        self.assertEqual(data["usage"]["input_tokens"], 10)
        self.assertEqual(data["usage"]["output_tokens"], 5)
        self.assertEqual(data["usage"]["total_tokens"], 15)
        # Check token headers
        self.assertEqual(resp["X-Tokens-Input"], "10")
        self.assertEqual(resp["X-Tokens-Output"], "5")

        # Cleanup
        router.engine._engine = None

    def test_chat_invalid_request(self):
        """POST /api/chat/ with missing messages."""
        resp = self.client.post(
            "/api/chat/",
            data={},
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

    @patch("router.engine._engine", None)
    @patch("router.engine._register_from_settings")
    def test_chat_unknown_model_returns_400(self, mock_reg):
        """POST /api/chat/ with unknown model."""
        import router.engine

        router.engine._engine = None
        get_engine()

        resp = self.client.post(
            "/api/chat/",
            data={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "nonexistent-xyz",
            },
            format="json",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, 400)

        router.engine._engine = None

    @patch("router.engine._engine", None)
    @patch("router.engine._register_from_settings")
    def test_health_check_endpoint(self, mock_reg):
        """GET /api/providers/health/."""
        import router.engine

        router.engine._engine = None
        engine = get_engine()
        mock_prov = MockProvider(
            api_key="k",
            base_url="http://mock",
        )
        engine.register(mock_prov)

        resp = self.client.get(
            "/api/providers/health/",
            **self.auth_headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertTrue(data[0]["available"])
        self.assertEqual(data[0]["name"], "mock")

        router.engine._engine = None


# ---------------------------------------------------------------
# OpenAI-compat provider tests
# ---------------------------------------------------------------


class OpenAICompatTest(TestCase):
    """Tests for the universal OpenAI-compat adapter."""

    def test_init_custom_name(self):
        from router.providers.openai_compat import (
            OpenAICompatProvider,
        )

        p = OpenAICompatProvider(
            name="qwen",
            api_key="none",
            base_url="http://localhost:8002/v1",
            models=[
                "Qwen3-Max-Thinking",
                "Qwen3-Coder-Next",
            ],
        )
        self.assertEqual(p.name, "qwen")
        self.assertTrue(p.has_model("Qwen3-Max-Thinking"))
        self.assertTrue(p.has_model("Qwen3-Coder-Next"))

    def test_init_llama(self):
        from router.providers.openai_compat import (
            OpenAICompatProvider,
        )

        p = OpenAICompatProvider(
            name="llama",
            api_key="none",
            base_url="http://localhost:11434/v1",
            models=[
                "Llama-4-Maverick",
                "Llama-4-Scout",
            ],
        )
        self.assertEqual(p.name, "llama")
        self.assertTrue(p.has_model("Llama-4-Maverick"))

    def test_init_tpro(self):
        from router.providers.openai_compat import (
            OpenAICompatProvider,
        )

        p = OpenAICompatProvider(
            name="tpro",
            api_key="none",
            base_url="http://localhost:8001/v1",
            models=["T-Pro-2.0"],
        )
        self.assertEqual(p.name, "tpro")
        self.assertTrue(p.has_model("T-Pro-2.0"))

    def test_unsupported_model_raises(self):
        from router.providers.openai_compat import (
            OpenAICompatProvider,
        )

        p = OpenAICompatProvider(
            name="test",
            api_key="none",
            base_url="http://localhost/v1",
            models=["model-a"],
        )
        with self.assertRaises(ValueError):
            p.complete(
                messages=[{"role": "user", "content": "hi"}],
                model="model-b",
            )

    def test_local_alias_exists(self):
        self.assertIn("local", MODEL_ALIASES)
        local = MODEL_ALIASES["local"]
        providers = [p for p, _ in local]
        self.assertIn("tpro", providers)
        self.assertIn("qwen", providers)
        self.assertIn("llama", providers)
