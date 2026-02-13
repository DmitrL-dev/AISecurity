# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Audit Logger - comprehensive security audit logging
"""

import logging
import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """Audit log entry."""
    timestamp: str
    event_type: str  # command, agent, mcp, injection
    ide: str
    details: Dict[str, Any]
    result: str  # allowed, blocked, warned
    risk_score: float


class AuditLogger:
    """
    Comprehensive audit logging for SuperClaude Shield.
    
    Logs all security-relevant events for:
    - Compliance reporting
    - Security analysis
    - Forensics
    """
    
    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_entries: int = 10000,
        ide: str = "generic"
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for log files
            max_entries: Max entries to keep in memory
            ide: IDE context
        """
        self.log_dir = Path(log_dir) if log_dir else None
        self.max_entries = max_entries
        self.ide = ide
        
        self.entries: List[AuditEntry] = []
        
        # Create log directory
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_command(
        self,
        command: str,
        params: Dict[str, Any],
        result: str,
        risk_score: float,
        issues: List[str] = None
    ):
        """Log a command execution."""
        self._log(
            event_type="command",
            details={
                "command": command,
                "params": self._sanitize_params(params),
                "issues": issues or []
            },
            result=result,
            risk_score=risk_score
        )
    
    def log_agent(
        self,
        agent_name: str,
        action: str,
        result: str,
        risk_score: float
    ):
        """Log agent activity."""
        self._log(
            event_type="agent",
            details={
                "agent": agent_name,
                "action": action
            },
            result=result,
            risk_score=risk_score
        )
    
    def log_mcp(
        self,
        mcp_name: str,
        operation: str,
        target: str,
        result: str,
        risk_score: float
    ):
        """Log MCP interaction."""
        self._log(
            event_type="mcp",
            details={
                "mcp": mcp_name,
                "operation": operation,
                "target": target
            },
            result=result,
            risk_score=risk_score
        )
    
    def log_injection(
        self,
        attack_type: str,
        source: str,
        patterns: List[str],
        result: str,
        risk_score: float
    ):
        """Log injection attempt."""
        self._log(
            event_type="injection",
            details={
                "attack_type": attack_type,
                "source": source,
                "patterns": patterns[:3]
            },
            result=result,
            risk_score=risk_score
        )
    
    def _log(
        self,
        event_type: str,
        details: Dict,
        result: str,
        risk_score: float
    ):
        """Internal logging method."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            ide=self.ide,
            details=details,
            result=result,
            risk_score=risk_score
        )
        
        self.entries.append(entry)
        
        # Trim if over limit
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        
        # Write to file if configured
        if self.log_dir:
            self._write_to_file(entry)
        
        # Also log to standard logger
        level = logging.WARNING if result == "blocked" else logging.DEBUG
        logger.log(level, f"Audit: {event_type} - {result} (risk={risk_score:.2f})")
    
    def _write_to_file(self, entry: AuditEntry):
        """Write entry to daily log file."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit_{date_str}.jsonl"
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")
        except Exception as e:
            logger.error(f"Audit write failed: {e}")
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """Sanitize params for logging (remove sensitive data)."""
        sanitized = {}
        sensitive_keys = {"password", "token", "key", "secret", "credential"}
        
        for key, value in params.items():
            if any(s in key.lower() for s in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            else:
                sanitized[key] = value
        
        return sanitized
    
    def get_summary(self, hours: int = 24) -> Dict:
        """Get summary of recent activity."""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        recent = [
            e for e in self.entries
            if datetime.fromisoformat(e.timestamp) > cutoff
        ]
        
        return {
            "total_events": len(recent),
            "blocked": sum(1 for e in recent if e.result == "blocked"),
            "by_type": {
                t: sum(1 for e in recent if e.event_type == t)
                for t in ["command", "agent", "mcp", "injection"]
            },
            "avg_risk": sum(e.risk_score for e in recent) / len(recent) if recent else 0
        }
    
    def export(self, filepath: str):
        """Export all entries to file."""
        with open(filepath, "w") as f:
            for entry in self.entries:
                f.write(json.dumps(asdict(entry)) + "\n")
