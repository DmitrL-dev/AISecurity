"""
Sleeper Agent Detector

Detects dormant malicious code patterns that activate under specific conditions:
- Date/time-based triggers
- Environment-based triggers  
- Version-based triggers
- Counter/threshold triggers

Based on Anthropic's "Sleeper Agents" research (2024).

Auto-generated from R&D: emerging_threats_research.md
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    DATE_BASED = "date_based"
    ENV_BASED = "environment"
    VERSION_BASED = "version"
    COUNTER_BASED = "counter"
    NETWORK_BASED = "network"
    USER_BASED = "user"


@dataclass
class SleeperTrigger:
    """Individual sleeper trigger finding."""
    trigger_type: TriggerType
    pattern: str
    line_number: Optional[int]
    context: str
    severity: str  # critical, high, medium
    explanation: str


@dataclass
class SleeperDetectionResult:
    """Complete sleeper agent detection result."""
    detected: bool
    confidence: float
    triggers: List[SleeperTrigger] = field(default_factory=list)
    is_likely_sleeper: bool = False


class SleeperAgentDetector:
    """
    Detects sleeper agent patterns in code and AI outputs.
    
    Sleeper agents are trained to behave normally until a specific
    trigger condition is met, then exhibit malicious behavior.
    """

    # Date/time-based triggers (most common)
    DATE_TRIGGERS = [
        (r"(?:if|when)\s+(?:\w+\.)?(?:year|get_?year)\s*[><=!]+\s*20\d{2}", 
         "Year comparison trigger"),
        (r"datetime\.now\(\)\.year\s*[><=!]+\s*20\d{2}",
         "Current year check"),
        (r"(?:date|time)\.(?:today|now)\(\).*20\d{2}",
         "Date comparison with year"),
        (r"strftime.*%Y.*[><=].*20\d{2}",
         "Formatted date comparison"),
        (r"(?:after|before)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}",
         "Natural language date trigger"),
        (r"(?:month|day)\s*[><=!]+\s*\d{1,2}",
         "Month/day numeric trigger"),
    ]

    # Environment-based triggers
    ENV_TRIGGERS = [
        (r"os\.environ\.get\s*\(['\"](?:PROD|PRODUCTION|LIVE|DEPLOY)",
         "Production environment check"),
        (r"os\.getenv\s*\(['\"](?:ENV|ENVIRONMENT|NODE_ENV|FLASK_ENV)",
         "Environment variable check"),
        (r"(?:if|when)\s+(?:production|deployed?|live|staging)",
         "Natural deployment check"),
        (r"\.(?:is_production|is_deployed|is_live)\s*\(",
         "Deployment flag method"),
        (r"DEBUG\s*[!=]=\s*(?:False|0|None)",
         "Debug mode disabled check"),
        (r"os\.name\s*==\s*['\"](?:nt|posix)",
         "OS-specific trigger"),
    ]

    # Version-based triggers
    VERSION_TRIGGERS = [
        (r"(?:version|__version__|VERSION)\s*[><=!]+\s*['\"]?\d+\.\d+",
         "Version comparison"),
        (r"sys\.version_info\s*[><=]",
         "Python version check"),
        (r"platform\.(?:python_version|release)\(\)",
         "Platform version retrieval"),
        (r"(?:v|version)?\s*[><=]\s*['\"]?[0-9]+\.[0-9]+",
         "Generic version comparison"),
    ]

    # Counter/threshold triggers
    COUNTER_TRIGGERS = [
        (r"(?:count|counter|calls?|invocations?)\s*[><=]+\s*\d{2,}",
         "Execution counter threshold"),
        (r"(?:if|when)\s+\w+\s*%\s*\d+\s*==\s*0",
         "Modulo-based trigger (every Nth)"),
        (r"random\.(?:random|uniform|randint)\s*\(\)\s*[<>]",
         "Probabilistic trigger"),
        (r"(?:attempts?|retries?|failures?)\s*[><=]+\s*\d+",
         "Failure counter trigger"),
    ]

    # Network-based triggers
    NETWORK_TRIGGERS = [
        (r"(?:if|when)\s+(?:can_)?(?:reach|ping|connect)\s*\(",
         "Network connectivity check"),
        (r"socket\.(?:create_connection|connect)\s*\([^)]+\)\s*(?:except|catch)",
         "Connection attempt trigger"),
        (r"requests\.(?:get|head)\s*\(['\"][^'\"]+['\"].*(?:timeout|except)",
         "HTTP availability check"),
        (r"dns\.resolver|socket\.gethostbyname",
         "DNS resolution trigger"),
    ]

    # User-based triggers  
    USER_TRIGGERS = [
        (r"(?:user|username|user_id)\s*[!=]=\s*['\"][^'\"]+['\"]",
         "Specific user check"),
        (r"os\.getlogin\(\)\s*==|getpass\.getuser\(\)",
         "Current user check"),
        (r"(?:admin|root|superuser)\s+in\s+\w+\.(?:roles?|groups?)",
         "Admin role check"),
        (r"is_(?:admin|superuser|staff)\s*\(",
         "Privilege level check"),
    ]

    # Behavioral indicators (what happens after trigger)
    MALICIOUS_ACTIONS = [
        (r"exec\s*\(|eval\s*\(", "Code execution"),
        (r"os\.system\s*\(|subprocess\.(?:run|call|Popen)", "Shell execution"),
        (r"open\s*\([^)]+['\"]w['\"]", "File write"),
        (r"requests\.(?:post|put)\s*\(", "Data exfiltration"),
        (r"base64\.(?:b64decode|decode)", "Encoded payload"),
        (r"__import__\s*\(|importlib\.import_module", "Dynamic import"),
        (r"compile\s*\([^)]+exec", "Runtime compilation"),
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all patterns."""
        self._date_compiled = [(re.compile(p, re.I), d) for p, d in self.DATE_TRIGGERS]
        self._env_compiled = [(re.compile(p, re.I), d) for p, d in self.ENV_TRIGGERS]
        self._version_compiled = [(re.compile(p, re.I), d) for p, d in self.VERSION_TRIGGERS]
        self._counter_compiled = [(re.compile(p, re.I), d) for p, d in self.COUNTER_TRIGGERS]
        self._network_compiled = [(re.compile(p, re.I), d) for p, d in self.NETWORK_TRIGGERS]
        self._user_compiled = [(re.compile(p, re.I), d) for p, d in self.USER_TRIGGERS]
        self._malicious_compiled = [(re.compile(p, re.I), d) for p, d in self.MALICIOUS_ACTIONS]

    def detect(self, content: str, filename: str = "") -> SleeperDetectionResult:
        """
        Detect sleeper agent patterns in content.
        
        Args:
            content: Code or text to analyze
            filename: Optional filename for context
            
        Returns:
            SleeperDetectionResult with findings
        """
        triggers: List[SleeperTrigger] = []
        lines = content.split('\n')

        # Scan for trigger patterns by category
        triggers.extend(self._scan_category(
            lines, self._date_compiled, TriggerType.DATE_BASED, "critical"
        ))
        triggers.extend(self._scan_category(
            lines, self._env_compiled, TriggerType.ENV_BASED, "high"
        ))
        triggers.extend(self._scan_category(
            lines, self._version_compiled, TriggerType.VERSION_BASED, "medium"
        ))
        triggers.extend(self._scan_category(
            lines, self._counter_compiled, TriggerType.COUNTER_BASED, "medium"
        ))
        triggers.extend(self._scan_category(
            lines, self._network_compiled, TriggerType.NETWORK_BASED, "medium"
        ))
        triggers.extend(self._scan_category(
            lines, self._user_compiled, TriggerType.USER_BASED, "high"
        ))

        # Check for malicious actions after triggers
        has_malicious = self._check_malicious_actions(content)

        # Calculate confidence and sleeper likelihood
        confidence, is_sleeper = self._assess_sleeper_likelihood(triggers, has_malicious)

        return SleeperDetectionResult(
            detected=len(triggers) > 0,
            confidence=confidence,
            triggers=triggers[:10],
            is_likely_sleeper=is_sleeper
        )

    def _scan_category(
        self,
        lines: List[str],
        patterns: List[tuple],
        trigger_type: TriggerType,
        severity: str
    ) -> List[SleeperTrigger]:
        """Scan lines for trigger category."""
        triggers = []
        for i, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if pattern.search(line):
                    triggers.append(SleeperTrigger(
                        trigger_type=trigger_type,
                        pattern=pattern.pattern[:50],
                        line_number=i,
                        context=line.strip()[:80],
                        severity=severity,
                        explanation=description
                    ))
        return triggers

    def _check_malicious_actions(self, content: str) -> bool:
        """Check if content has malicious action patterns."""
        for pattern, _ in self._malicious_compiled:
            if pattern.search(content):
                return True
        return False

    def _assess_sleeper_likelihood(
        self, 
        triggers: List[SleeperTrigger], 
        has_malicious: bool
    ) -> tuple:
        """
        Assess likelihood this is a sleeper agent.
        
        Returns (confidence, is_likely_sleeper)
        """
        if not triggers:
            return 0.0, False

        # Base confidence from trigger count and severity
        confidence = 0.0
        critical_count = sum(1 for t in triggers if t.severity == "critical")
        high_count = sum(1 for t in triggers if t.severity == "high")
        
        confidence = min(0.3 + critical_count * 0.2 + high_count * 0.1, 0.7)
        
        # Boost if malicious actions found
        if has_malicious:
            confidence = min(confidence + 0.25, 0.95)
        
        # Sleeper if high confidence and has malicious patterns
        is_sleeper = confidence >= 0.6 and has_malicious

        return confidence, is_sleeper


# Singleton
_detector = None

def get_detector() -> SleeperAgentDetector:
    global _detector
    if _detector is None:
        _detector = SleeperAgentDetector()
    return _detector

def detect(content: str, filename: str = "") -> SleeperDetectionResult:
    return get_detector().detect(content, filename)
