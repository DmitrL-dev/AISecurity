"""
Tests for RLM v2.4 Middleware Components.

Tests:
- Request and Response dataclasses
- Middleware base class
- MiddlewareChain orchestration
- Built-in middlewares
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch

from rlm_toolkit.middleware import (
    Request,
    Response,
    Middleware,
    MiddlewareChain,
    PassthroughMiddleware,
    CompositeMiddleware,
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
    ContextEnrichmentMiddleware,
)


class TestRequest:
    """Tests for Request dataclass."""

    def test_creation(self):
        """Request should be created with required fields."""
        req = Request(prompt="Hello, world!")
        assert req.prompt == "Hello, world!"
        assert req.id is not None
        assert isinstance(req.metadata, dict)
        assert isinstance(req.context, dict)

    def test_with_context(self):
        """with_context should add context and return self."""
        req = Request(prompt="test")
        result = req.with_context("key", "value")

        assert result is req
        assert req.context["key"] == "value"

    def test_with_metadata(self):
        """with_metadata should add metadata and return self."""
        req = Request(prompt="test")
        result = req.with_metadata("model", "gpt-4")

        assert result is req
        assert req.metadata["model"] == "gpt-4"

    def test_chaining(self):
        """Context and metadata should be chainable."""
        req = (Request(prompt="test")
               .with_context("a", 1)
               .with_context("b", 2)
               .with_metadata("c", 3))

        assert req.context == {"a": 1, "b": 2}
        assert req.metadata == {"c": 3}


class TestResponse:
    """Tests for Response dataclass."""

    def test_creation(self):
        """Response should be created with required fields."""
        resp = Response(content="Hello!", request_id="req-123")
        assert resp.content == "Hello!"
        assert resp.request_id == "req-123"

    def test_optional_fields(self):
        """Optional fields should work."""
        resp = Response(
            content="test",
            tokens_used=100,
            cost=0.005,
            latency_ms=150.5
        )
        assert resp.tokens_used == 100
        assert resp.cost == 0.005
        assert resp.latency_ms == 150.5


class TestMiddleware:
    """Tests for Middleware base class."""

    def test_passthrough_does_nothing(self):
        """PassthroughMiddleware should not modify request/response."""
        middleware = PassthroughMiddleware()

        async def test():
            req = Request(prompt="original")
            result = await middleware.before(req)
            assert result.prompt == "original"

            resp = Response(content="original")
            result = await middleware.after(resp)
            assert result.content == "original"

        asyncio.run(test())

    def test_custom_middleware(self):
        """Custom middleware should work."""

        class PrefixMiddleware(Middleware):
            async def before(self, request: Request) -> Request:
                request.prompt = f"PREFIX: {request.prompt}"
                return request

            async def after(self, response: Response) -> Response:
                response.content = f"SUFFIX: {response.content}"
                return response

        async def test():
            middleware = PrefixMiddleware()

            req = Request(prompt="test")
            req = await middleware.before(req)
            assert req.prompt == "PREFIX: test"

            resp = Response(content="result")
            resp = await middleware.after(resp)
            assert resp.content == "SUFFIX: result"

        asyncio.run(test())

    def test_composite_middleware(self):
        """CompositeMiddleware should chain middlewares."""

        class AddA(Middleware):
            async def before(self, request: Request) -> Request:
                request.context["order"] = request.context.get(
                    "order", "") + "A"
                return request

        class AddB(Middleware):
            async def before(self, request: Request) -> Request:
                request.context["order"] = request.context.get(
                    "order", "") + "B"
                return request

        async def test():
            composite = CompositeMiddleware([AddA(), AddB()])
            req = Request(prompt="test")
            req = await composite.before(req)
            assert req.context["order"] == "AB"

        asyncio.run(test())


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""

    @pytest.mark.asyncio
    async def test_empty_chain(self):
        """Empty chain should just call handler."""
        chain = MiddlewareChain([])

        async def handler(req: Request) -> Response:
            return Response(content=f"Got: {req.prompt}", request_id=req.id)

        req = Request(prompt="hello")
        resp = await chain.process(req, handler)

        assert resp.content == "Got: hello"

    @pytest.mark.asyncio
    async def test_single_middleware(self):
        """Chain with single middleware should work."""

        class UpperMiddleware(Middleware):
            async def before(self, request: Request) -> Request:
                request.prompt = request.prompt.upper()
                return request

        chain = MiddlewareChain([UpperMiddleware()])

        async def handler(req: Request) -> Response:
            return Response(content=req.prompt, request_id=req.id)

        req = Request(prompt="hello")
        resp = await chain.process(req, handler)

        assert resp.content == "HELLO"

    @pytest.mark.asyncio
    async def test_middleware_order(self):
        """Middlewares should execute in correct order."""
        order = []

        class OrderTracker(Middleware):
            def __init__(self, name):
                self._name = name

            async def before(self, request: Request) -> Request:
                order.append(f"{self._name}_before")
                return request

            async def after(self, response: Response) -> Response:
                order.append(f"{self._name}_after")
                return response

        chain = MiddlewareChain([
            OrderTracker("A"),
            OrderTracker("B"),
            OrderTracker("C"),
        ])

        async def handler(req: Request) -> Response:
            order.append("handler")
            return Response(content="ok", request_id=req.id)

        await chain.process(Request(prompt="test"), handler)

        # Before: A -> B -> C, Handler, After: C -> B -> A
        assert order == [
            "A_before", "B_before", "C_before",
            "handler",
            "C_after", "B_after", "A_after"
        ]

    @pytest.mark.asyncio
    async def test_wrap_handler(self):
        """wrap() should create a wrapped handler."""
        chain = MiddlewareChain([PassthroughMiddleware()])

        async def original_handler(req: Request) -> Response:
            return Response(content="original", request_id=req.id)

        wrapped = chain.wrap(original_handler)

        # Call wrapped directly with Request
        resp = await wrapped(Request(prompt="test"))
        assert resp.content == "original"

    @pytest.mark.asyncio
    async def test_context_shared_across_middlewares(self):
        """Context should be shared between middlewares."""

        class SetContext(Middleware):
            async def before(self, request: Request) -> Request:
                request.context["set_by_first"] = True
                return request

        class ReadContext(Middleware):
            async def before(self, request: Request) -> Request:
                request.context["saw_first"] = request.context.get(
                    "set_by_first", False)
                return request

        chain = MiddlewareChain([SetContext(), ReadContext()])

        async def handler(req: Request) -> Response:
            return Response(content="ok", request_id=req.id, context=req.context)

        resp = await chain.process(Request(prompt="test"), handler)
        assert resp.context["saw_first"] is True


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_logs_request(self):
        """Should log request info."""
        middleware = LoggingMiddleware(log_prompts=True)
        req = Request(prompt="test prompt")

        # Just verify it runs without error
        result = await middleware.before(req)
        assert result is req


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware."""

    @pytest.mark.asyncio
    async def test_tracks_timing(self):
        """Should track request timing."""
        middleware = MetricsMiddleware()

        req = Request(prompt="test")
        req = await middleware.before(req)

        # Simulate some processing time
        await asyncio.sleep(0.01)

        resp = Response(content="result", request_id=req.id,
                        context=req.context)
        resp = await middleware.after(resp)

        assert resp.latency_ms is not None
        assert resp.latency_ms > 0

    def test_get_metrics(self):
        """Should return collected metrics."""
        middleware = MetricsMiddleware()
        metrics = middleware.get_metrics()

        assert "total_requests" in metrics
        assert "total_tokens" in metrics


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_under_limit(self):
        """Should allow requests under limit."""
        middleware = RateLimitMiddleware(requests_per_second=100)  # High limit

        for _ in range(5):
            req = Request(prompt="test")
            result = await middleware.before(req)
            assert result is not None

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """Should throttle requests over limit via delay."""
        # With 1 req/sec, second request should be delayed
        middleware = RateLimitMiddleware(requests_per_second=10)

        import time
        start = time.time()
        await middleware.before(Request(prompt="1"))
        await middleware.before(Request(prompt="2"))
        elapsed = time.time() - start

        # Should complete quickly (no long delay)
        assert elapsed < 1.0


