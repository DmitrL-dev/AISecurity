# Memory Bridge Tools — Shared Components
"""
Shared types and data container for domain tool modules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Union

try:
    from mcp.server import Server
    from mcp.server.fastmcp import FastMCP
except ImportError:
    Server = None  # type: ignore
    FastMCP = None  # type: ignore

# Type alias for server parameter
ServerType = Union["Server", "FastMCP", Any]


@dataclass
class ToolComponents:
    """Simple data container for initialized v2 components.

    Created by the orchestrator (__init__.py) and passed
    to each domain register_*_tools function.
    """

    store: Any
    router: Any
    extractor: Any
    ttl_manager: Any
    causal_tracker: Any
    cold_start: Any
    orchestrator: Any
    context_builder: Any
    project_root: Path = field(default_factory=lambda: Path("."))

    def as_dict(self) -> Dict[str, Any]:
        """Return components dict for external access."""
        return {
            "store": self.store,
            "router": self.router,
            "extractor": self.extractor,
            "ttl_manager": self.ttl_manager,
            "causal_tracker": self.causal_tracker,
            "cold_start": self.cold_start,
            "orchestrator": self.orchestrator,
            "context_builder": self.context_builder,
        }
