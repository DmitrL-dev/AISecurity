"""Decorator-based tool definition for GoMCP."""

import functools
import inspect
from typing import Any, Callable, TypeVar

from pydantic import BaseModel  # noqa: F401 - reserved for future use

from gomcp.types import ToolDefinition, ToolResult, ToolError, ErrorCode

F = TypeVar("F", bound=Callable[..., Any])


class Tool:
    """Wrapper for a tool function with metadata."""

    def __init__(
        self,
        func: Callable,
        name: str | None = None,
        description: str | None = None,
        timeout_ms: int = 30000,
    ):
        self.func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        self.timeout_ms = timeout_ms
        self._input_schema = self._generate_schema()
        functools.update_wrapper(self, func)

    def _generate_schema(self) -> dict:
        """Generate JSON Schema from function signature."""
        sig = inspect.signature(self.func)
        hints = getattr(self.func, "__annotations__", {})

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name, str)
            json_type = self._python_type_to_json(param_type)

            properties[param_name] = {"type": json_type}

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @staticmethod
    def _python_type_to_json(python_type: type) -> str:
        """Convert Python type to JSON Schema type."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(python_type, "string")

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition for registration."""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self._input_schema,
            default_timeout_ms=self.timeout_ms,
        )

    async def __call__(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        try:
            if inspect.iscoroutinefunction(self.func):
                result = await self.func(**kwargs)
            else:
                result = self.func(**kwargs)
            return ToolResult(output=result)
        except TypeError as e:
            return ToolResult(
                error=ToolError(
                    code=ErrorCode.INVALID_ARGUMENTS,
                    message=str(e),
                )
            )
        except Exception as e:
            return ToolResult(
                error=ToolError(
                    code=ErrorCode.UNKNOWN,
                    message=str(e),
                    details=type(e).__name__,
                )
            )


def tool(
    name: str | None = None,
    description: str | None = None,
    timeout_ms: int = 30000,
) -> Callable[[F], Tool]:
    """Decorator to define a GoMCP tool.

    Usage:
        @tool(description="Adds two numbers")
        def add(a: int, b: int) -> int:
            return a + b

        @tool()
        async def fetch_data(url: str) -> dict:
            # async operation
            return {"data": "..."}
    """
    def decorator(func: F) -> Tool:
        return Tool(
            func=func,
            name=name,
            description=description,
            timeout_ms=timeout_ms,
        )
    return decorator