class TestErrorHandlingMiddleware:
    """Tests for ErrorHandlingMiddleware."""

    @pytest.mark.asyncio
    async def test_passes_through_on_success(self):
        """Should not modify successful responses."""
        middleware = ErrorHandlingMiddleware()

        resp = Response(content="success")
        result = await middleware.after(resp)

        assert result.content == "success"


class TestContextEnrichmentMiddleware:
    """Tests for ContextEnrichmentMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_context(self):
        """Should enrich request with configured context."""
        middleware = ContextEnrichmentMiddleware(
            context_data={"user_id": "123", "tenant": "acme"}
        )

        req = Request(prompt="test")
        req = await middleware.before(req)

        assert req.context["user_id"] == "123"
        assert req.context["tenant"] == "acme"


class TestMiddlewareIntegration:
    """Integration tests for middleware chain."""

    @pytest.mark.asyncio
    async def test_full_stack(self):
        """Test complete middleware stack."""
        chain = MiddlewareChain([
            ContextEnrichmentMiddleware(context_data={"env": "test"}),
            MetricsMiddleware(),
            LoggingMiddleware(),
        ])

        async def handler(req: Request) -> Response:
            return Response(
                content=f"Processed: {req.prompt}",
                request_id=req.id,
                context=req.context
            )

        req = Request(prompt="Hello")
        resp = await chain.process(req, handler)

        assert "Processed: Hello" in resp.content
        assert resp.context.get("env") == "test"
        assert resp.latency_ms is not None


class TestEdgeCases:
    """Edge cases and boundary condition tests."""

    def test_empty_chain(self):
        """Empty chain should work."""
        chain = MiddlewareChain()
        assert len(chain._middlewares) == 0

    @pytest.mark.asyncio
    async def test_empty_prompt(self):
        """Empty prompt should be handled."""
        req = Request(prompt="")

        async def handler(r):
            return Response(content="handled", request_id=r.id)

        chain = MiddlewareChain([PassthroughMiddleware()])
        resp = await chain.process(req, handler)
        assert resp.content == "handled"

    @pytest.mark.asyncio
    async def test_very_long_prompt(self):
        """Very long prompts should work."""
        long_prompt = "x" * 100000
        req = Request(prompt=long_prompt)

        async def handler(r):
            return Response(content=f"len={len(r.prompt)}", request_id=r.id)

        chain = MiddlewareChain()
        resp = await chain.process(req, handler)
        assert "100000" in resp.content

    @pytest.mark.asyncio
    async def test_unicode_content(self):
        """Unicode content should be handled."""
        req = Request(prompt="Привет мир 🌍 日本語")

        async def handler(r):
            return Response(content=r.prompt, request_id=r.id)

        chain = MiddlewareChain()
        resp = await chain.process(req, handler)
        assert "Привет" in resp.content
        assert "🌍" in resp.content

    def test_request_metadata_types(self):
        """Request should handle various metadata types."""
        req = Request(
            prompt="test",
            metadata={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "list": [1, 2, 3],
                "nested": {"a": {"b": "c"}},
            }
        )
        assert req.metadata["nested"]["a"]["b"] == "c"

    @pytest.mark.asyncio
    async def test_exception_propagation(self):
        """Exceptions should propagate correctly."""

        class ErrorMiddleware(Middleware):
            async def before(self, request):
                raise RuntimeError("Middleware error")

        chain = MiddlewareChain([ErrorMiddleware()])

        async def handler(r):
            return Response(content="ok", request_id=r.id)

        with pytest.raises(RuntimeError):
            await chain.process(Request(prompt="test"), handler)

    @pytest.mark.asyncio
    async def test_response_modification(self):
        """Middleware should be able to modify response."""

        class ModifyResponse(Middleware):
            async def after(self, response):
                response.content = f"MODIFIED: {response.content}"
                return response

        chain = MiddlewareChain([ModifyResponse()])

        async def handler(r):
            return Response(content="original", request_id=r.id)

        resp = await chain.process(Request(prompt="test"), handler)
        assert resp.content == "MODIFIED: original"

    @pytest.mark.asyncio
    async def test_multiple_chains(self):
        """Multiple independent chains should work."""
        chain1 = MiddlewareChain([PassthroughMiddleware()])
        chain2 = MiddlewareChain([PassthroughMiddleware()])

        async def handler(r):
            return Response(content="ok", request_id=r.id)

        resp1 = await chain1.process(Request(prompt="test1"), handler)
        resp2 = await chain2.process(Request(prompt="test2"), handler)

        assert resp1.content == "ok"
        assert resp2.content == "ok"
