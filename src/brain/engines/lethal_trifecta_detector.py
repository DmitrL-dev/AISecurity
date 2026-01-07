"""
Lethal Trifecta Detector — SENTINEL R&D Jan 2026

Detects agents vulnerable to the "Lethal Trifecta" pattern.

The Lethal Trifecta (Promptfoo/HiddenLayer research):
An AI agent is fundamentally insecure if it has ALL THREE:
1. Access to Private Data (files, credentials, PII)
2. Exposure to Untrusted Content (user input, external data)
3. Ability to Externally Communicate (network, email, webhooks)

If your system meets all three criteria, no guardrails can fully protect it.

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum

logger = logging.getLogger("LethalTrifectaDetector")


class TrifectaCapability(str, Enum):
    """The three lethal capabilities."""
    PRIVATE_DATA_ACCESS = "private_data_access"
    UNTRUSTED_CONTENT = "untrusted_content"
    EXTERNAL_COMMUNICATION = "external_communication"


class RiskLevel(str, Enum):
    """Risk levels based on capability combinations."""
    SAFE = "safe"           # 0 capabilities
    LOW = "low"             # 1 capability
    MODERATE = "moderate"   # 2 capabilities
    LETHAL = "lethal"       # ALL 3 capabilities


@dataclass
class AgentCapabilities:
    """Describes an agent's capabilities for trifecta analysis."""
    agent_id: str
    
    # Private Data Access indicators
    can_read_files: bool = False
    can_read_database: bool = False
    can_access_credentials: bool = False
    can_access_pii: bool = False
    can_read_environment: bool = False
    
    # Untrusted Content Exposure indicators
    accepts_user_input: bool = False
    processes_external_urls: bool = False
    reads_external_files: bool = False
    uses_rag_with_external_docs: bool = False
    processes_emails: bool = False
    
    # External Communication indicators
    can_make_http_requests: bool = False
    can_send_emails: bool = False
    can_use_webhooks: bool = False
    can_execute_shell: bool = False
    can_access_network: bool = False


@dataclass
class TrifectaResult:
    """Result of lethal trifecta analysis."""
    agent_id: str
    risk_level: RiskLevel
    risk_score: float  # 0-100
    
    has_private_data_access: bool = False
    has_untrusted_content: bool = False
    has_external_communication: bool = False
    
    private_data_indicators: List[str] = field(default_factory=list)
    untrusted_content_indicators: List[str] = field(default_factory=list)
    external_comm_indicators: List[str] = field(default_factory=list)
    
    recommendations: List[str] = field(default_factory=list)
    is_lethal: bool = False


