#!/usr/bin/env python3
"""
SENTINEL Brain — Security Detections MCP Client

Client for MHaggis/Security-Detections-MCP integration.
Enables AI-assisted detection engineering with Sigma, KQL, Splunk, Elastic rules.

Features:
- Search and query detection rules
- MITRE ATT&CK mapping
- CVE coverage analysis
- Detection gap identification

Reference: https://github.com/MHaggis/Security-Detections-MCP
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json


class DetectionSourceType(Enum):
    """Supported detection sources."""
    SIGMA = "sigma"
    SPLUNK_ESCU = "splunk_escu"
    ELASTIC = "elastic"
    KQL = "kql"


class SeverityLevel(Enum):
    """Detection severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DetectionRule:
    """Unified detection rule representation."""
    id: str
    title: str
    description: str
    source_type: str
    severity: str
    mitre_techniques: List[str] = field(default_factory=list)
    mitre_tactics: List[str] = field(default_factory=list)
    cves: List[str] = field(default_factory=list)
    logsource: Dict[str, str] = field(default_factory=dict)
    detection: Dict = field(default_factory=dict)
    raw_content: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "source_type": self.source_type,
            "severity": self.severity,
            "mitre_techniques": self.mitre_techniques,
            "mitre_tactics": self.mitre_tactics,
            "cves": self.cves,
            "logsource": self.logsource,
        }


@dataclass
class CoverageReport:
    """MITRE ATT&CK coverage analysis."""
    total_techniques: int
    covered_techniques: int
    coverage_percentage: float
    gaps: List[str] = field(default_factory=list)
    by_tactic: Dict[str, int] = field(default_factory=dict)


@dataclass
class MCPToolCall:
    """MCP tool call representation."""
    tool_name: str
    arguments: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps({
            "tool": self.tool_name,
            "arguments": self.arguments
        })


