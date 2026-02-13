# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Blocker - blocks dangerous operations
"""

from dataclasses import dataclass
from typing import Callable, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BlockAction:
    """Describes a block action."""
    command: str
    reason: str
    risk_score: float
    blocked: bool = True


class Blocker:
    """
    Enforces security blocks on dangerous operations.
    
    Supports multiple IDE contexts:
    - Claude Code
    - Cursor
    - Windsurf
    - Continue
    - Cody
    """
    
    # IDE-specific handlers (supports all SuperClaude-Org frameworks)
    IDE_CONFIGS = {
        # Claude ecosystem
        "claude-code": {
            "block_method": "return_error",
            "error_format": "Security blocked: {reason}"
        },
        "superclaude": {
            "block_method": "return_error",
            "error_format": "[SuperClaude Shield] {reason}"
        },
        # Gemini ecosystem
        "gemini": {
            "block_method": "return_error",
            "error_format": "[Shield] {reason}"
        },
        "supergemini": {
            "block_method": "return_error",
            "error_format": "[SuperGemini Shield] {reason}"
        },
        # Qwen ecosystem
        "qwen": {
            "block_method": "return_error",
            "error_format": "[Shield] {reason}"
        },
        "superqwen": {
            "block_method": "return_error",
            "error_format": "[SuperQwen Shield] {reason}"
        },
        # Codex ecosystem
        "codex": {
            "block_method": "return_error",
            "error_format": "[Shield] {reason}"
        },
        "supercodex": {
            "block_method": "return_error",
            "error_format": "[SuperCodex Shield] {reason}"
        },
        # Popular IDE extensions
        "cursor": {
            "block_method": "reject_command", 
            "error_format": "[SENTINEL Shield] {reason}"
        },
        "windsurf": {
            "block_method": "reject_command",
            "error_format": "[Security] {reason}"
        },
        "continue": {
            "block_method": "return_error",
            "error_format": "Blocked by security policy: {reason}"
        },
        "cody": {
            "block_method": "return_error",
            "error_format": "[Shield] {reason}"
        },
        # OpenCode / heimdall
        "opencode": {
            "block_method": "return_error",
            "error_format": "[Heimdall] {reason}"
        },
        "generic": {
            "block_method": "return_error",
            "error_format": "Security: {reason}"
        }
    }
    
    def __init__(
        self,
        ide: str = "generic",
        on_block: Optional[Callable[[BlockAction], None]] = None
    ):
        """
        Initialize blocker.
        
        Args:
            ide: IDE context (claude-code, cursor, windsurf, etc.)
            on_block: Callback when block occurs
        """
        self.ide = ide.lower()
        self.on_block = on_block
        self.config = self.IDE_CONFIGS.get(self.ide, self.IDE_CONFIGS["generic"])
        
        self.blocked_count = 0
        self.blocked_history = []
    
    def block(self, command: str, reason: str, risk_score: float = 0.0) -> str:
        """
        Block a command and return error message.
        
        Args:
            command: The blocked command
            reason: Why it was blocked
            risk_score: Risk score that triggered block
            
        Returns:
            Formatted error message for the IDE
        """
        action = BlockAction(
            command=command,
            reason=reason,
            risk_score=risk_score,
            blocked=True
        )
        
        self.blocked_count += 1
        self.blocked_history.append(action)
        
        # Keep history limited
        if len(self.blocked_history) > 100:
            self.blocked_history.pop(0)
        
        # Call callback if set
        if self.on_block:
            try:
                self.on_block(action)
            except Exception as e:
                logger.error(f"Block callback error: {e}")
        
        logger.warning(f"Blocked {command}: {reason} (risk={risk_score:.2f})")
        
        # Format error for IDE
        return self.config["error_format"].format(reason=reason)
    
    def get_stats(self) -> dict:
        """Get block statistics."""
        return {
            "total_blocked": self.blocked_count,
            "recent_blocks": [
                {"command": b.command, "reason": b.reason}
                for b in self.blocked_history[-5:]
            ]
        }
