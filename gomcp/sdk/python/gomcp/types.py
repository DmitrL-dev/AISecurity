"""Type definitions for GoMCP tools."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class ErrorCode(IntEnum):
    """Error codes matching Go supervisor errors."""

    UNKNOWN = 0
    TIMEOUT = 1
    TOOL_NOT_FOUND = 2
    WORKER_CRASHED = 3
    PERMISSION_DENIED = 4
    INVALID_ARGUMENTS = 5


@dataclass
class ToolError:
    """Error from tool execution."""

    code: ErrorCode
    message: str
    details: str = ""


@dataclass
class ToolResult:
    """Result of tool execution."""

    output: Any = None
    error: ToolError | None = None
    duration_ms: int = 0

    @property
    def success(self) -> bool:
        """Check if tool executed successfully."""
        return self.error is None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        if self.error:
            return {
                "error": {
                    "code": int(self.error.code),
                    "message": self.error.message,
                    "details": self.error.details,
                }
            }
        return {"output": self.output, "duration_ms": self.duration_ms}


@dataclass
class ToolDefinition:
    """Definition of a tool's interface."""

    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    default_timeout_ms: int = 30000

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "defaultTimeoutMs": self.default_timeout_ms,
        }