class SecurityDetectionsMCPClient:
    """Client for Security-Detections-MCP server.
    
    Provides Python interface to the MCP server for detection engineering.
    Can be used directly or as MCP tool calls for LLM integration.
    
    Example:
        client = SecurityDetectionsMCPClient()
        
        # Search for PowerShell detections
        rules = client.search("powershell", limit=10)
        
        # Get CVE coverage
        cve_rules = client.list_by_cve("CVE-2021-44228")
        
        # Analyze coverage gaps
        gaps = client.identify_gaps(["T1059", "T1055"])
    """
    
    # Available tools from Security-Detections-MCP
    AVAILABLE_TOOLS = [
        # Core Detection Tools
        "search",
        "get_by_id",
        "list_all",
        "list_by_source",
        "get_raw_yaml",
        "get_stats",
        "rebuild_index",
        
        # MITRE ATT&CK Filters
        "list_by_mitre",
        "list_by_mitre_tactic",
        
        # Vulnerability & Process Filters
        "list_by_cve",
        "list_by_process_name",
        "list_by_data_source",
        
        # Classification Filters
        "list_by_logsource",
        "list_by_severity",
        "list_by_detection_type",
        "list_by_analytic_story",
        
        # KQL-Specific Filters
        "list_by_kql_category",
        "list_by_kql_tag",
        "list_by_kql_datasource",
        
        # Story Tools
        "search_stories",
        "get_story",
        "list_stories",
        "list_stories_by_category",
        
        # Efficient Analysis Tools
        "analyze_coverage",
        "identify_gaps",
        "suggest_detections",
        "get_technique_ids",
        "generate_navigator_layer",
    ]
    
    def __init__(self, mcp_endpoint: Optional[str] = None):
        """Initialize MCP client.
        
        Args:
            mcp_endpoint: MCP server endpoint (optional, for direct calls)
        """
        self.endpoint = mcp_endpoint
        self._cache: Dict[str, Any] = {}
    
    # ==================== Core Detection Tools ====================
    
    def search(self, query: str, limit: int = 10) -> MCPToolCall:
        """Full-text search across all detections.
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="search",
            arguments={"query": query, "limit": limit}
        )
    
    def get_by_id(self, rule_id: str) -> MCPToolCall:
        """Get specific detection by ID.
        
        Args:
            rule_id: Detection rule ID
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="get_by_id",
            arguments={"id": rule_id}
        )
    
    def list_by_source(self, source_type: DetectionSourceType) -> MCPToolCall:
        """List detections by source type.
        
        Args:
            source_type: sigma, splunk_escu, elastic, or kql
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_source",
            arguments={"source_type": source_type.value}
        )
    
    def get_stats(self) -> MCPToolCall:
        """Get detection database statistics.
        
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="get_stats",
            arguments={}
        )
    
    # ==================== MITRE ATT&CK Filters ====================
    
    def list_by_mitre(self, technique_id: str) -> MCPToolCall:
        """List detections for a MITRE technique.
        
        Args:
            technique_id: MITRE ATT&CK technique ID (e.g., T1059.001)
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_mitre",
            arguments={"technique_id": technique_id}
        )
    
    def list_by_mitre_tactic(self, tactic: str) -> MCPToolCall:
        """List detections for a MITRE tactic.
        
        Args:
            tactic: MITRE tactic name (e.g., "execution", "persistence")
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_mitre_tactic",
            arguments={"tactic": tactic}
        )
    
    # ==================== Vulnerability Filters ====================
    
    def list_by_cve(self, cve_id: str) -> MCPToolCall:
        """List detections for a CVE.
        
        Args:
            cve_id: CVE identifier (e.g., CVE-2021-44228)
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_cve",
            arguments={"cve_id": cve_id}
        )
    
    def list_by_process_name(self, process_name: str) -> MCPToolCall:
        """List detections targeting a process.
        
        Args:
            process_name: Process name (e.g., "powershell.exe")
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_process_name",
            arguments={"process_name": process_name}
        )
    
    # ==================== KQL-Specific Filters ====================
    
    def list_by_kql_category(self, category: str) -> MCPToolCall:
        """List KQL queries by category.
        
        Args:
            category: KQL category (e.g., "Defender For Endpoint")
            
        Returns:
            MCPToolCall for execution
        """
        return MCPToolCall(
            tool_name="list_by_kql_category",
            arguments={"category": category}
        )
    
    # ==================== Efficient Analysis Tools ====================
    
    def analyze_coverage(
        self, 
        source_type: Optional[DetectionSourceType] = None
    ) -> MCPToolCall:
        """Analyze MITRE ATT&CK coverage.
        
        Args:
            source_type: Optional filter by source
            
        Returns:
            MCPToolCall for execution
        """
        args = {}
        if source_type:
            args["source_type"] = source_type.value
        
        return MCPToolCall(
            tool_name="analyze_coverage",
            arguments=args
        )
    
    def identify_gaps(
        self, 
        threat_profile: List[str],
        source_type: Optional[DetectionSourceType] = None
    ) -> MCPToolCall:
        """Identify detection gaps for threat profile.
        
        Args:
            threat_profile: List of MITRE technique IDs
            source_type: Optional filter by source
            
        Returns:
            MCPToolCall for execution
        """
        args = {"threat_profile": threat_profile}
        if source_type:
            args["source_type"] = source_type.value
        
        return MCPToolCall(
            tool_name="identify_gaps",
            arguments=args
        )
    
    def suggest_detections(
        self,
        technique_id: str,
        source_type: Optional[DetectionSourceType] = None
    ) -> MCPToolCall:
        """Suggest detections for a technique.
        
        Args:
            technique_id: MITRE technique ID
            source_type: Optional filter by source
            
        Returns:
            MCPToolCall for execution
        """
        args = {"technique_id": technique_id}
        if source_type:
            args["source_type"] = source_type.value
        
        return MCPToolCall(
            tool_name="suggest_detections",
            arguments=args
        )
    
    def generate_navigator_layer(
        self,
        name: str,
        source_type: Optional[DetectionSourceType] = None,
        tactic: Optional[str] = None
    ) -> MCPToolCall:
        """Generate MITRE ATT&CK Navigator layer.
        
        Args:
            name: Layer name
            source_type: Optional filter by source
            tactic: Optional filter by tactic
            
        Returns:
            MCPToolCall for execution
        """
        args = {"name": name}
        if source_type:
            args["source_type"] = source_type.value
        if tactic:
            args["tactic"] = tactic
        
        return MCPToolCall(
            tool_name="generate_navigator_layer",
            arguments=args
        )


# ==================== SENTINEL Integration ====================

