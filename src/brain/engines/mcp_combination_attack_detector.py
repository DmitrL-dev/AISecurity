"""
MCP Combination Attack Detector — SENTINEL R&D Jan 2026

Detects combination attacks using multiple MCP servers together.

Attack pattern from HiddenLayer research:
1. User downloads document via Fetch MCP
2. Document contains prompt injection
3. Injection uses already-granted Filesystem permissions
4. Data exfiltrated via URL encoding to attacker webhook

The key insight: individual MCP servers seem safe, but
COMBINATIONS create attack surfaces that are hard to reason about.

Dangerous combinations:
- Fetch + Filesystem = data exfiltration without code execution
- Slack + Filesystem = social engineering + data theft
- GitHub + Filesystem = code injection + secrets exposure

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
from collections import defaultdict

logger = logging.getLogger("MCPCombinationAttackDetector")


class MCPServerCategory(str, Enum):
    """Categories of MCP servers by capability."""
    DATA_SOURCE = "data_source"       # Can read private data
    EXTERNAL_FETCH = "external_fetch"  # Can fetch external content
    COMMUNICATION = "communication"    # Can send data out
    EXECUTION = "execution"            # Can execute code
    STORAGE = "storage"                # Can write/store data


class CombinationThreat(str, Enum):
    """Types of combination attack threats."""
    DATA_EXFILTRATION = "data_exfiltration"
    PROMPT_INJECTION_CHAIN = "prompt_injection_chain"
    PERMISSION_ESCALATION = "permission_escalation"
    INDIRECT_CODE_EXECUTION = "indirect_code_execution"
    CREDENTIAL_THEFT = "credential_theft"


@dataclass
class MCPServerUsage:
    """Tracks usage of an MCP server in a session."""
    server_name: str
    category: MCPServerCategory
    tools_used: List[str] = field(default_factory=list)
    first_used: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    call_count: int = 0
    permissions_granted: Set[str] = field(default_factory=set)


@dataclass
class CombinationAttackResult:
    """Result of combination attack analysis."""
    is_suspicious: bool = False
    risk_score: float = 0.0
    detected_threats: List[CombinationThreat] = field(default_factory=list)
    dangerous_combinations: List[Tuple[str, str]] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class MCPCombinationAttackDetector:
    """
    Detects attacks that combine multiple MCP servers.
    
    Key insight: Permission granted for one action can be reused
    by a prompt injection to perform different actions.
    """
    
    # MCP server categorization
    SERVER_CATEGORIES = {
        # Data sources
        "filesystem": MCPServerCategory.DATA_SOURCE,
        "postgres": MCPServerCategory.DATA_SOURCE,
        "sqlite": MCPServerCategory.DATA_SOURCE,
        "google-drive": MCPServerCategory.DATA_SOURCE,
        "dropbox": MCPServerCategory.DATA_SOURCE,
        "s3": MCPServerCategory.DATA_SOURCE,
        "memory": MCPServerCategory.DATA_SOURCE,
        
        # External fetch
        "fetch": MCPServerCategory.EXTERNAL_FETCH,
        "brave-search": MCPServerCategory.EXTERNAL_FETCH,
        "puppeteer": MCPServerCategory.EXTERNAL_FETCH,
        "web": MCPServerCategory.EXTERNAL_FETCH,
        "browser": MCPServerCategory.EXTERNAL_FETCH,
        
        # Communication
        "slack": MCPServerCategory.COMMUNICATION,
        "discord": MCPServerCategory.COMMUNICATION,
        "gmail": MCPServerCategory.COMMUNICATION,
        "email": MCPServerCategory.COMMUNICATION,
        "webhook": MCPServerCategory.COMMUNICATION,
        "github": MCPServerCategory.COMMUNICATION,
        "gitlab": MCPServerCategory.COMMUNICATION,
        
        # Execution
        "terminal": MCPServerCategory.EXECUTION,
        "shell": MCPServerCategory.EXECUTION,
        "docker": MCPServerCategory.EXECUTION,
        "kubernetes": MCPServerCategory.EXECUTION,
    }
    
    # Dangerous server combinations
    DANGEROUS_COMBINATIONS = [
        # (category1, category2, threat_type, risk_multiplier)
        (MCPServerCategory.EXTERNAL_FETCH, MCPServerCategory.DATA_SOURCE,
         CombinationThreat.PROMPT_INJECTION_CHAIN, 1.5),
        
        (MCPServerCategory.DATA_SOURCE, MCPServerCategory.COMMUNICATION,
         CombinationThreat.DATA_EXFILTRATION, 2.0),
        
        (MCPServerCategory.EXTERNAL_FETCH, MCPServerCategory.COMMUNICATION,
         CombinationThreat.DATA_EXFILTRATION, 1.8),
        
        (MCPServerCategory.EXTERNAL_FETCH, MCPServerCategory.EXECUTION,
         CombinationThreat.INDIRECT_CODE_EXECUTION, 2.5),
        
        (MCPServerCategory.DATA_SOURCE, MCPServerCategory.EXECUTION,
         CombinationThreat.CREDENTIAL_THEFT, 2.2),
    ]
    
    # URL encoding patterns that might indicate exfiltration
    EXFILTRATION_PATTERNS = [
        r'[?&]data=',
        r'[?&]content=',
        r'[?&]file=',
        r'[?&]secret=',
        r'[?&]key=',
        r'[?&]token=',
        r'[?&]password=',
        r'[?&]credential=',
        r'base64[=,]',
        r'%[0-9A-Fa-f]{2}.*%[0-9A-Fa-f]{2}.*%[0-9A-Fa-f]{2}',  # Heavy URL encoding
    ]
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.sessions: Dict[str, Dict[str, MCPServerUsage]] = defaultdict(dict)
        self.exfil_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.EXFILTRATION_PATTERNS
        ]
        logger.info("MCPCombinationAttackDetector initialized")
    
    def start_session(self, session_id: str) -> None:
        """Start tracking a new session."""
        self.sessions[session_id] = {}
        logger.info(f"Started MCP tracking session: {session_id}")
    
    def end_session(self, session_id: str) -> Optional[Dict]:
        """End a session and return final analysis."""
        session_data = self.sessions.pop(session_id, None)
        if session_data:
            logger.info(
                f"Ended session {session_id}: "
                f"{len(session_data)} servers used"
            )
        return session_data
    
    def record_server_usage(
        self,
        session_id: str,
        server_name: str,
        tool_name: str,
        permissions: Optional[Set[str]] = None
    ) -> CombinationAttackResult:
        """
        Record that an MCP server was used and check for dangerous combinations.
        
        Args:
            session_id: Session identifier
            server_name: Name of MCP server
            tool_name: Specific tool called
            permissions: Permissions granted (optional)
            
        Returns:
            CombinationAttackResult with any detected threats
        """
        # Get or create session
        if session_id not in self.sessions:
            self.start_session(session_id)
        
        session = self.sessions[session_id]
        
        # Determine category
        server_lower = server_name.lower()
        category = MCPServerCategory.DATA_SOURCE  # default
        for known, cat in self.SERVER_CATEGORIES.items():
            if known in server_lower:
                category = cat
                break
        
        # Update or create server usage record
        if server_name not in session:
            session[server_name] = MCPServerUsage(
                server_name=server_name,
                category=category
            )
        
        usage = session[server_name]
        usage.tools_used.append(tool_name)
        usage.call_count += 1
        usage.last_used = time.time()
        if permissions:
            usage.permissions_granted.update(permissions)
        
        # Analyze combinations
        return self.analyze_session(session_id)
    
    def analyze_session(self, session_id: str) -> CombinationAttackResult:
        """
        Analyze current session for dangerous MCP combinations.
        
        Returns:
            CombinationAttackResult with threats and recommendations
        """
        session = self.sessions.get(session_id, {})
        
        if len(session) < 2:
            return CombinationAttackResult()
        
        result = CombinationAttackResult()
        categories_used: Set[MCPServerCategory] = set()
        servers_by_category: Dict[MCPServerCategory, List[str]] = defaultdict(list)
        
        # Group servers by category
        for server_name, usage in session.items():
            categories_used.add(usage.category)
            servers_by_category[usage.category].append(server_name)
        
        # Check for dangerous combinations
        risk_score = 0.0
        
        for cat1, cat2, threat, multiplier in self.DANGEROUS_COMBINATIONS:
            if cat1 in categories_used and cat2 in categories_used:
                result.detected_threats.append(threat)
                
                # Record specific server combinations
                for s1 in servers_by_category[cat1]:
                    for s2 in servers_by_category[cat2]:
                        result.dangerous_combinations.append((s1, s2))
                
                risk_score += 30.0 * multiplier
                result.indicators.append(
                    f"{cat1.value} + {cat2.value} = {threat.value} risk"
                )
        
        # Check for the classic Fetch + Filesystem pattern
        has_fetch = MCPServerCategory.EXTERNAL_FETCH in categories_used
        has_data = MCPServerCategory.DATA_SOURCE in categories_used
        has_comm = MCPServerCategory.COMMUNICATION in categories_used
        
        if has_fetch and has_data:
            result.indicators.append(
                "CLASSIC PATTERN: External fetch + data access. "
                "Prompt injection in fetched content can read files."
            )
            risk_score += 20.0
        
        if has_data and has_comm:
            result.indicators.append(
                "EXFILTRATION RISK: Data access + communication. "
                "Data can be sent to external services."
            )
            risk_score += 25.0
        
        # Triple threat: all three
        if has_fetch and has_data and has_comm:
            result.indicators.append(
                "CRITICAL: Fetch + Data + Communication. "
                "Complete attack chain possible!"
            )
            risk_score += 30.0
        
        result.risk_score = min(100.0, risk_score)
        result.is_suspicious = result.risk_score >= 30.0
        
        # Generate recommendations
        result.recommendations = self._generate_recommendations(
            categories_used, result.risk_score
        )
        
        if result.is_suspicious:
            logger.warning(
                f"Session {session_id}: Dangerous MCP combination detected! "
                f"Risk score: {result.risk_score:.0f}"
            )
        
        return result
    
    def check_exfiltration_url(self, url: str) -> Tuple[bool, List[str]]:
        """
        Check if a URL looks like it's being used for data exfiltration.
        
        Returns:
            (is_suspicious, matched_patterns)
        """
        matches = []
        
        for pattern in self.exfil_patterns:
            if pattern.search(url):
                matches.append(pattern.pattern)
        
        is_suspicious = len(matches) > 0
        
        if is_suspicious:
            logger.warning(f"Potential exfiltration URL: {url[:100]}...")
        
        return is_suspicious, matches
    
    def _generate_recommendations(
        self,
        categories: Set[MCPServerCategory],
        risk_score: float
    ) -> List[str]:
        """Generate recommendations based on categories used."""
        recommendations = []
        
        if risk_score >= 70:
            recommendations.append(
                "CRITICAL: Review all MCP server permissions immediately"
            )
            recommendations.append(
                "Consider reducing number of concurrent MCP servers"
            )
        
        if MCPServerCategory.EXTERNAL_FETCH in categories:
            recommendations.append(
                "Validate all fetched content before processing"
            )
            recommendations.append(
                "Consider content sandboxing for external data"
            )
        
        if MCPServerCategory.COMMUNICATION in categories:
            recommendations.append(
                "Implement output filtering for communication tools"
            )
            recommendations.append(
                "Add human approval for external sends"
            )
        
        if MCPServerCategory.EXECUTION in categories:
            recommendations.append(
                "Use containerized execution environments"
            )
            recommendations.append(
                "Implement command allowlisting"
            )
        
        return recommendations
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of MCP usage in a session."""
        session = self.sessions.get(session_id, {})
        
        return {
            "session_id": session_id,
            "servers_used": len(session),
            "servers": [
                {
                    "name": usage.server_name,
                    "category": usage.category.value,
                    "call_count": usage.call_count,
                    "tools": usage.tools_used[:10],  # Limit for summary
                }
                for usage in session.values()
            ]
        }


