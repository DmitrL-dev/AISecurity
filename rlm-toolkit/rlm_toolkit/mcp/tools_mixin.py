"""MCP tool registration mixin for RLMServer.

Thin aggregator that delegates to sub-mixins:
- ContextToolsMixin: load_context, query, list, analyze
- MemoryToolsMixin: H-MEM store/recall/forget/consolidate
- ServerToolsMixin: status, session, reindex, validate, settings
"""

from __future__ import annotations

from .context_tools_mixin import ContextToolsMixin
from .memory_tools_mixin import MemoryToolsMixin
from .server_tools_mixin import ServerToolsMixin


class ToolsMixin(
    ContextToolsMixin,
    MemoryToolsMixin,
    ServerToolsMixin,
):
    """MCP tool registration for RLMServer.

    Aggregates 3 sub-mixins covering 10 tools.
    """

    def _register_tools(self) -> None:
        """Register all MCP tools via sub-mixins."""
        self._register_context_tools()
        self._register_memory_tools()
        self._register_server_tools()