class SENTINELDetectionBridge:
    """Bridge between SENTINEL Brain and Security Detections MCP.
    
    Provides SENTINEL-specific detection engineering workflows.
    
    Example:
        bridge = SENTINELDetectionBridge()
        
        # Convert R&D finding to detection query
        detections = bridge.find_detections_for_threat("CVE-2026-22812")
        
        # Map OWASP to MITRE and find gaps
        gaps = bridge.map_owasp_to_detections("LLM01")
    """
    
    # OWASP LLM Top 10 to MITRE ATT&CK mapping
    OWASP_TO_MITRE = {
        "LLM01": ["T1059", "T1203"],  # Prompt Injection → Execution
        "LLM02": ["T1552", "T1555"],  # Insecure Output → Credential Access
        "LLM03": ["T1195", "T1566"],  # Training Data Poisoning → Supply Chain
        "LLM04": ["T1499", "T1498"],  # DoS → Impact
        "LLM05": ["T1195.002"],       # Supply Chain
        "LLM06": ["T1530", "T1213"],  # Sensitive Info → Collection
        "LLM07": ["T1078"],           # Insecure Plugin → Valid Accounts
        "LLM08": ["T1078.004"],       # Excessive Agency
        "LLM09": ["T1566.001"],       # Overreliance → Phishing
        "LLM10": ["T1071"],           # Model Theft → C2
    }
    
    # OWASP Agentic AI Top 10 to MITRE
    OWASP_ASI_TO_MITRE = {
        "ASI01": ["T1059", "T1203"],  # Prompt Injection
        "ASI02": ["T1068", "T1548"],  # Sandbox Escape
        "ASI03": ["T1078", "T1134"],  # Identity/Privilege
        "ASI04": ["T1195"],           # Supply Chain
        "ASI05": ["T1059.006"],       # Unexpected Execution
        "ASI06": ["T1567"],           # Data Exfiltration
        "ASI07": ["T1543"],           # Persistence
        "ASI08": ["T1562"],           # Defense Evasion
        "ASI09": ["T1199"],           # Trust Exploitation
        "ASI10": ["T1486"],           # Untrusted Output
    }
    
    def __init__(self):
        self.mcp_client = SecurityDetectionsMCPClient()
    
    def find_detections_for_threat(self, threat_id: str) -> List[MCPToolCall]:
        """Find relevant detections for a threat.
        
        Args:
            threat_id: CVE, OWASP ID, or search term
            
        Returns:
            List of MCP tool calls to execute
        """
        calls = []
        
        # Check if CVE
        if threat_id.upper().startswith("CVE-"):
            calls.append(self.mcp_client.list_by_cve(threat_id))
        
        # Check if OWASP LLM
        elif threat_id.upper().startswith("LLM"):
            techniques = self.OWASP_TO_MITRE.get(threat_id.upper(), [])
            for tech in techniques:
                calls.append(self.mcp_client.list_by_mitre(tech))
        
        # Check if OWASP ASI
        elif threat_id.upper().startswith("ASI"):
            techniques = self.OWASP_ASI_TO_MITRE.get(threat_id.upper(), [])
            for tech in techniques:
                calls.append(self.mcp_client.list_by_mitre(tech))
        
        # Generic search
        else:
            calls.append(self.mcp_client.search(threat_id))
        
        return calls
    
    def map_owasp_to_detections(self, owasp_id: str) -> MCPToolCall:
        """Map OWASP category to detection gap analysis.
        
        Args:
            owasp_id: OWASP ID (LLM01-10 or ASI01-10)
            
        Returns:
            MCPToolCall for gap analysis
        """
        owasp_upper = owasp_id.upper()
        
        if owasp_upper.startswith("LLM"):
            techniques = self.OWASP_TO_MITRE.get(owasp_upper, [])
        elif owasp_upper.startswith("ASI"):
            techniques = self.OWASP_ASI_TO_MITRE.get(owasp_upper, [])
        else:
            techniques = []
        
        return self.mcp_client.identify_gaps(techniques)
    
    def generate_sentinel_detections(
        self,
        source: str = "sigma"
    ) -> MCPToolCall:
        """Generate detection coverage analysis for SENTINEL.
        
        Args:
            source: Detection source type
            
        Returns:
            MCPToolCall for coverage analysis
        """
        source_type = DetectionSourceType(source)
        return self.mcp_client.analyze_coverage(source_type)
    
    def search_ai_security_detections(self) -> List[MCPToolCall]:
        """Search for AI-security specific detections.
        
        Returns:
            List of MCP tool calls for AI security searches
        """
        ai_terms = [
            "llm",
            "ai model",
            "machine learning",
            "prompt injection",
            "langchain",
            "openai",
            "anthropic",
        ]
        
        return [
            self.mcp_client.search(term, limit=5)
            for term in ai_terms
        ]