class LethalTrifectaDetector:
    """
    Detects the Lethal Trifecta pattern in AI agents.
    
    If an agent has ALL THREE capabilities, it cannot be fully secured
    through guardrails alone — deterministic limitations are required.
    """
    
    # Tool names that indicate each capability
    PRIVATE_DATA_TOOLS = {
        "read_file", "read_files", "list_directory", "list_dir",
        "get_file", "file_read", "filesystem", "read_database",
        "query_db", "sql_query", "get_credentials", "read_env",
        "environment", "get_secret", "read_config", "grep", "find"
    }
    
    UNTRUSTED_CONTENT_TOOLS = {
        "fetch", "fetch_url", "web_search", "browse", "browser",
        "read_url", "download", "get_webpage", "scrape", "rag_query",
        "search_documents", "read_email", "get_messages", "slack_read",
        "discord_read", "user_input", "chat"
    }
    
    EXTERNAL_COMM_TOOLS = {
        "http_request", "post", "put", "delete", "send_email",
        "webhook", "notify", "send_message", "slack_send", "discord_send",
        "bash", "shell", "execute", "run_command", "terminal",
        "ssh", "scp", "curl", "wget", "api_call", "push_files"
    }
    
    # MCP servers with high-risk capabilities
    HIGH_RISK_MCP_SERVERS = {
        "filesystem": TrifectaCapability.PRIVATE_DATA_ACCESS,
        "postgres": TrifectaCapability.PRIVATE_DATA_ACCESS,
        "sqlite": TrifectaCapability.PRIVATE_DATA_ACCESS,
        "google-drive": TrifectaCapability.PRIVATE_DATA_ACCESS,
        "fetch": TrifectaCapability.UNTRUSTED_CONTENT,
        "brave-search": TrifectaCapability.UNTRUSTED_CONTENT,
        "puppeteer": TrifectaCapability.UNTRUSTED_CONTENT,
        "gmail": TrifectaCapability.EXTERNAL_COMMUNICATION,
        "slack": TrifectaCapability.EXTERNAL_COMMUNICATION,
        "github": TrifectaCapability.EXTERNAL_COMMUNICATION,
    }
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        logger.info("LethalTrifectaDetector initialized")
    
    def analyze_capabilities(self, caps: AgentCapabilities) -> TrifectaResult:
        """
        Analyze agent capabilities for lethal trifecta pattern.
        
        Returns:
            TrifectaResult with risk assessment
        """
        private_indicators = []
        untrusted_indicators = []
        external_indicators = []
        
        # Check Private Data Access
        if caps.can_read_files:
            private_indicators.append("File system read access")
        if caps.can_read_database:
            private_indicators.append("Database read access")
        if caps.can_access_credentials:
            private_indicators.append("Credential access")
        if caps.can_access_pii:
            private_indicators.append("PII data access")
        if caps.can_read_environment:
            private_indicators.append("Environment variable access")
        
        # Check Untrusted Content
        if caps.accepts_user_input:
            untrusted_indicators.append("Accepts user input")
        if caps.processes_external_urls:
            untrusted_indicators.append("Processes external URLs")
        if caps.reads_external_files:
            untrusted_indicators.append("Reads external files")
        if caps.uses_rag_with_external_docs:
            untrusted_indicators.append("RAG with external documents")
        if caps.processes_emails:
            untrusted_indicators.append("Processes emails")
        
        # Check External Communication
        if caps.can_make_http_requests:
            external_indicators.append("HTTP request capability")
        if caps.can_send_emails:
            external_indicators.append("Email sending capability")
        if caps.can_use_webhooks:
            external_indicators.append("Webhook capability")
        if caps.can_execute_shell:
            external_indicators.append("Shell execution")
        if caps.can_access_network:
            external_indicators.append("Network access")
        
        # Determine capabilities present
        has_private = len(private_indicators) > 0
        has_untrusted = len(untrusted_indicators) > 0
        has_external = len(external_indicators) > 0
        
        # Count capabilities
        capability_count = sum([has_private, has_untrusted, has_external])
        
        # Determine risk level
        if capability_count == 3:
            risk_level = RiskLevel.LETHAL
            risk_score = 100.0
        elif capability_count == 2:
            risk_level = RiskLevel.MODERATE
            risk_score = 60.0
        elif capability_count == 1:
            risk_level = RiskLevel.LOW
            risk_score = 30.0
        else:
            risk_level = RiskLevel.SAFE
            risk_score = 0.0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            has_private, has_untrusted, has_external, risk_level
        )
        
        result = TrifectaResult(
            agent_id=caps.agent_id,
            risk_level=risk_level,
            risk_score=risk_score,
            has_private_data_access=has_private,
            has_untrusted_content=has_untrusted,
            has_external_communication=has_external,
            private_data_indicators=private_indicators,
            untrusted_content_indicators=untrusted_indicators,
            external_comm_indicators=external_indicators,
            recommendations=recommendations,
            is_lethal=(risk_level == RiskLevel.LETHAL)
        )
        
        if result.is_lethal:
            logger.warning(
                f"LETHAL TRIFECTA detected for agent {caps.agent_id}! "
                f"All three vulnerability conditions present."
            )
        
        return result
    
    def analyze_tools(
        self,
        agent_id: str,
        tools: List[str]
    ) -> TrifectaResult:
        """
        Analyze a list of tool names for lethal trifecta pattern.
        
        Args:
            agent_id: Agent identifier
            tools: List of tool names available to the agent
            
        Returns:
            TrifectaResult with risk assessment
        """
        tool_set = {t.lower() for t in tools}
        
        caps = AgentCapabilities(agent_id=agent_id)
        
        # Check for private data tools
        private_matches = tool_set & self.PRIVATE_DATA_TOOLS
        if private_matches:
            caps.can_read_files = True
        
        # Check for untrusted content tools
        untrusted_matches = tool_set & self.UNTRUSTED_CONTENT_TOOLS
        if untrusted_matches:
            caps.processes_external_urls = True
            caps.accepts_user_input = True
        
        # Check for external communication tools
        external_matches = tool_set & self.EXTERNAL_COMM_TOOLS
        if external_matches:
            caps.can_make_http_requests = True
            if "bash" in tool_set or "shell" in tool_set or "execute" in tool_set:
                caps.can_execute_shell = True
        
        return self.analyze_capabilities(caps)
    
    def analyze_mcp_servers(
        self,
        agent_id: str,
        mcp_servers: List[str]
    ) -> TrifectaResult:
        """
        Analyze MCP servers for lethal trifecta pattern.
        
        Args:
            agent_id: Agent identifier
            mcp_servers: List of MCP server names
            
        Returns:
            TrifectaResult with risk assessment
        """
        caps = AgentCapabilities(agent_id=agent_id)
        
        for server in mcp_servers:
            server_lower = server.lower()
            
            # Check known high-risk servers
            for known, capability in self.HIGH_RISK_MCP_SERVERS.items():
                if known in server_lower:
                    if capability == TrifectaCapability.PRIVATE_DATA_ACCESS:
                        caps.can_read_files = True
                    elif capability == TrifectaCapability.UNTRUSTED_CONTENT:
                        caps.processes_external_urls = True
                    elif capability == TrifectaCapability.EXTERNAL_COMMUNICATION:
                        caps.can_make_http_requests = True
        
        return self.analyze_capabilities(caps)
    
    def _generate_recommendations(
        self,
        has_private: bool,
        has_untrusted: bool,
        has_external: bool,
        risk_level: RiskLevel
    ) -> List[str]:
        """Generate recommendations based on risk level."""
        recommendations = []
        
        if risk_level == RiskLevel.LETHAL:
            recommendations.append(
                "CRITICAL: Lethal Trifecta detected. "
                "No guardrails can fully secure this configuration."
            )
            recommendations.append(
                "Remove at least ONE capability: private data, "
                "untrusted content, or external communication"
            )
            recommendations.append(
                "Implement deterministic output filtering"
            )
            recommendations.append(
                "Add human-in-the-loop approval for all external actions"
            )
        
        elif risk_level == RiskLevel.MODERATE:
            recommendations.append(
                "HIGH RISK: Two trifecta conditions present. "
                "Adding the third would create lethal vulnerability."
            )
            
            if not has_private:
                recommendations.append(
                    "DO NOT add file/database access without removing "
                    "external communication"
                )
            if not has_untrusted:
                recommendations.append(
                    "DO NOT process external content without removing "
                    "external communication"
                )
            if not has_external:
                recommendations.append(
                    "DO NOT add network/email capability without "
                    "removing data access"
                )
        
        elif risk_level == RiskLevel.LOW:
            recommendations.append(
                "MODERATE RISK: One trifecta condition present. "
                "Monitor for capability creep."
            )
        
        return recommendations


