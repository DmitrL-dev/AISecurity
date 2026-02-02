"""
Middleware Chain.

Orchestrates middleware execution in a chain pattern.

Example:
    >>> chain = MiddlewareChain([
    ...     LoggingMiddleware(),
    ...     MetricsMiddleware(),
    ...     AuthMiddleware(),
    ... ])
    >>> 
    >>> async def handler(request):
    ...     return Response(content=llm.generate(request.prompt))
    >>> 
    >>> response = await chain.process(Request(prompt="Hello"), handler)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, List, Optional, Union, Awaitable

from rlm_toolkit.middleware.base import Middleware, Request, Response

logger = logging.getLogger(__name__)


# Type alias for handlers
Handler = Callable[[Request], Union[Response, Awaitable[Response]]]


class MiddlewareChain:
    """Chain of middlewares with request/response processing.

    Processes requests through middlewares in order, calls the handler,
    then processes responses through middlewares in reverse order.

    Flow:
        Request → [M1.before] → [M2.before] → [M3.before] → Handler
                                                               ↓
        Response ← [M1.after] ← [M2.after] ← [M3.after] ← Result

    Args:
        middlewares: List of middleware instances
        name: Chain name for logging

    Example:
        >>> chain = MiddlewareChain([
        ...     LoggingMiddleware(),
        ...     MetricsMiddleware(),
        ... ], name="llm_chain")
        >>> 
        >>> response = await chain.process(
        ...     Request(prompt="Hello"),
        ...     handler=my_llm_handler
        ... )
    """

    def __init__(
        self,
        middlewares: Optional[List[Middleware]] = None,
        name: str = "default"
    ):
        self._middlewares: List[Middleware] = middlewares or []
        self.name = name

    @property
    def middlewares(self) -> List[Middleware]:
        """Get list of middlewares."""
        return list(self._middlewares)

    def add(self, middleware: Middleware) -> "MiddlewareChain":
        """Add middleware to chain.

        Args:
            middleware: Middleware to add

        Returns:
            Self for chaining
        """
        self._middlewares.append(middleware)
        return self

    def insert(self, index: int, middleware: Middleware) -> "MiddlewareChain":
        """Insert middleware at specific position.

        Args:
            index: Position to insert at
            middleware: Middleware to insert

        Returns:
            Self for chaining
        """
        self._middlewares.insert(index, middleware)
        return self

    def remove(self, name: str) -> "MiddlewareChain":
        """Remove middleware by name.

        Args:
            name: Middleware class name to remove

        Returns:
            Self for chaining
        """
        self._middlewares = [m for m in self._middlewares if m.name != name]
        return self

    def clear(self) -> "MiddlewareChain":
        """Remove all middlewares.

        Returns:
            Self for chaining
        """
        self._middlewares.clear()
        return self

    async def process(
        self,
        request: Request,
        handler: Handler
    ) -> Response:
        """Process request through middleware chain.

        Args:
            request: Input request
            handler: Core handler function

        Returns:
            Processed response
        """
        start_time = time.time()

        # Pre-processing: execute middlewares in order
        for middleware in self._middlewares:
            try:
                request = await middleware.before(request)
            except Exception as e:
                logger.error(
                    f"Middleware {middleware.name}.before failed: {e}")
                raise

        # Call handler
        try:
            result = handler(request)
            if asyncio.iscoroutine(result):
                response = await result
            else:
                response = result
        except Exception as e:
            # Create error response
            response = Response(
                content=str(e),
                request_id=request.id,
                context=request.context.copy(),
                metadata={"error": True, "error_type": type(e).__name__}
            )
            logger.error(f"Handler failed: {e}")

        # Ensure response has request_id
        if not response.request_id:
            response.request_id = request.id

        # Copy context from request
        response.context.update(request.context)

        # Post-processing: execute middlewares in reverse order
        for middleware in reversed(self._middlewares):
            try:
                response = await middleware.after(response)
            except Exception as e:
                logger.error(f"Middleware {middleware.name}.after failed: {e}")
                raise

        # Calculate latency if not set
        if response.latency_ms is None:
            response.latency_ms = (time.time() - start_time) * 1000

        return response

    def process_sync(
        self,
        request: Request,
        handler: Callable[[Request], Response]
    ) -> Response:
        """Synchronous version of process.

        Args:
            request: Input request
            handler: Core handler function (sync)

        Returns:
            Processed response
        """
        start_time = time.time()

        # Pre-processing
        for middleware in self._middlewares:
            request = middleware.before_sync(request)

        # Call handler
        try:
            response = handler(request)
        except Exception as e:
            response = Response(
                content=str(e),
                request_id=request.id,
                context=request.context.copy(),
                metadata={"error": True, "error_type": type(e).__name__}
            )

        if not response.request_id:
            response.request_id = request.id
        response.context.update(request.context)

        # Post-processing
        for middleware in reversed(self._middlewares):
            response = middleware.after_sync(response)

        if response.latency_ms is None:
            response.latency_ms = (time.time() - start_time) * 1000

        return response

    def wrap(self, handler: Handler) -> Handler:
        """Wrap a handler with this middleware chain.

        Returns a new handler that processes through the chain.

        Args:
            handler: Handler to wrap

        Returns:
            Wrapped handler

        Example:
            >>> @chain.wrap
            ... async def my_handler(request):
            ...     return Response(content="Hello")
        """
        async def wrapped(request: Request) -> Response:
            return await self.process(request, handler)
        return wrapped

    def __len__(self) -> int:
        """Number of middlewares in chain."""
        return len(self._middlewares)

    def __repr__(self) -> str:
        names = [m.name for m in self._middlewares]
        return f"MiddlewareChain({self.name}, [{' → '.join(names)}])"
