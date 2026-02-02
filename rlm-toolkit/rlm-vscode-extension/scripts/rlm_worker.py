#!/usr/bin/env python3
"""
RLM Worker - Long-running Python process for RLM MCP tools.

This worker receives JSON-RPC requests on stdin and writes responses to stdout.
It provides a persistent Python environment for RLM tools that require Python.

Usage:
    python rlm_worker.py
"""

import json
import sys
import os
import asyncio
import traceback
from pathlib import Path
from typing import Any, Dict, Optional


# Add project paths
PROJECT_ROOT = os.environ.get('RLM_PROJECT_ROOT', os.getcwd())
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'src'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'rlm-toolkit'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'rlm-toolkit', 'src'))


class RLMWorker:
    """Long-running RLM tool executor."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.store = None
        self.tools = {}

    async def initialize(self) -> bool:
        """Initialize RLM components."""
        try:
            from rlm_toolkit.memory_bridge.v2.hierarchical import HierarchicalMemoryStore
            from rlm_toolkit.memory_bridge.mcp_tools_v2 import register_memory_bridge_v2_tools

            # Create mock server for tool registration
            class MockServer:
                def __init__(self):
                    self.tools = {}

                def tool(self, name=None, description=None):
                    def decorator(func):
                        self.tools[name] = func
                        return func
                    return decorator

            server = MockServer()

            db_path = self.project_root / '.rlm' / 'memory' / 'memory_bridge_v2.db'
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self.store = HierarchicalMemoryStore(db_path=str(db_path))
            register_memory_bridge_v2_tools(
                server, self.store, self.project_root)
            self.tools = server.tools

            return True
        except Exception as e:
            print(json.dumps({
                'id': 0,
                'success': False,
                'error': f'Initialization failed: {e}',
                'trace': traceback.format_exc()
            }), flush=True)
            return False

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a single tool request."""
        req_id = request.get('id', 0)
        tool = request.get('tool', '')
        params = request.get('params', {}) or {}

        try:
            if tool not in self.tools:
                return {
                    'id': req_id,
                    'success': False,
                    'error': f'Tool {tool} not found. Available: {list(self.tools.keys())}'
                }

            # Call the tool
            result = await self.tools[tool](**params)

            return {
                'id': req_id,
                'success': True,
                'result': result if isinstance(result, dict) else {'data': result}
            }

        except Exception as e:
            return {
                'id': req_id,
                'success': False,
                'error': str(e),
                'trace': traceback.format_exc()
            }

    async def run(self):
        """Main worker loop - read from stdin, write to stdout."""
        if not await self.initialize():
            return

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )

                if not line:
                    break  # EOF

                line = line.strip()
                if not line:
                    continue

                request = json.loads(line)
                response = await self.handle_request(request)

                print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                print(json.dumps({
                    'id': 0,
                    'success': False,
                    'error': f'Invalid JSON: {e}'
                }), flush=True)
            except EOFError:
                break
            except Exception as e:
                print(json.dumps({
                    'id': 0,
                    'success': False,
                    'error': str(e),
                    'trace': traceback.format_exc()
                }), flush=True)


def main():
    """Entry point."""
    project_root = os.environ.get('RLM_PROJECT_ROOT', os.getcwd())
    worker = RLMWorker(project_root)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