# ============================================================================
# Factory
# ============================================================================

_detector: Optional[LethalTrifectaDetector] = None


def get_lethal_trifecta_detector() -> LethalTrifectaDetector:
    """Get singleton detector."""
    global _detector
    if _detector is None:
        _detector = LethalTrifectaDetector()
    return _detector


def create_engine(config: Optional[Dict[str, Any]] = None) -> LethalTrifectaDetector:
    """Factory function for analyzer integration."""
    return LethalTrifectaDetector(config)


# === Unit Tests ===
if __name__ == "__main__":
    detector = LethalTrifectaDetector()
    
    print("=== Test 1: Safe Agent (no capabilities) ===")
    caps = AgentCapabilities(agent_id="safe_agent")
    result = detector.analyze_capabilities(caps)
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Is Lethal: {result.is_lethal}")
    print()
    
    print("=== Test 2: Moderate Risk (2 capabilities) ===")
    caps = AgentCapabilities(
        agent_id="moderate_agent",
        can_read_files=True,
        can_make_http_requests=True
    )
    result = detector.analyze_capabilities(caps)
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Recommendations: {result.recommendations}")
    print()
    
    print("=== Test 3: LETHAL TRIFECTA ===")
    caps = AgentCapabilities(
        agent_id="lethal_agent",
        can_read_files=True,
        can_access_credentials=True,
        accepts_user_input=True,
        processes_external_urls=True,
        can_make_http_requests=True,
        can_execute_shell=True
    )
    result = detector.analyze_capabilities(caps)
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Is Lethal: {result.is_lethal}")
    print(f"Private Data: {result.private_data_indicators}")
    print(f"Untrusted: {result.untrusted_content_indicators}")
    print(f"External: {result.external_comm_indicators}")
    print(f"Recommendations: {result.recommendations}")
    print()
    
    print("=== Test 4: Tool Analysis ===")
    tools = ["read_file", "fetch", "bash", "grep"]
    result = detector.analyze_tools("tool_agent", tools)
    print(f"Tools: {tools}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Is Lethal: {result.is_lethal}")
    print()
    
    print("=== Test 5: MCP Server Analysis ===")
    servers = ["filesystem", "fetch", "slack"]
    result = detector.analyze_mcp_servers("mcp_agent", servers)
    print(f"MCP Servers: {servers}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Is Lethal: {result.is_lethal}")
