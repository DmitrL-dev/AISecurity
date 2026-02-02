"""Worker implementation for GoMCP Python SDK."""

import asyncio
import json
import sys
from typing import TextIO

from gomcp.decorators import Tool
from gomcp.types import ToolResult, ToolError, ErrorCode


class Worker:
    """Python worker that communicates with GoMCP supervisor.

    Usage:
        worker = Worker()

        @worker.tool(description="Adds numbers")
        def add(a: int, b: int) -> int:
            return a + b

        worker.run()
    """

    def __init__(
        self,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ):
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.tools: dict[str, Tool] = {}

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
        timeout_ms: int = 30000,
    ):
        """Decorator to register a tool with this worker."""
        def decorator(func):
            t = Tool(
                func=func,
                name=name,
                description=description,
                timeout_ms=timeout_ms,
            )
            self.tools[t.name] = t
            return t
        return decorator

    def register(self, tool: Tool) -> None:
        """Register an existing Tool instance."""
        self.tools[tool.name] = tool

    def list_tools(self) -> list[dict]:
        """Get list of registered tools."""
        return [t.definition.to_dict() for t in self.tools.values()]

    async def call_tool(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name."""
        if name not in self.tools:
            return ToolResult(
                error=ToolError(
                    code=ErrorCode.TOOL_NOT_FOUND,
                    message=f"Tool not found: {name}",
                )
            )

        tool = self.tools[name]
        return await tool(**arguments)

    async def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC request."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.list_tools()},
            }

        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = await self.call_tool(name, arguments)

            if result.error:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": int(result.error.code),
                        "message": result.error.message,
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result.output)}],
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def send_response(self, response: dict) -> None:
        """Send JSON response to stdout."""
        self.stdout.write(json.dumps(response) + "\n")
        self.stdout.flush()

    async def run_async(self) -> None:
        """Run the worker event loop (async)."""
        loop = asyncio.get_event_loop()

        while True:
            line = await loop.run_in_executor(None, self.stdin.readline)
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                self.send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"},
                })
                continue

            response = await self.handle_request(request)
            self.send_response(response)

    def run(self) -> None:
        """Run the worker (blocking)."""
        asyncio.run(self.run_async())