# ============================================================================
# Factory
# ============================================================================

_detector: Optional[MCPCombinationAttackDetector] = None


def get_mcp_combination_detector() -> MCPCombinationAttackDetector:
    """Get singleton detector."""
    global _detector
    if _detector is None:
        _detector = MCPCombinationAttackDetector()
    return _detector


def create_engine(config: Optional[Dict[str, Any]] = None) -> MCPCombinationAttackDetector:
    """Factory function for analyzer integration."""
    return MCPCombinationAttackDetector(config)


# === Unit Tests ===
if __name__ == "__main__":
    detector = MCPCombinationAttackDetector()
    
    print("=== Test 1: Single Server (Safe) ===")
    detector.start_session("session_1")
    result = detector.record_server_usage("session_1", "filesystem", "read_file")
    print(f"Is Suspicious: {result.is_suspicious}")
    print(f"Risk Score: {result.risk_score}")
    print()
    
    print("=== Test 2: Fetch + Filesystem (Dangerous) ===")
    detector.start_session("session_2")
    detector.record_server_usage("session_2", "fetch", "download_url")
    result = detector.record_server_usage("session_2", "filesystem", "read_file")
    print(f"Is Suspicious: {result.is_suspicious}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Threats: {[t.value for t in result.detected_threats]}")
    print(f"Indicators: {result.indicators}")
    print()
    
    print("=== Test 3: Triple Threat ===")
    detector.start_session("session_3")
    detector.record_server_usage("session_3", "fetch", "get_url")
    detector.record_server_usage("session_3", "filesystem", "read_file")
    result = detector.record_server_usage("session_3", "slack", "send_message")
    print(f"Is Suspicious: {result.is_suspicious}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Dangerous Combinations: {result.dangerous_combinations}")
    print(f"Recommendations: {result.recommendations}")
    print()
    
    print("=== Test 4: Exfiltration URL Detection ===")
    urls = [
        "https://webhook.site/abc?data=sensitive_content",
        "https://example.com/page",
        "https://evil.com/collect?token=abc123&secret=xyz",
        "https://legit.com/api/save",
    ]
    for url in urls:
        is_sus, patterns = detector.check_exfiltration_url(url)
        print(f"URL: {url[:50]}... | Suspicious: {is_sus}")
