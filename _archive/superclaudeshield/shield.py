# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Main Shield class - orchestrates all security components
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
import logging
import functools

logger = logging.getLogger(__name__)


class ShieldMode(Enum):
    """Security enforcement modes."""
    STRICT = "strict"      # Block all suspicious activity
    MODERATE = "moderate"  # Block high-risk, warn on medium
    PERMISSIVE = "permissive"  # Warn only, log everything


@dataclass
class ShieldResult:
    """Result of security check."""
    is_safe: bool
    risk_score: float
    threats: List[str] = field(default_factory=list)
    blocked: bool = False
    reason: str = ""
    recommendations: List[str] = field(default_factory=list)


class Shield:
    """
    Main security wrapper for SuperClaude Framework.
    
    Orchestrates:
    - Command validation
    - Agent monitoring
    - MCP protection
    - Injection detection
    """
    
    # SuperClaude command categories
    COMMAND_CATEGORIES = {
        "planning": ["/brainstorm", "/design", "/estimate", "/spec-panel"],
        "development": ["/implement", "/build", "/improve", "/cleanup", "/explain"],
        "testing": ["/test", "/analyze", "/troubleshoot", "/reflect"],
        "documentation": ["/document", "/help"],
        "git": ["/git"],
        "project": ["/pm", "/task", "/workflow"],
        "research": ["/research", "/business-panel"],
        "utilities": ["/agent", "/index-repo", "/index", "/recommend", 
                     "/select-tool", "/spawn", "/load", "/save", "/sc"],
    }
    
    # High-risk commands requiring extra scrutiny
    HIGH_RISK_COMMANDS = ["/spawn", "/implement", "/build", "/research", "/agent"]
    
    def __init__(
        self,
        mode: ShieldMode = ShieldMode.MODERATE,
        config: Optional[Dict] = None,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize Shield.
        
        Args:
            mode: Security enforcement mode
            config: Optional configuration dict
            alert_callback: Optional callback for security alerts
        """
        self.mode = mode
        self.config = config or {}
        self.alert_callback = alert_callback
        
        # Initialize components (lazy loading)
        self._command_validator = None
        self._injection_analyzer = None
        self._agent_analyzer = None
        self._mcp_guard = None
        self._blocker = None
        
        # Statistics
        self.stats = {
            "commands_checked": 0,
            "commands_blocked": 0,
            "threats_detected": 0,
        }
        
        logger.info(f"SuperClaude Shield initialized in {mode.value} mode")
    
    @property
    def command_validator(self):
        if self._command_validator is None:
            from .validator.command import CommandValidator
            self._command_validator = CommandValidator()
        return self._command_validator
    
    @property
    def injection_analyzer(self):
        if self._injection_analyzer is None:
            from .analyzer.injection import InjectionAnalyzer
            self._injection_analyzer = InjectionAnalyzer()
        return self._injection_analyzer
    
    @property
    def agent_analyzer(self):
        if self._agent_analyzer is None:
            from .analyzer.agent_chain import AgentChainAnalyzer
            self._agent_analyzer = AgentChainAnalyzer()
        return self._agent_analyzer
    
    @property
    def mcp_guard(self):
        if self._mcp_guard is None:
            from .analyzer.mcp_flow import MCPGuard
            self._mcp_guard = MCPGuard()
        return self._mcp_guard
    
    def validate_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> ShieldResult:
        """
        Validate a SuperClaude slash command.
        
        Args:
            command: The slash command (e.g., "/research")
            params: Command parameters
            
        Returns:
            ShieldResult with safety assessment
        """
        self.stats["commands_checked"] += 1
        params = params or {}
        threats = []
        risk_score = 0.0
        
        # 1. Validate command syntax and parameters
        cmd_result = self.command_validator.validate(command, params)
        if not cmd_result.is_valid:
            threats.extend(cmd_result.issues)
            risk_score = max(risk_score, cmd_result.risk_score)
        
        # 2. Check for injection attacks in parameters
        for key, value in params.items():
            if isinstance(value, str):
                inj_result = self.injection_analyzer.analyze(value)
                if inj_result.detected:
                    threats.append(f"Injection in param '{key}': {inj_result.attack_type}")
                    risk_score = max(risk_score, inj_result.risk_score)
        
        # 3. High-risk command extra checks
        if command in self.HIGH_RISK_COMMANDS:
            risk_score += 0.1  # Base risk increase
        
        # 4. Determine if safe based on mode
        is_safe, blocked, reason = self._apply_policy(risk_score, threats)
        
        if blocked:
            self.stats["commands_blocked"] += 1
            self._send_alert(command, params, threats)
        
        if threats:
            self.stats["threats_detected"] += len(threats)
        
        return ShieldResult(
            is_safe=is_safe,
            risk_score=risk_score,
            threats=threats,
            blocked=blocked,
            reason=reason,
            recommendations=self._get_recommendations(threats)
        )
    
    def validate_agent_sequence(self, agents: List[str]) -> ShieldResult:
        """
        Validate a sequence of agent invocations.
        
        Args:
            agents: List of agent names in order of invocation
            
        Returns:
            ShieldResult with chain analysis
        """
        result = self.agent_analyzer.analyze(agents)
        
        is_safe, blocked, reason = self._apply_policy(
            result.risk_score,
            result.chains if result.is_attack else []
        )
        
        return ShieldResult(
            is_safe=is_safe,
            risk_score=result.risk_score,
            threats=[c.description for c in result.chains] if hasattr(result, 'chains') else [],
            blocked=blocked,
            reason=reason
        )
    
    def validate_mcp_call(
        self,
        mcp_name: str,
        operation: str,
        params: Dict[str, Any]
    ) -> ShieldResult:
        """
        Validate an MCP server call.
        
        Args:
            mcp_name: Name of MCP server (e.g., "tavily", "playwright")
            operation: Operation being performed
            params: Call parameters
            
        Returns:
            ShieldResult with MCP analysis
        """
        result = self.mcp_guard.validate(mcp_name, operation, params)
        
        is_safe, blocked, reason = self._apply_policy(
            result.risk_score,
            result.issues
        )
        
        return ShieldResult(
            is_safe=is_safe,
            risk_score=result.risk_score,
            threats=result.issues,
            blocked=blocked,
            reason=reason
        )
    
    def _apply_policy(
        self,
        risk_score: float,
        threats: List
    ) -> tuple:
        """Apply security policy based on mode."""
        
        if self.mode == ShieldMode.STRICT:
            if risk_score > 0.3 or threats:
                return False, True, f"Blocked: risk={risk_score:.2f}, threats={len(threats)}"
            return True, False, ""
        
        elif self.mode == ShieldMode.MODERATE:
            if risk_score > 0.6:
                return False, True, f"High risk blocked: {risk_score:.2f}"
            if threats:
                return True, False, "Warning: threats detected but allowed"
            return True, False, ""
        
        else:  # PERMISSIVE
            return True, False, "Logged only" if threats else ""
    
    def _send_alert(self, command: str, params: Dict, threats: List):
        """Send security alert."""
        alert = {
            "command": command,
            "params": params,
            "threats": threats,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }
        
        logger.warning(f"Security alert: {alert}")
        
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _get_recommendations(self, threats: List[str]) -> List[str]:
        """Generate recommendations based on threats."""
        recommendations = []
        
        if any("injection" in t.lower() for t in threats):
            recommendations.append("Sanitize user input before passing to commands")
        if any("path" in t.lower() for t in threats):
            recommendations.append("Use absolute paths within project directory")
        if any("url" in t.lower() for t in threats):
            recommendations.append("Validate URLs against allowlist")
        
        return recommendations
    
    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with Shield validation.
        
        Usage:
            @shield.protect
            def handle_command(command, params):
                ...
        """
        @functools.wraps(func)
        def wrapper(command: str, params: Optional[Dict] = None, *args, **kwargs):
            result = self.validate_command(command, params)
            
            if result.blocked:
                raise SecurityError(f"Blocked by Shield: {result.reason}")
            
            if not result.is_safe:
                logger.warning(f"Proceeding with warnings: {result.threats}")
            
            return func(command, params, *args, **kwargs)
        
        return wrapper
    
    def get_stats(self) -> Dict[str, int]:
        """Get security statistics."""
        return self.stats.copy()


class SecurityError(Exception):
    """Raised when Shield blocks an operation."""
    pass
