# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Sequential Tool Attack Chaining (STAC) Detector - P1 Security Engine

Detects multi-step attack patterns where individually benign tool calls
collectively cause harm when executed in sequence.

Based on:
- OWASP Agentic Top 10 2026 (ASI02: Tool Misuse)
- TTPs.ai Sequential Attack patterns
- HiddenLayer multi-step attack research

Attack Pattern Examples:
1. Read credentials file → Make HTTP request (exfil)
2. List environment → Create file with exploit
3. Search for secrets → Call external API (leak)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ToolCategory(Enum):
    """Categories of tool capabilities."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_REQUEST = "network_request"
    SYSTEM_COMMAND = "system_command"
    DATABASE_QUERY = "database_query"
    CREDENTIALS_ACCESS = "credentials_access"
    ENVIRONMENT_ACCESS = "environment_access"
    CODE_EXECUTION = "code_execution"
    SEARCH_QUERY = "search_query"
    MEMORY_ACCESS = "memory_access"
    UNKNOWN = "unknown"


@dataclass
class ToolCall:
    """Represents a single tool call in a sequence."""
    tool_name: str
    category: ToolCategory
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[float] = None
    description: str = ""


@dataclass
class AttackChain:
    """Represents a detected attack chain."""
    chain_type: str
    tools_involved: List[str]
    confidence: float
    severity: str
    description: str
    mitre_mapping: Optional[str] = None


@dataclass
class STACDetectorResult:
    """Result from STAC detection."""
    is_attack_chain: bool
    chains_detected: List[AttackChain] = field(default_factory=list)
    risk_score: float = 0.0
    highest_severity: str = "LOW"
    tool_sequence: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class STACDetector:
    """
    Detects Sequential Tool Attack Chaining patterns.
    
    Monitors sequences of tool calls to identify patterns where
    benign individual calls combine to form malicious behavior.
    """
    
    # Tool name to category mapping
    TOOL_CATEGORIES = {
        # File operations
        "read_file": ToolCategory.FILE_READ,
        "view_file": ToolCategory.FILE_READ,
        "cat": ToolCategory.FILE_READ,
        "get_file_content": ToolCategory.FILE_READ,
        "file_read": ToolCategory.FILE_READ,
        
        "write_file": ToolCategory.FILE_WRITE,
        "create_file": ToolCategory.FILE_WRITE,
        "save_file": ToolCategory.FILE_WRITE,
        "write_to_file": ToolCategory.FILE_WRITE,
        "append_file": ToolCategory.FILE_WRITE,
        
        "delete_file": ToolCategory.FILE_DELETE,
        "remove_file": ToolCategory.FILE_DELETE,
        "rm": ToolCategory.FILE_DELETE,
        
        # Network operations
        "http_request": ToolCategory.NETWORK_REQUEST,
        "fetch": ToolCategory.NETWORK_REQUEST,
        "curl": ToolCategory.NETWORK_REQUEST,
        "wget": ToolCategory.NETWORK_REQUEST,
        "api_call": ToolCategory.NETWORK_REQUEST,
        "send_request": ToolCategory.NETWORK_REQUEST,
        "post_data": ToolCategory.NETWORK_REQUEST,
        "webhook": ToolCategory.NETWORK_REQUEST,
        
        # System operations
        "run_command": ToolCategory.SYSTEM_COMMAND,
        "execute": ToolCategory.SYSTEM_COMMAND,
        "shell": ToolCategory.SYSTEM_COMMAND,
        "terminal": ToolCategory.SYSTEM_COMMAND,
        "bash": ToolCategory.SYSTEM_COMMAND,
        "exec": ToolCategory.SYSTEM_COMMAND,
        
        # Database
        "query": ToolCategory.DATABASE_QUERY,
        "sql_query": ToolCategory.DATABASE_QUERY,
        "database_read": ToolCategory.DATABASE_QUERY,
        
        # Credentials
        "get_credentials": ToolCategory.CREDENTIALS_ACCESS,
        "read_secrets": ToolCategory.CREDENTIALS_ACCESS,
        "vault_read": ToolCategory.CREDENTIALS_ACCESS,
        "get_api_key": ToolCategory.CREDENTIALS_ACCESS,
        
        # Environment
        "get_env": ToolCategory.ENVIRONMENT_ACCESS,
        "environment": ToolCategory.ENVIRONMENT_ACCESS,
        "list_env": ToolCategory.ENVIRONMENT_ACCESS,
        
        # Code execution
        "eval": ToolCategory.CODE_EXECUTION,
        "python_exec": ToolCategory.CODE_EXECUTION,
        "code_interpreter": ToolCategory.CODE_EXECUTION,
        
        # Search
        "search": ToolCategory.SEARCH_QUERY,
        "grep": ToolCategory.SEARCH_QUERY,
        "find": ToolCategory.SEARCH_QUERY,
        "codebase_search": ToolCategory.SEARCH_QUERY,
        
        # Memory
        "memory_read": ToolCategory.MEMORY_ACCESS,
        "get_context": ToolCategory.MEMORY_ACCESS,
        "retrieve_memory": ToolCategory.MEMORY_ACCESS,
    }
    
    # Dangerous sequential patterns: (first_category, second_category) -> attack_type
    ATTACK_PATTERNS = {
        # Data exfiltration patterns
        (ToolCategory.FILE_READ, ToolCategory.NETWORK_REQUEST): {
            "type": "data_exfiltration",
            "severity": "CRITICAL",
            "description": "File read followed by network request - potential data exfiltration",
            "mitre": "T1041"  # Exfiltration Over C2 Channel
        },
        (ToolCategory.CREDENTIALS_ACCESS, ToolCategory.NETWORK_REQUEST): {
            "type": "credential_theft",
            "severity": "CRITICAL", 
            "description": "Credentials access followed by network request - credential exfiltration",
            "mitre": "T1552"  # Unsecured Credentials
        },
        (ToolCategory.DATABASE_QUERY, ToolCategory.NETWORK_REQUEST): {
            "type": "database_exfiltration",
            "severity": "CRITICAL",
            "description": "Database query followed by network request - data exfiltration",
            "mitre": "T1213"  # Data from Information Repositories
        },
        (ToolCategory.ENVIRONMENT_ACCESS, ToolCategory.NETWORK_REQUEST): {
            "type": "env_exfiltration",
            "severity": "HIGH",
            "description": "Environment access followed by network request - secrets exfiltration",
            "mitre": "T1552.001"  # Credentials In Files
        },
        (ToolCategory.MEMORY_ACCESS, ToolCategory.NETWORK_REQUEST): {
            "type": "memory_exfiltration",
            "severity": "HIGH",
            "description": "Memory access followed by network request - context exfiltration",
            "mitre": "T1005"  # Data from Local System
        },
        
        # Persistence patterns
        (ToolCategory.NETWORK_REQUEST, ToolCategory.FILE_WRITE): {
            "type": "payload_download",
            "severity": "CRITICAL",
            "description": "Network request followed by file write - payload download",
            "mitre": "T1105"  # Ingress Tool Transfer
        },
        (ToolCategory.CODE_EXECUTION, ToolCategory.FILE_WRITE): {
            "type": "malware_creation",
            "severity": "CRITICAL",
            "description": "Code execution followed by file write - malware creation",
            "mitre": "T1027"  # Obfuscated Files or Information
        },
        
        # Reconnaissance + action patterns
        (ToolCategory.SEARCH_QUERY, ToolCategory.FILE_READ): {
            "type": "targeted_file_access",
            "severity": "MEDIUM",
            "description": "Search followed by file read - targeted sensitive file access",
            "mitre": "T1083"  # File and Directory Discovery
        },
        (ToolCategory.SEARCH_QUERY, ToolCategory.CREDENTIALS_ACCESS): {
            "type": "credential_hunting",
            "severity": "HIGH",
            "description": "Search followed by credentials access - credential hunting",
            "mitre": "T1552"  # Unsecured Credentials
        },
        
        # Destructive patterns
        (ToolCategory.FILE_READ, ToolCategory.FILE_DELETE): {
            "type": "data_destruction",
            "severity": "HIGH",
            "description": "File read followed by delete - potential data destruction after exfil",
            "mitre": "T1485"  # Data Destruction
        },
        (ToolCategory.SYSTEM_COMMAND, ToolCategory.NETWORK_REQUEST): {
            "type": "command_result_exfil",
            "severity": "HIGH",
            "description": "System command followed by network request - command output exfiltration",
            "mitre": "T1059"  # Command and Scripting Interpreter
        },
    }
    
    # Three-step attack chains
    THREE_STEP_PATTERNS = {
        (ToolCategory.SEARCH_QUERY, ToolCategory.FILE_READ, ToolCategory.NETWORK_REQUEST): {
            "type": "reconnaissance_exfiltration",
            "severity": "CRITICAL",
            "description": "Search → Read → Exfiltrate chain detected",
            "mitre": "T1087"  # Account Discovery
        },
        (ToolCategory.NETWORK_REQUEST, ToolCategory.CODE_EXECUTION, ToolCategory.FILE_WRITE): {
            "type": "remote_code_persistence",
            "severity": "CRITICAL",
            "description": "Download → Execute → Persist chain detected",
            "mitre": "T1059"  # Command and Scripting Interpreter
        },
        (ToolCategory.CREDENTIALS_ACCESS, ToolCategory.DATABASE_QUERY, ToolCategory.NETWORK_REQUEST): {
            "type": "privileged_data_theft",
            "severity": "CRITICAL",
            "description": "Credentials → Query → Exfiltrate chain detected",
            "mitre": "T1078"  # Valid Accounts
        },
    }
    
    def __init__(self, window_size: int = 10):
        """
        Initialize STAC detector.
        
        Args:
            window_size: Number of recent tool calls to analyze
        """
        self.window_size = window_size
        self.tool_history: List[ToolCall] = []
    
    def categorize_tool(self, tool_name: str) -> ToolCategory:
        """Categorize a tool by its name."""
        tool_lower = tool_name.lower().replace("-", "_").replace(" ", "_")
        
        # Direct match
        if tool_lower in self.TOOL_CATEGORIES:
            return self.TOOL_CATEGORIES[tool_lower]
        
        # Partial match
        for known_tool, category in self.TOOL_CATEGORIES.items():
            if known_tool in tool_lower or tool_lower in known_tool:
                return category
        
        # Keyword-based heuristics
        if any(kw in tool_lower for kw in ["read", "get", "view", "cat", "show"]):
            if any(kw in tool_lower for kw in ["file", "content", "document"]):
                return ToolCategory.FILE_READ
        if any(kw in tool_lower for kw in ["write", "save", "create", "append"]):
            return ToolCategory.FILE_WRITE
        if any(kw in tool_lower for kw in ["http", "request", "fetch", "curl", "api", "webhook"]):
            return ToolCategory.NETWORK_REQUEST
        if any(kw in tool_lower for kw in ["run", "exec", "shell", "command", "bash"]):
            return ToolCategory.SYSTEM_COMMAND
        if any(kw in tool_lower for kw in ["cred", "secret", "key", "password", "token"]):
            return ToolCategory.CREDENTIALS_ACCESS
        if any(kw in tool_lower for kw in ["env", "environment", "config"]):
            return ToolCategory.ENVIRONMENT_ACCESS
        if any(kw in tool_lower for kw in ["search", "find", "grep", "query"]):
            return ToolCategory.SEARCH_QUERY
        
        return ToolCategory.UNKNOWN
    
    def add_tool_call(self, tool_name: str, parameters: Optional[Dict] = None):
        """
        Add a tool call to history and analyze.
        
        Args:
            tool_name: Name of the tool being called
            parameters: Tool parameters (optional)
        """
        category = self.categorize_tool(tool_name)
        tool_call = ToolCall(
            tool_name=tool_name,
            category=category,
            parameters=parameters or {}
        )
        
        self.tool_history.append(tool_call)
        
        # Maintain window size
        if len(self.tool_history) > self.window_size:
            self.tool_history.pop(0)
    
    def analyze_sequence(self, tools: Optional[List[str]] = None) -> STACDetectorResult:
        """
        Analyze tool sequence for attack chains.
        
        Args:
            tools: Optional list of tool names to analyze. If None, uses history.
            
        Returns:
            STACDetectorResult with findings
        """
        if tools:
            self.tool_history = [
                ToolCall(t, self.categorize_tool(t)) for t in tools
            ]
        
        if len(self.tool_history) < 2:
            return STACDetectorResult(
                is_attack_chain=False,
                tool_sequence=[t.tool_name for t in self.tool_history]
            )
        
        chains_detected: List[AttackChain] = []
        
        # Check two-step patterns
        for i in range(len(self.tool_history) - 1):
            cat1 = self.tool_history[i].category
            cat2 = self.tool_history[i + 1].category
            
            pattern_key = (cat1, cat2)
            if pattern_key in self.ATTACK_PATTERNS:
                pattern = self.ATTACK_PATTERNS[pattern_key]
                chains_detected.append(AttackChain(
                    chain_type=pattern["type"],
                    tools_involved=[
                        self.tool_history[i].tool_name,
                        self.tool_history[i + 1].tool_name
                    ],
                    confidence=0.85,
                    severity=pattern["severity"],
                    description=pattern["description"],
                    mitre_mapping=pattern.get("mitre")
                ))
        
        # Check three-step patterns
        for i in range(len(self.tool_history) - 2):
            cat1 = self.tool_history[i].category
            cat2 = self.tool_history[i + 1].category
            cat3 = self.tool_history[i + 2].category
            
            pattern_key = (cat1, cat2, cat3)
            if pattern_key in self.THREE_STEP_PATTERNS:
                pattern = self.THREE_STEP_PATTERNS[pattern_key]
                chains_detected.append(AttackChain(
                    chain_type=pattern["type"],
                    tools_involved=[
                        self.tool_history[i].tool_name,
                        self.tool_history[i + 1].tool_name,
                        self.tool_history[i + 2].tool_name
                    ],
                    confidence=0.95,
                    severity=pattern["severity"],
                    description=pattern["description"],
                    mitre_mapping=pattern.get("mitre")
                ))
        
        # Calculate overall results
        is_attack = len(chains_detected) > 0
        risk_score = self._calculate_risk_score(chains_detected)
        highest_severity = self._get_highest_severity(chains_detected)
        recommendations = self._generate_recommendations(chains_detected)
        
        return STACDetectorResult(
            is_attack_chain=is_attack,
            chains_detected=chains_detected,
            risk_score=risk_score,
            highest_severity=highest_severity,
            tool_sequence=[t.tool_name for t in self.tool_history],
            recommendations=recommendations
        )
    
    def _calculate_risk_score(self, chains: List[AttackChain]) -> float:
        """Calculate overall risk score."""
        if not chains:
            return 0.0
        
        severity_scores = {
            "CRITICAL": 1.0,
            "HIGH": 0.75,
            "MEDIUM": 0.5,
            "LOW": 0.25
        }
        
        total_score = sum(
            severity_scores.get(c.severity, 0.5) * c.confidence
            for c in chains
        )
        
        return min(1.0, total_score / 2.0)
    
    def _get_highest_severity(self, chains: List[AttackChain]) -> str:
        """Get highest severity from chains."""
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for severity in severity_order:
            if any(c.severity == severity for c in chains):
                return severity
        return "LOW"
    
    def _generate_recommendations(self, chains: List[AttackChain]) -> List[str]:
        """Generate security recommendations."""
        recommendations = []
        chain_types = set(c.chain_type for c in chains)
        
        if any("exfil" in ct for ct in chain_types):
            recommendations.extend([
                "Block network requests that include sensitive file contents",
                "Implement data loss prevention (DLP) for AI agent outputs",
                "Require human approval for network requests after file reads"
            ])
        
        if any("credential" in ct for ct in chain_types):
            recommendations.extend([
                "Isolate credential access from network operations",
                "Implement credential access logging and alerting",
                "Use credential vaulting with time-limited access"
            ])
        
        if any("download" in ct or "payload" in ct for ct in chain_types):
            recommendations.extend([
                "Sandbox file writes from network downloads",
                "Implement allowlist for download domains",
                "Scan written files for malicious content"
            ])
        
        if any("destruction" in ct for ct in chain_types):
            recommendations.extend([
                "Implement soft-delete with recovery period",
                "Require human approval for file deletions",
                "Maintain immutable audit logs"
            ])
        
        return list(set(recommendations))[:5]
    
    def reset(self):
        """Clear tool history."""
        self.tool_history = []


# Convenience functions for Brain integration
def analyze_tool_sequence(tools: List[str]) -> Dict[str, Any]:
    """
    Analyze a sequence of tool calls for attack chains.
    
    Args:
        tools: List of tool names in order of execution
        
    Returns:
        Dictionary with analysis results
    """
    detector = STACDetector()
    result = detector.analyze_sequence(tools)
    
    return {
        "is_attack_chain": result.is_attack_chain,
        "risk_score": result.risk_score,
        "highest_severity": result.highest_severity,
        "chain_count": len(result.chains_detected),
        "chains": [
            {
                "type": c.chain_type,
                "tools": c.tools_involved,
                "confidence": c.confidence,
                "severity": c.severity,
                "description": c.description,
                "mitre": c.mitre_mapping
            }
            for c in result.chains_detected
        ],
        "tool_sequence": result.tool_sequence,
        "recommendations": result.recommendations
    }


def create_stac_monitor() -> STACDetector:
    """Create a STAC detector instance for continuous monitoring."""
    return STACDetector()
