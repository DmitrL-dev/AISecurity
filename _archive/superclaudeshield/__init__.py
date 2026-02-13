# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
SuperClaude Shield - Security wrapper for SuperClaude Framework

Provides security controls for:
- Slash command validation
- Agent behavior monitoring  
- MCP server protection
- Injection attack detection
"""

from .shield import Shield, ShieldResult, ShieldMode
from .validator.command import CommandValidator
from .analyzer.injection import InjectionAnalyzer
from .analyzer.agent_chain import AgentChainAnalyzer
from .analyzer.mcp_flow import MCPGuard
from .enforcer.blocker import Blocker
from .enforcer.alerter import Alerter

__version__ = "1.0.0"
__all__ = [
    "Shield",
    "ShieldResult", 
    "ShieldMode",
    "CommandValidator",
    "InjectionAnalyzer",
    "AgentChainAnalyzer",
    "MCPGuard",
    "Blocker",
    "Alerter",
]
