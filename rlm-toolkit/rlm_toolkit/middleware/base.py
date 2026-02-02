"""
Middleware Base Classes.

Provides the foundation for building request/response middleware chains.

Example:
    >>> class LoggingMiddleware(Middleware):
    ...     async def before(self, request):
    ...         logger.info(f"Request: {request}")
    ...         return request
    ...     
    ...     async def after(self, response):
    ...         logger.info(f"Response: {response}")
    ...         return response
"""

from __future__ import annotations

import uuid
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class Request:
    """Represents a request through the middleware chain.

    Attributes:
        id: Unique request identifier (correlation ID)
        prompt: The input prompt/query
        metadata: Additional request metadata
        context: Shared context across middlewares
        timestamp: Request creation time
    """
    prompt: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def with_context(self, key: str, value: Any) -> "Request":
        """Add context and return self for chaining."""
        self.context[key] = value
        return self

    def with_metadata(self, key: str, value: Any) -> "Request":
        """Add metadata and return self for chaining."""
        self.metadata[key] = value
        return self


@dataclass
class Response:
    """Represents a response through the middleware chain.

    Attributes:
        request_id: Correlation ID from request
        content: The response content
        metadata: Additional response metadata
        context: Shared context across middlewares
        timestamp: Response creation time
        tokens_used: Token count (if available)
        cost: Cost in USD (if available)
        latency_ms: Processing time in milliseconds
    """
    content: str
    request_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency_ms: Optional[float] = None

    def with_context(self, key: str, value: Any) -> "Response":
        """Add context and return self for chaining."""
        self.context[key] = value
        return self

    def with_metadata(self, key: str, value: Any) -> "Response":
        """Add metadata and return self for chaining."""
        self.metadata[key] = value
        return self


class Middleware(ABC):
    """Abstract base class for middleware.

    Middleware processes requests before they reach the handler
    and responses after the handler returns.

    Subclasses should implement `before` and/or `after` methods.
    Both methods receive and return the request/response objects,
    allowing modification or enrichment.

    Example:
        >>> class TimingMiddleware(Middleware):
        ...     async def before(self, request: Request) -> Request:
        ...         request.context["start_time"] = time.time()
        ...         return request
        ...     
        ...     async def after(self, response: Response) -> Response:
        ...         start = response.context.get("start_time", 0)
        ...         response.latency_ms = (time.time() - start) * 1000
        ...         return response
    """

    @property
    def name(self) -> str:
        """Middleware name for logging."""
        return self.__class__.__name__

    async def before(self, request: Request) -> Request:
        """Process request before handler.

        Override to add pre-processing logic.
        Must return the (possibly modified) request.

        Args:
            request: Incoming request

        Returns:
            Processed request
        """
        return request

    async def after(self, response: Response) -> Response:
        """Process response after handler.

        Override to add post-processing logic.
        Must return the (possibly modified) response.

        Args:
            response: Handler response

        Returns:
            Processed response
        """
        return response

    def before_sync(self, request: Request) -> Request:
        """Synchronous version of before.

        Override for sync-only middleware.
        Default calls async before via asyncio.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.before(request))

    def after_sync(self, response: Response) -> Response:
        """Synchronous version of after.

        Override for sync-only middleware.
        Default calls async after via asyncio.
        """
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self.after(response))


class PassthroughMiddleware(Middleware):
    """No-op middleware that passes through unchanged.

    Useful for conditional middleware or testing.
    """
    pass


class CompositeMiddleware(Middleware):
    """Combines multiple middlewares into one.

    Useful for grouping related middlewares.

    Example:
        >>> auth_stack = CompositeMiddleware([
        ...     AuthMiddleware(),
        ...     RateLimitMiddleware(),
        ... ])
    """

    def __init__(self, middlewares: List[Middleware]):
        self._middlewares = middlewares

    async def before(self, request: Request) -> Request:
        """Execute all middlewares' before in order."""
        for m in self._middlewares:
            request = await m.before(request)
        return request

    async def after(self, response: Response) -> Response:
        """Execute all middlewares' after in reverse order."""
        for m in reversed(self._middlewares):
            response = await m.after(response)
        return response
