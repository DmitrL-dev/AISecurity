#!/usr/bin/env python3
"""
RLM-Toolkit Installer for Antigravity IDE.

Automatically configures RLM as an MCP server in Antigravity.

Usage:
    python install_antigravity.py
    # or after pip install:
    rlm-install
"""

import json
import os
import sys
from pathlib import Path


def get_antigravity_config_path() -> Path:
    """Find Antigravity MCP config file."""
    # Common locations
    candidates = [
        Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        Path.home() / ".antigravity" / "mcp_config.json",
        Path.home() / "AppData" / "Roaming" / "Antigravity" / "mcp_config.json",
        Path.home() / ".config" / "antigravity" / "mcp_config.json",
    ]

    for path in candidates:
        if path.exists():
            return path

    # Default to first option (create if needed)
    return candidates[0]


def get_rlm_config(project_root: str = None) -> dict:
    """Generate RLM MCP server configuration."""
    return {
        "command": sys.executable,  # Use current Python
        "args": ["-m", "rlm_toolkit.mcp.server"],
        "env": {
            "RLM_PROJECT_ROOT": project_root or "${workspaceFolder}",
            "RLM_SECURE_MEMORY": "true",
        },
    }


def install():
    """Install RLM into Antigravity MCP config."""
    print("=" * 50)
    print("RLM-Toolkit Installer for Antigravity IDE")
    print("=" * 50)

    config_path = get_antigravity_config_path()
    print(f"\nConfig file: {config_path}")

    # Load or create config
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                content = f.read().strip()
                config = json.loads(content) if content else {"mcpServers": {}}
            print("✓ Found existing config")
        except json.JSONDecodeError:
            config = {"mcpServers": {}}
            print("✓ Resetting empty/invalid config")
    else:
        config = {"mcpServers": {}}
        config_path.parent.mkdir(parents=True, exist_ok=True)
        print("✓ Creating new config")

    # Ensure mcpServers exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if already installed
    if "rlm-toolkit" in config["mcpServers"]:
        print("\n⚠ RLM-Toolkit is already installed!")
        response = input("Reinstall? (y/N): ").strip().lower()
        if response != "y":
            print("Cancelled.")
            return

    # Get project root
    default_root = os.getcwd()
    print(f"\nDefault project root: {default_root}")
    project_root = input(f"Project root [{default_root}]: ").strip() or default_root

    # Add RLM config
    config["mcpServers"]["rlm-toolkit"] = get_rlm_config(project_root)

    # Save config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print("\n" + "=" * 50)
    print("✓ RLM-Toolkit installed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Restart Antigravity IDE")
    print("2. In chat, try: 'What is the status of RLM?'")
    print("3. The agent will use rlm_status tool")
    print("\nAvailable tools:")
    print("  - rlm_status      : Get server status")
    print("  - rlm_reindex     : Reindex project")
    print("  - rlm_query       : Search in context")
    print("  - rlm_analyze     : Deep code analysis")
    print("  - rlm_memory      : Memory operations")
    print("  - rlm_validate    : Check freshness")
    print("  - rlm_settings    : Get/set settings")


def uninstall():
    """Remove RLM from Antigravity config."""
    config_path = get_antigravity_config_path()

    if not config_path.exists():
        print("No Antigravity config found.")
        return

    with open(config_path, "r") as f:
        config = json.load(f)

    if "rlm-toolkit" in config.get("mcpServers", {}):
        del config["mcpServers"]["rlm-toolkit"]
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("✓ RLM-Toolkit uninstalled")
    else:
        print("RLM-Toolkit not found in config")


def main():
    """Main entry point."""
    if len(sys.argv) > 1 and sys.argv[1] == "--uninstall":
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
