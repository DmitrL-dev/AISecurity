"""
GoMCP Python SDK
================

A Python client library for GoMCP HTTP mode server.

Example:
    >>> from gomcp import GoMCPClient
    >>> client = GoMCPClient("http://localhost:8080")
    >>> tools = client.list_tools()
    >>> result = client.call_tool("echo", {"message": "hello"})
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


__version__ = "1.0.0"
__all__ = [
    "GoMCPClient",
    "GoMCPError",
    "ToolInfo",
    "ToolResult",
    "BatchRequest",
    "BatchResult",
    "HealthStatus",
]


class GoMCPError(Exception):
    """Base exception for GoMCP errors."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.code = code


class ConnectionError(GoMCPError):
    """Connection failed."""
    pass


class TimeoutError(GoMCPError):
    """Request timed out."""
    pass


class ValidationError(GoMCPError):
    """Validation failed."""
    pass


class ToolNotFoundError(GoMCPError):
    """Tool not found."""
    pass


@dataclass
class ToolInfo:
    """Information about a tool."""
    name: str
    description: str = ""
    input_schema: Optional[Dict[str, Any]] = None


@dataclass
class ToolResult:
    """Result of a tool call."""
    output: Any
    duration_ms: float = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class BatchRequest:
    """A single request in a batch."""
    id: str
    tool: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    """Result of a batch call."""
    results: Dict[str, ToolResult]
    total_duration_ms: float = 0
    success_count: int = 0
    error_count: int = 0


@dataclass
class HealthStatus:
    """Health status of the server."""
    status: str
    uptime: str = ""
    workers: int = 0
    tenants: int = 0


class GoMCPClient:
    """
    GoMCP HTTP client.

    Args:
        base_url: Base URL of the GoMCP server (e.g., "http://localhost:8080")
        timeout: Request timeout in seconds (default: 30)
        tenant_id: Optional tenant ID for multi-tenancy
        headers: Optional additional headers
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        tenant_id: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.tenant_id = tenant_id
        self._headers = headers or {}

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an HTTP request."""
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self._headers,
        }

        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id

        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")

        request = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read().decode("utf-8")
                if content:
                    return json.loads(content)
                return None
        except HTTPError as e:
            content = e.read().decode("utf-8")
            try:
                error_data = json.loads(content)
                message = error_data.get("error", str(e))
            except json.JSONDecodeError:
                message = content or str(e)

            if e.code == 404:
                raise ToolNotFoundError(message, e.code)
            elif e.code == 400:
                raise ValidationError(message, e.code)
            else:
                raise GoMCPError(message, e.code)
        except URLError as e:
            raise ConnectionError(f"Connection failed: {e.reason}")
        except TimeoutError:
            raise TimeoutError("Request timed out")

    def list_tools(self) -> List[ToolInfo]:
        """
        List all available tools.

        Returns:
            List of ToolInfo objects
        """
        response = self._request("GET", "/v1/tools")
        tools = response.get("tools", [])
        return [
            ToolInfo(
                name=t.get("name", ""),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema"),
            )
            for t in tools
        ]

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> ToolResult:
        """
        Call a single tool.

        Args:
            name: Tool name
            arguments: Tool arguments
            timeout: Optional timeout override

        Returns:
            ToolResult with output
        """
        data = {
            "tool": name,
            "arguments": arguments or {},
        }
        if timeout is not None:
            data["timeout"] = f"{timeout}s"

        start = time.time()
        try:
            response = self._request("POST", "/v1/tools/call", data)
            duration = (time.time() - start) * 1000
            return ToolResult(
                output=response.get("output"),
                duration_ms=duration,
                success=True,
            )
        except GoMCPError as e:
            duration = (time.time() - start) * 1000
            return ToolResult(
                output=None,
                duration_ms=duration,
                success=False,
                error=str(e),
            )

    def batch_call(
        self,
        requests: List[BatchRequest],
        parallel: bool = False,
        max_concurrent: int = 10,
    ) -> BatchResult:
        """
        Call multiple tools in a batch.

        Args:
            requests: List of BatchRequest objects
            parallel: Execute in parallel (default: False)
            max_concurrent: Max concurrent calls (default: 10)

        Returns:
            BatchResult with all results
        """
        data = {
            "requests": [
                {
                    "id": r.id,
                    "tool": r.tool,
                    "arguments": r.arguments,
                }
                for r in requests
            ],
            "parallel": parallel,
            "maxConcurrent": max_concurrent,
        }

        start = time.time()
        response = self._request("POST", "/v1/tools/batch", data)
        total_duration = (time.time() - start) * 1000

        results = {}
        success_count = 0
        error_count = 0

        for r in response.get("results", []):
            request_id = r.get("id", "")
            success = r.get("success", False)
            if success:
                success_count += 1
            else:
                error_count += 1

            results[request_id] = ToolResult(
                output=r.get("output"),
                duration_ms=r.get("duration_ms", 0),
                success=success,
                error=r.get("error"),
            )

        return BatchResult(
            results=results,
            total_duration_ms=total_duration,
            success_count=success_count,
            error_count=error_count,
        )

    def health(self) -> HealthStatus:
        """Get full health status."""
        response = self._request("GET", "/health")
        return HealthStatus(
            status=response.get("status", "unknown"),
            uptime=response.get("uptime", ""),
            workers=response.get("workers", 0),
            tenants=response.get("tenants", 0),
        )

    def liveness(self) -> bool:
        """Check if server is alive."""
        try:
            self._request("GET", "/healthz")
            return True
        except GoMCPError:
            return False

    def readiness(self) -> bool:
        """Check if server is ready."""
        try:
            self._request("GET", "/readyz")
            return True
        except GoMCPError:
            return False

    def __repr__(self) -> str:
        return f"GoMCPClient(base_url={self.base_url!r})"


def create_client(
    base_url: str,
    timeout: float = 30.0,
    tenant_id: Optional[str] = None,
) -> GoMCPClient:
    """
    Factory function to create a GoMCP client.

    Args:
        base_url: Base URL of the GoMCP server
        timeout: Request timeout in seconds
        tenant_id: Optional tenant ID

    Returns:
        GoMCPClient instance
    """
    return GoMCPClient(base_url, timeout=timeout, tenant_id=tenant_id)
