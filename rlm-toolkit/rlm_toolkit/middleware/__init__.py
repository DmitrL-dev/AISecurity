"""
Middleware Module.

Provides a structured request/response processing pipeline for RLM operations.

Components:
    - Middleware: Base class for creating middlewares
    - MiddlewareChain: Orchestrates middleware execution
    - Built-in middlewares: Logging, Metrics, RateLimit, ErrorHandling

Example:
    >>> from rlm_toolkit.middleware import MiddlewareChain, LoggingMiddleware
    >>> 
    >>> chain = MiddlewareChain([
    ...     LoggingMiddleware(),
    ...     MetricsMiddleware(),
    ... ])
    >>> 
    >>> response = await chain.process(Request(prompt="Hello"), handler)
"""

from rlm_toolkit.middleware.base import (
    Middleware,
    Request,
    Response,
    PassthroughMiddleware,
    CompositeMiddleware,
)
from rlm_toolkit.middleware.chain import MiddlewareChain
from rlm_toolkit.middleware.builtin import (
    LoggingMiddleware,
    MetricsMiddleware,
    RateLimitMiddleware,
    ErrorHandlingMiddleware,
    ContextEnrichmentMiddleware,
    MetricsData,
)

__all__ = [
    # Base
    "Middleware",
    "Request",
    "Response",
    "PassthroughMiddleware",
    "CompositeMiddleware",
    # Chain
    "MiddlewareChain",
    # Built-in
    "LoggingMiddleware",
    "MetricsMiddleware",
    "RateLimitMiddleware",
    "ErrorHandlingMiddleware",
    "ContextEnrichmentMiddleware",
    "MetricsData",
]
