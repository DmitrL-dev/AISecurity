"""
Built-in Middlewares.

Ready-to-use middleware implementations for common patterns:
- LoggingMiddleware: Structured request/response logging
- MetricsMiddleware: Latency, token, and cost tracking
- RateLimitMiddleware: Per-provider rate limiting
- ErrorHandlingMiddleware: Graceful error handling
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set
from collections import defaultdict

from rlm_toolkit.middleware.base import Middleware, Request, Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(Middleware):
    """Structured logging for requests and responses.

    Logs request start, response completion, and any errors.
    Includes correlation IDs for tracing.

    Args:
        log_level: Logging level (default INFO)
        log_prompts: Whether to log full prompts (may be sensitive)
        log_responses: Whether to log full responses
        max_content_length: Truncate content for logging

    Example:
        >>> chain = MiddlewareChain([
        ...     LoggingMiddleware(log_prompts=False),
        ...     # other middlewares...
        ... ])
    """

    def __init__(
        self,
        log_level: int = logging.INFO,
        log_prompts: bool = False,
        log_responses: bool = False,
        max_content_length: int = 100
    ):
        self.log_level = log_level
        self.log_prompts = log_prompts
        self.log_responses = log_responses
        self.max_content_length = max_content_length

    def _truncate(self, text: str) -> str:
        """Truncate text for logging."""
        if len(text) > self.max_content_length:
            return text[:self.max_content_length] + "..."
        return text

    async def before(self, request: Request) -> Request:
        """Log request start."""
        msg = f"[{request.id[:8]}] Request started"
        if self.log_prompts:
            msg += f": {self._truncate(request.prompt)}"
        logger.log(self.log_level, msg)
        request.context["_log_start_time"] = time.time()
        return request

    async def after(self, response: Response) -> Response:
        """Log response completion."""
        start = response.context.get("_log_start_time", 0)
        elapsed = (time.time() - start) * 1000

        msg = f"[{response.request_id[:8]}] Response completed ({elapsed:.1f}ms)"
        if self.log_responses:
            msg += f": {self._truncate(response.content)}"
        if response.metadata.get("error"):
            logger.warning(msg)
        else:
            logger.log(self.log_level, msg)

        return response


@dataclass
class MetricsData:
    """Aggregated metrics data."""
    total_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    error_count: int = 0
    latencies: list = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return sum(self.latencies) / len(self.latencies)

    @property
    def p95_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.total_requests, 1),
        }


class MetricsMiddleware(Middleware):
    """Tracks latency, tokens, and costs.

    Aggregates metrics across all requests for monitoring.

    Args:
        emit_callback: Optional callback for real-time metrics emission

    Example:
        >>> metrics_mw = MetricsMiddleware()
        >>> chain = MiddlewareChain([metrics_mw])
        >>> # After some requests...
        >>> print(metrics_mw.get_metrics())
    """

    def __init__(self, emit_callback: Optional[callable] = None):
        self._metrics = MetricsData()
        self._emit_callback = emit_callback

    async def before(self, request: Request) -> Request:
        """Record start time."""
        request.context["_metrics_start"] = time.time()
        return request

    async def after(self, response: Response) -> Response:
        """Collect metrics from response."""
        start = response.context.get("_metrics_start", time.time())
        latency = (time.time() - start) * 1000

        self._metrics.total_requests += 1
        self._metrics.latencies.append(latency)
        self._metrics.total_latency_ms += latency

        if response.tokens_used:
            self._metrics.total_tokens += response.tokens_used

        if response.cost:
            self._metrics.total_cost += response.cost

        if response.metadata.get("error"):
            self._metrics.error_count += 1

        # Set latency on response if not set
        if response.latency_ms is None:
            response.latency_ms = latency

        # Emit callback
        if self._emit_callback:
            self._emit_callback({
                "request_id": response.request_id,
                "latency_ms": latency,
                "tokens": response.tokens_used,
                "cost": response.cost,
                "error": response.metadata.get("error", False),
            })

        return response

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated metrics."""
        return self._metrics.to_dict()

    def reset(self) -> None:
        """Reset metrics."""
        self._metrics = MetricsData()


class RateLimitMiddleware(Middleware):
    """Per-provider rate limiting.

    Limits requests per time window to avoid hitting provider limits.

    Args:
        requests_per_second: Max requests per second (0 = unlimited)
        tokens_per_minute: Max tokens per minute (0 = unlimited)

    Example:
        >>> chain = MiddlewareChain([
        ...     RateLimitMiddleware(requests_per_second=10),
        ... ])
    """

    def __init__(
        self,
        requests_per_second: float = 0,
        tokens_per_minute: int = 0
    ):
        self.requests_per_second = requests_per_second
        self.tokens_per_minute = tokens_per_minute
        self._last_request_time = 0.0
        self._tokens_this_minute: Dict[int, int] = defaultdict(int)

    async def before(self, request: Request) -> Request:
        """Enforce rate limits."""
        now = time.time()

        # Request rate limiting
        if self.requests_per_second > 0:
            min_interval = 1.0 / self.requests_per_second
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                import asyncio
                await asyncio.sleep(min_interval - elapsed)

        self._last_request_time = time.time()
        return request

    async def after(self, response: Response) -> Response:
        """Track token usage."""
        if self.tokens_per_minute > 0 and response.tokens_used:
            minute = int(time.time() // 60)
            self._tokens_this_minute[minute] += response.tokens_used

            # Warn if approaching limit
            if self._tokens_this_minute[minute] > self.tokens_per_minute * 0.9:
                logger.warning(
                    f"Approaching token limit: {self._tokens_this_minute[minute]}"
                    f"/{self.tokens_per_minute} TPM"
                )

        return response


class ErrorHandlingMiddleware(Middleware):
    """Graceful error handling with optional fallback.

    Catches exceptions and converts them to error responses.
    Can optionally retry or use fallback values.

    Args:
        fallback_content: Content to use on error (None = re-raise)
        log_errors: Whether to log errors
        retries: Number of retries before giving up
    """

    def __init__(
        self,
        fallback_content: Optional[str] = None,
        log_errors: bool = True,
        retries: int = 0
    ):
        self.fallback_content = fallback_content
        self.log_errors = log_errors
        self.retries = retries

    async def after(self, response: Response) -> Response:
        """Handle errors in response."""
        if response.metadata.get("error"):
            error_type = response.metadata.get("error_type", "Unknown")

            if self.log_errors:
                logger.error(
                    f"[{response.request_id[:8]}] Error: {error_type} - "
                    f"{response.content}"
                )

            if self.fallback_content is not None:
                response.content = self.fallback_content
                response.metadata["fallback_used"] = True

        return response


class ContextEnrichmentMiddleware(Middleware):
    """Adds context to all requests.

    Useful for adding user IDs, session IDs, or other metadata.

    Args:
        context_data: Static context to add to all requests
        context_factory: Function to generate dynamic context
    """

    def __init__(
        self,
        context_data: Optional[Dict[str, Any]] = None,
        context_factory: Optional[callable] = None
    ):
        self._static_context = context_data or {}
        self._context_factory = context_factory

    async def before(self, request: Request) -> Request:
        """Enrich request with context."""
        # Add static context
        for key, value in self._static_context.items():
            if key not in request.context:
                request.context[key] = value

        # Add dynamic context
        if self._context_factory:
            dynamic = self._context_factory(request)
            request.context.update(dynamic)

        return request
