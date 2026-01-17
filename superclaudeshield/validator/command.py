# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Command Validator - validates SuperClaude slash commands
"""

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    risk_score: float
    issues: List[str] = field(default_factory=list)
    sanitized_params: Dict[str, Any] = field(default_factory=dict)


class CommandValidator:
    """
    Validates SuperClaude slash command parameters.
    
    Checks for:
    - Shell injection in parameters
    - Path traversal attempts
    - Dangerous URL patterns
    - Code injection in strings
    """
    
    # All 30 SuperClaude commands
    VALID_COMMANDS = {
        # Planning & Design
        "/brainstorm", "/design", "/estimate", "/spec-panel",
        # Development
        "/implement", "/build", "/improve", "/cleanup", "/explain",
        # Testing & Quality
        "/test", "/analyze", "/troubleshoot", "/reflect",
        # Documentation
        "/document", "/help",
        # Version Control
        "/git",
        # Project Management
        "/pm", "/task", "/workflow",
        # Research & Analysis
        "/research", "/business-panel",
        # Utilities
        "/agent", "/index-repo", "/index", "/recommend",
        "/select-tool", "/spawn", "/load", "/save", "/sc",
    }
    
    # Commands that can be disabled via config
    DISABLEABLE_COMMANDS = {"/spawn", "/agent"}
    
    # Dangerous patterns in parameters
    SHELL_INJECTION_PATTERNS = [
        r';\s*\w+',              # Command chaining
        r'\|\s*\w+',             # Pipe to command
        r'`[^`]+`',              # Backtick execution
        r'\$\([^)]+\)',          # $() substitution
        r'&&\s*\w+',             # AND chaining
        r'\|\|\s*\w+',           # OR chaining
        r'>\s*/\w+',             # Redirect to absolute path
        r'<\s*/\w+',             # Input from absolute path
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\.[/\\]',            # Parent directory
        r'/etc/',                # System directories
        r'/proc/',
        r'/sys/',
        r'C:\\Windows',
        r'C:\\System32',
        r'%systemroot%',
        r'%windir%',
    ]
    
    DANGEROUS_URL_PATTERNS = [
        r'file://',              # Local file access
        r'javascript:',          # JavaScript injection
        r'data:',                # Data URI
        r'127\.0\.0\.',          # Localhost
        r'localhost',
        r'169\.254\.169\.254',   # AWS metadata
        r'metadata\.google',     # GCP metadata
        r'\[::1\]',              # IPv6 localhost
        r'0\.0\.0\.0',
    ]
    
    CODE_INJECTION_PATTERNS = [
        r'eval\s*\(',
        r'exec\s*\(',
        r'__import__',
        r'subprocess\.',
        r'os\.system',
        r'os\.popen',
        r'Popen\s*\(',
    ]
    
    def __init__(self, disabled_commands: Optional[Set[str]] = None):
        """
        Initialize validator.
        
        Args:
            disabled_commands: Set of commands to block entirely
        """
        self.disabled_commands = disabled_commands or set()
        
        # Compile all patterns
        self._shell_patterns = [re.compile(p, re.IGNORECASE) for p in self.SHELL_INJECTION_PATTERNS]
        self._path_patterns = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        self._url_patterns = [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_URL_PATTERNS]
        self._code_patterns = [re.compile(p, re.IGNORECASE) for p in self.CODE_INJECTION_PATTERNS]
    
    def validate(self, command: str, params: Dict[str, Any]) -> ValidationResult:
        """
        Validate a slash command and its parameters.
        
        Args:
            command: The slash command (e.g., "/research")
            params: Command parameters
            
        Returns:
            ValidationResult with issues found
        """
        issues = []
        risk_score = 0.0
        sanitized = {}
        
        # 1. Check command is valid
        if command not in self.VALID_COMMANDS:
            issues.append(f"Unknown command: {command}")
            risk_score = 1.0
            return ValidationResult(False, risk_score, issues)
        
        # 2. Check command is not disabled
        if command in self.disabled_commands:
            issues.append(f"Command disabled by policy: {command}")
            risk_score = 0.8
            return ValidationResult(False, risk_score, issues)
        
        # 3. Validate each parameter
        for key, value in params.items():
            if isinstance(value, str):
                param_issues, param_risk = self._validate_string_param(key, value)
                issues.extend(param_issues)
                risk_score = max(risk_score, param_risk)
                
                # Sanitize if issues found
                if param_issues:
                    sanitized[key] = self._sanitize(value)
                else:
                    sanitized[key] = value
            else:
                sanitized[key] = value
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            risk_score=risk_score,
            issues=issues,
            sanitized_params=sanitized
        )
    
    def _validate_string_param(self, key: str, value: str) -> tuple:
        """Validate a string parameter."""
        issues = []
        risk_score = 0.0
        
        # Shell injection
        for pattern in self._shell_patterns:
            if pattern.search(value):
                issues.append(f"Shell injection in '{key}': {pattern.pattern}")
                risk_score = max(risk_score, 0.9)
        
        # Path traversal
        for pattern in self._path_patterns:
            if pattern.search(value):
                issues.append(f"Path traversal in '{key}': {pattern.pattern}")
                risk_score = max(risk_score, 0.8)
        
        # URL validation (for research commands, URLs are expected)
        for pattern in self._url_patterns:
            if pattern.search(value):
                issues.append(f"Dangerous URL in '{key}': {pattern.pattern}")
                risk_score = max(risk_score, 0.7)
        
        # Code injection
        for pattern in self._code_patterns:
            if pattern.search(value):
                issues.append(f"Code injection in '{key}': {pattern.pattern}")
                risk_score = max(risk_score, 0.95)
        
        return issues, risk_score
    
    def _sanitize(self, value: str) -> str:
        """Sanitize a string value by removing dangerous patterns."""
        result = value
        
        # Remove shell metacharacters
        dangerous_chars = [';', '|', '`', '$', '&', '>', '<']
        for char in dangerous_chars:
            result = result.replace(char, '')
        
        # Remove path traversal
        result = re.sub(r'\.\.+[/\\]', '', result)
        
        return result
    
    def is_high_risk_command(self, command: str) -> bool:
        """Check if command is considered high risk."""
        high_risk = {"/spawn", "/implement", "/build", "/research", "/agent"}
        return command in high_risk
