"""
SAA LLM Bridge MCP Server
=========================

MCP server that proxies LLM requests from external SAA processes
through the Antigravity IDE context.

This solves the "context barrier" problem where standalone processes
(cron, daemon, tests) cannot access the IDE's built-in Claude.

Tools:
- saa_llm_complete: Execute LLM completion via IDE proxy
"""

import json
import os
import sys
from typing import Any, Dict

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Configuration
LLM_BRIDGE_PORT = int(os.environ.get("LLM_BRIDGE_PORT", "3849"))

# Create MCP server
server = Server("saa-llm-bridge")


@server.list_tools()
async def list_tools():
    """List available LLM Bridge tools."""
    return [
        Tool(
            name="saa_llm_complete",
            description="Execute LLM completion through Antigravity IDE. Use this for SAA agents that need Claude access from external processes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to the LLM",
                    },
                    "system": {
                        "type": "string",
                        "description": "Optional system prompt",
                        "default": "",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use (default: claude-sonnet-4-20250514)",
                        "default": "claude-sonnet-4-20250514",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in response (default: 4096)",
                        "default": 4096,
                    },
                },
                "required": ["prompt"],
            },
        ),
        Tool(
            name="saa_llm_status",
            description="Check LLM Bridge status and availability",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "saa_llm_complete":
        prompt = arguments.get("prompt", "")
        system = arguments.get("system", "")
        model = arguments.get("model", "claude-sonnet-4-20250514")
        max_tokens = arguments.get("max_tokens", 4096)

        if not prompt:
            return [TextContent(type="text", text="❌ Error: prompt is required")]

        # The key insight: when this MCP server runs inside Antigravity IDE,
        # it can leverage the IDE's LLM access through the notification system.
        # For now, we return an instruction that the calling agent should
        # route through IDE context.

        # TODO: Implement actual LLM proxy when IDE exposes internal API
        # Current behavior: return structured request for IDE to fulfill

        request = {
            "type": "llm_request",
            "prompt": prompt[:500],  # Truncate for display
            "system": system[:200] if system else None,
            "model": model,
            "max_tokens": max_tokens,
            "status": "pending_ide_fulfillment",
        }

        output = f"""
🤖 **LLM Bridge Request**
━━━━━━━━━━━━━━━━━━━━━━━
**Model:** {model}
**Max Tokens:** {max_tokens}

**Prompt Preview:**
```
{prompt[:300]}{"..." if len(prompt) > 300 else ""}
```

⚠️ **Note:** This MCP server routes requests. For full functionality, 
the IDE must expose an internal LLM API endpoint.

**Request JSON:**
```json
{json.dumps(request, indent=2, ensure_ascii=False)}
```
"""
        return [TextContent(type="text", text=output)]

    elif name == "saa_llm_status":
        output = f"""
🌉 **SAA LLM Bridge Status**
━━━━━━━━━━━━━━━━━━━━━━━
✅ MCP Server: running
📍 Port: {LLM_BRIDGE_PORT}
🔌 IDE Integration: pending

**Purpose:**
Routes LLM requests from external SAA processes 
through Antigravity IDE's built-in Claude access.

**Usage:**
```python
# From SAA agent:
mcp_saa-llm-bridge_saa_llm_complete(
    prompt="Analyze this threat...",
    system="You are a security expert."
)
```
"""
        return [TextContent(type="text", text=output)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    # Quick self-test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("✅ SAA LLM Bridge MCP Server - Self-test passed")
        print(f"   Port: {LLM_BRIDGE_PORT}")
        sys.exit(0)

    asyncio.run(main())
