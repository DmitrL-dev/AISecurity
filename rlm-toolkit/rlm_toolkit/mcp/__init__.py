"""
RLM-Toolkit MCP Server Module.

Provides MCP (Model Context Protocol) server for integration with
Antigravity IDE, Cursor, Claude Desktop and other MCP-compatible clients.

Usage:
    python -m rlm_toolkit.mcp.server

Or in mcp.json:
    {
        "mcpServers": {
            "rlm-toolkit": {
                "command": "python",
                "args": ["-m", "rlm_toolkit.mcp.server"]
            }
        }
    }
"""

from .server import create_server, run_server, RLMServer
from .contexts import ContextManager
from .providers import ProviderRouter
from .ratelimit import RateLimiter, RateLimitConfig

__all__ = [
    "create_server",
    "run_server",
    "RLMServer",
    "ContextManager",
    "ProviderRouter",
    "RateLimiter",
    "RateLimitConfig",
]

__version__ = "1.0.0"

