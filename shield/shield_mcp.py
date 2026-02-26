#!/usr/bin/env python3
"""
SENTINEL Shield MCP Server
===========================

Exposes Shield + Skills Scanner as MCP tools for IDE integration.

Tools:
  - shield_scan_skill: Scan MCP skill source for threats
  - shield_analyze: Analyze text for prompt injection
"""

import json
import sys
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server  # type: ignore
from mcp.types import TextContent, Tool  # type: ignore

from skill_scanner import (
    THREAT_DB,
    format_json,
    format_report,
    scan_directory,
)

server = Server("sentinel-shield")


# ============================================================
# Tool: skill_scan
# ============================================================


SCAN_TOOL = Tool(
    name="shield_scan_skill",
    description=(
        "Scan MCP skill/tool source code for "
        "dangerous patterns. Returns risk verdict "
        "(🟢 Safe / 🟡 Risky / 🔴 Dangerous) "
        "with detailed findings."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": ("Path to MCP skill directory " "or file to scan"),
            },
            "format": {
                "type": "string",
                "enum": ["text", "json"],
                "default": "text",
                "description": "Output format",
            },
        },
        "required": ["path"],
    },
)


# ============================================================
# Tool: analyze (prompt injection check)
# ============================================================


ANALYZE_TOOL = Tool(
    name="shield_analyze",
    description=(
        "Analyze text for security threats: "
        "prompt injection, jailbreak, PII, "
        "exfiltration attempts."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze",
            },
        },
        "required": ["text"],
    },
)


# ============================================================
# Handlers
# ============================================================


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [SCAN_TOOL, ANALYZE_TOOL]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict,
) -> list[TextContent]:
    if name == "shield_scan_skill":
        return await _handle_scan(arguments)
    elif name == "shield_analyze":
        return await _handle_analyze(arguments)
    else:
        return [
            TextContent(
                type="text",
                text=f"Unknown tool: {name}",
            )
        ]


async def _handle_scan(
    args: dict,
) -> list[TextContent]:
    """Handle skill scan request."""
    path_str = args.get("path", "")
    fmt = args.get("format", "text")

    target = Path(path_str)
    if not target.exists():
        return [
            TextContent(
                type="text",
                text=f"❌ Path not found: {path_str}",
            )
        ]

    result = scan_directory(target)

    if fmt == "json":
        output = format_json(result)
    else:
        output = format_report(result)

    return [TextContent(type="text", text=output)]


async def _handle_analyze(
    args: dict,
) -> list[TextContent]:
    """Analyze text for threats using scanner patterns."""
    text = args.get("text", "")
    if not text:
        return [
            TextContent(
                type="text",
                text="❌ No text provided",
            )
        ]

    import re
    import tempfile

    # Write text to temp file for scanning
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(text)
        tmp_path = Path(f.name)

    try:
        result = scan_directory(tmp_path)
        if result.findings:
            output = format_report(result)
        else:
            output = "✅ No threats detected.\n" f"Analyzed {len(text)} characters."
    finally:
        tmp_path.unlink(missing_ok=True)

    return [TextContent(type="text", text=output)]


# ============================================================
# Main
# ============================================================


async def main():
    """Run MCP server via stdio."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read, write):
        await server.run(
            read,
            write,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
