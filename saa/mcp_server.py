"""
SAA (SENTINEL Autonomous Agent) MCP Server
==========================================

MCP server for integrating SAA Watchdog with AI IDEs (Antigravity, Claude, etc.)
Solves the terminal hang problem by routing commands through Watchdog HTTP API.

Provides tools for:
- Executing shell commands via Watchdog
- Git operations (commit, push)
- Daemon management (start, stop, restart)
- Status monitoring
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
import sys

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

# Watchdog configuration
WATCHDOG_URL = "http://localhost:3848"
WATCHDOG_TIMEOUT = 2  # Fast timeout for health checks

# Cached watchdog status
_watchdog_available: bool | None = None
_watchdog_last_check: float = 0
WATCHDOG_CACHE_TTL = 30  # seconds

# Create MCP server
server = Server("saa-watchdog")


def check_watchdog_available() -> bool:
    """Quick health check with caching."""
    global _watchdog_available, _watchdog_last_check
    import time

    now = time.time()
    if (
        _watchdog_available is not None
        and (now - _watchdog_last_check) < WATCHDOG_CACHE_TTL
    ):
        return _watchdog_available

    try:
        req = urllib.request.Request(f"{WATCHDOG_URL}/health")
        with urllib.request.urlopen(req, timeout=WATCHDOG_TIMEOUT) as resp:
            _watchdog_available = resp.status == 200
    except Exception:
        _watchdog_available = False

    _watchdog_last_check = now
    return _watchdog_available


def call_watchdog(
    endpoint: str, method: str = "GET", data: Optional[Dict] = None, timeout: int = 30
) -> Dict:
    """Make HTTP request to Watchdog API."""
    # Quick check before making request
    if not check_watchdog_available():
        return {"error": "Watchdog not running. Start it with: start-watchdog.bat"}

    url = f"{WATCHDOG_URL}{endpoint}"

    try:
        if method == "GET":
            req = urllib.request.Request(url)
        else:
            body = json.dumps(data).encode() if data else b"{}"
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        global _watchdog_available
        _watchdog_available = False  # Invalidate cache
        return {"error": f"Watchdog unavailable: {e}"}
    except Exception as e:
        return {"error": str(e)}


@server.list_tools()
async def list_tools():
    """List available SAA Watchdog tools."""
    return [
        Tool(
            name="saa_exec",
            description="Execute a shell command via SAA Watchdog. Use this instead of run_command to avoid terminal hangs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cmd": {
                        "type": "string",
                        "description": "Shell command to execute (e.g., 'pnpm test', 'git status')",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in milliseconds (default: 30000)",
                        "default": 30000,
                    },
                },
                "required": ["cmd"],
            },
        ),
        Tool(
            name="saa_status",
            description="Get SAA Watchdog and Daemon status",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="saa_git_commit",
            description="Stage all changes and commit with message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Commit message",
                    }
                },
                "required": ["message"],
            },
        ),
        Tool(
            name="saa_git_push",
            description="Push commits to remote",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="saa_daemon_restart",
            description="Restart the SAA daemon",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="saa_daemon_start",
            description="Start the SAA daemon",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="saa_daemon_stop",
            description="Stop the SAA daemon",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="saa_history",
            description="Get recent command execution history",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""

    if name == "saa_exec":
        cmd = arguments.get("cmd", "")
        timeout = arguments.get("timeout", 30000)

        if not cmd:
            return [TextContent(type="text", text="❌ Error: command is required")]

        # URL encode for GET request
        import urllib.parse

        encoded_cmd = urllib.parse.quote(cmd)
        result = call_watchdog(
            f"/exec?cmd={encoded_cmd}&timeout={timeout}", timeout=timeout // 1000 + 5
        )

        if "error" in result:
            output = f"❌ Error: {result['error']}"
        else:
            success = result.get("success", False)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            duration = result.get("duration", 0)

            emoji = "✅" if success else "❌"
            output = f"""
{emoji} **Command:** `{cmd}`
━━━━━━━━━━━━━━━━━━━━━━━
⏱️ Duration: {duration}ms

**stdout:**
```
{stdout[:2000]}
```
"""
            if stderr:
                output += f"""
**stderr:**
```
{stderr[:1000]}
```
"""
        return [TextContent(type="text", text=output)]

    elif name == "saa_status":
        result = call_watchdog("/status")

        if "error" in result:
            return [TextContent(type="text", text=f"❌ {result['error']}")]

        watchdog = result.get("watchdog", "unknown")
        daemon = result.get("daemon", "unknown")
        uptime = result.get("uptime", 0)
        cwd = result.get("cwd", "unknown")

        daemon_emoji = "✅" if daemon == "running" else "❌"
        output = f"""
🤖 **SAA Status**
━━━━━━━━━━━━━━━━━━━━━━━
🐕 Watchdog: {watchdog}
{daemon_emoji} Daemon: {daemon} (PID: {result.get('daemonPid', 'N/A')})
⏱️ Uptime: {uptime:.0f}s
📁 CWD: {cwd}
"""
        return [TextContent(type="text", text=output)]

    elif name == "saa_git_commit":
        msg = arguments.get("message", "auto-commit")
        import urllib.parse

        encoded_msg = urllib.parse.quote(msg)
        result = call_watchdog(f"/commit?msg={encoded_msg}")

        if "error" in result:
            return [TextContent(type="text", text=f"❌ {result['error']}")]

        success = result.get("success", False)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        emoji = "✅" if success else "❌"
        output = f"{emoji} **Git Commit:** `{msg}`\n\n```\n{stdout[:500]}\n```"
        if stderr:
            output += f"\nstderr: {stderr[:200]}"

        return [TextContent(type="text", text=output)]

    elif name == "saa_git_push":
        result = call_watchdog("/push")

        success = result.get("success", False)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        emoji = "✅" if success else "❌"
        output = f"{emoji} **Git Push**\n\n```\n{stdout[:500]}\n```"
        if stderr:
            output += f"\nstderr: {stderr[:200]}"

        return [TextContent(type="text", text=output)]

    elif name == "saa_daemon_restart":
        result = call_watchdog("/daemon/restart")
        return [
            TextContent(
                type="text", text=f"🔄 Daemon restart: {json.dumps(result, indent=2)}"
            )
        ]

    elif name == "saa_daemon_start":
        result = call_watchdog("/daemon/start")
        return [
            TextContent(
                type="text", text=f"▶️ Daemon start: {json.dumps(result, indent=2)}"
            )
        ]

    elif name == "saa_daemon_stop":
        result = call_watchdog("/daemon/stop")
        return [
            TextContent(
                type="text", text=f"⏹️ Daemon stop: {json.dumps(result, indent=2)}"
            )
        ]

    elif name == "saa_history":
        result = call_watchdog("/history")

        if isinstance(result, list):
            output = "📜 **Command History**\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            for item in result[:10]:
                cmd = item.get("cmd", "?")[:40]
                success = "✅" if item.get("result", {}).get("success") else "❌"
                output += f"{success} `{cmd}`\n"
            return [TextContent(type="text", text=output)]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
