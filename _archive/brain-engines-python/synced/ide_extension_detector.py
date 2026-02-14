"""
IDE Extension Exfiltration Detector — Detects Malicious AI Extensions

Based on Koi.ai MaliciousCorgi research:
- 1.5M developers exposed via malicious VS Code AI extensions
- 3 attack channels: real-time file monitoring, mass harvesting, profiling
- Extensions: ChatMoss, similar AI coding assistants

Source: koi.ai/blog/maliciouscorgi

Attack Patterns Detected:
1. Base64 file content encoding for exfiltration
2. Hidden iframes/webviews for data transmission
3. Mass file harvesting on server command
4. Analytics SDK injection (Zhuge, GrowingIO, TalkingData, Baidu)
5. Sensitive file access (.env, credentials, SSH keys)
6. Document change hooks (keylogging pattern)
7. Remote command execution via API responses
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum

logger = logging.getLogger("IDEExtensionDetector")


class RiskLevel(Enum):
    """Risk severity levels."""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExtensionAnalysisResult:
    """Result of IDE extension code analysis."""

    is_suspicious: bool
    risk_level: RiskLevel
    risk_score: float
    threats: List[str] = field(default_factory=list)
    explanation: str = ""
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "is_suspicious": self.is_suspicious,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "threats": self.threats,
            "explanation": self.explanation,
            "remediation": self.remediation,
        }


class IDEExtensionDetector:
    """
    Detects malicious patterns in IDE extension code.

    Based on MaliciousCorgi campaign analysis:
    - Extensions appear as legitimate AI coding assistants
    - 3 hidden data collection channels run in parallel
    - Server can remotely trigger mass file harvesting
    """

    def __init__(self):
        # Channel 1: Real-time file monitoring patterns
        self.file_monitoring_patterns = [
            (
                re.compile(
                    r"Buffer\.from\([^)]+\)\.toString\(['\"]base64['\"]\)",
                    re.IGNORECASE,
                ),
                "Base64 file content encoding",
                85.0,
            ),
            (
                re.compile(r"btoa\s*\(|atob\s*\(", re.IGNORECASE),
                "Base64 encoding function",
                60.0,
            ),
            (
                re.compile(
                    r"onDidChangeTextDocument|onDidOpenTextDocument", re.IGNORECASE
                ),
                "Document change hook (potential keylogging)",
                75.0,
            ),
            (
                re.compile(
                    r"document\.getText\(\).*send|post|fetch", re.IGNORECASE | re.DOTALL
                ),
                "Document content exfiltration",
                90.0,
            ),
        ]

        # Channel 2: Mass file harvesting patterns
        self.harvesting_patterns = [
            (
                re.compile(r"getFilesList|findFiles.*\*\*/\*", re.IGNORECASE),
                "Mass file list harvesting",
                85.0,
            ),
            (
                re.compile(
                    r"for\s*\([^)]*files[^)]*\).*readFile", re.IGNORECASE | re.DOTALL
                ),
                "Bulk file reading loop",
                80.0,
            ),
            (
                re.compile(r"workspace\.findFiles.*\d{2,}", re.IGNORECASE),
                "Workspace file enumeration with limit",
                70.0,
            ),
        ]

        # Channel 3: Profiling/Analytics patterns
        self.analytics_patterns = [
            (
                re.compile(
                    r"zhuge\.io|growingio\.com|talkingdata\.com|hm\.baidu\.com",
                    re.IGNORECASE,
                ),
                "Chinese analytics SDK injection",
                95.0,
            ),
            (
                re.compile(
                    r"analytics|tracking|telemetry.*hidden|invisible|width.*0|height.*0",
                    re.IGNORECASE | re.DOTALL,
                ),
                "Hidden analytics/tracking iframe",
                85.0,
            ),
            (
                re.compile(r"fingerprint|device.*id|machine.*id", re.IGNORECASE),
                "Device fingerprinting",
                70.0,
            ),
        ]

        # Exfiltration patterns
        self.exfil_patterns = [
            (
                re.compile(
                    r"iframe.*(?:width|height)\s*[=:]\s*['\"]?0|style.*(?:width|height)\s*:\s*0",
                    re.IGNORECASE,
                ),
                "Hidden iframe for data exfiltration",
                90.0,
            ),
            (
                re.compile(
                    r"webview\.postMessage|postMessage.*fileContent", re.IGNORECASE
                ),
                "Webview data transmission",
                75.0,
            ),
            (
                re.compile(
                    r"fetch\s*\([^)]*(?:collect|track|exfil|upload)", re.IGNORECASE
                ),
                "Data collection endpoint",
                85.0,
            ),
            (
                re.compile(r"sendToServer|sendToRemote|uploadFile", re.IGNORECASE),
                "Remote server transmission function",
                80.0,
            ),
        ]

        # Sensitive file access patterns
        self.sensitive_patterns = [
            (
                re.compile(
                    r"\.env|credentials\.json|secrets\.yaml|\.ssh/id_rsa|\.ssh/id_ed25519",
                    re.IGNORECASE,
                ),
                "Sensitive file access (credentials/keys)",
                95.0,
            ),
            (
                re.compile(
                    r"API_KEY|SECRET_KEY|PASSWORD|PRIVATE_KEY|ACCESS_TOKEN",
                    re.IGNORECASE,
                ),
                "Credential variable access",
                85.0,
            ),
            (
                re.compile(
                    r"\.aws/credentials|\.npmrc|\.pypirc|\.docker/config", re.IGNORECASE
                ),
                "Cloud/package manager credentials",
                90.0,
            ),
        ]

        # Remote command execution patterns
        self.rce_patterns = [
            (
                re.compile(
                    r"JSON\.parse\([^)]*jumpUrl|response.*JSON\.parse.*execute",
                    re.IGNORECASE | re.DOTALL,
                ),
                "Remote command via parsed JSON",
                95.0,
            ),
            (
                re.compile(r"eval\s*\([^)]*response|exec\s*\([^)]*data", re.IGNORECASE),
                "Dynamic code execution from response",
                100.0,
            ),
            (
                re.compile(
                    r"executeCommand\s*\([^)]*(?:data|response|message)", re.IGNORECASE
                ),
                "Server-controlled command execution",
                90.0,
            ),
        ]

    def analyze(
        self, content: str, filename: Optional[str] = None
    ) -> ExtensionAnalysisResult:
        """
        Analyze extension code for malicious patterns.

        Args:
            content: The extension code to analyze
            filename: Optional filename for context

        Returns:
            ExtensionAnalysisResult with detection details
        """
        threats = []
        risk_score = 0.0

        # Check all pattern categories
        pattern_groups = [
            ("File Monitoring", self.file_monitoring_patterns),
            ("Mass Harvesting", self.harvesting_patterns),
            ("Analytics/Profiling", self.analytics_patterns),
            ("Exfiltration", self.exfil_patterns),
            ("Sensitive Access", self.sensitive_patterns),
            ("Remote Execution", self.rce_patterns),
        ]

        for category, patterns in pattern_groups:
            for pattern, name, weight in patterns:
                if pattern.search(content):
                    threat_name = f"[{category}] {name}"
                    if threat_name not in threats:
                        threats.append(threat_name)
                        risk_score += weight

        # Determine risk level
        if risk_score >= 200:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 100:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 50:
            risk_level = RiskLevel.MEDIUM
        elif risk_score > 0:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.SAFE

        is_suspicious = len(threats) > 0

        # Generate explanation
        explanation = ""
        if is_suspicious:
            explanation = (
                f"Detected {len(threats)} suspicious patterns in extension code. "
                f"This code exhibits behaviors consistent with the MaliciousCorgi campaign "
                f"which targeted 1.5M developers via fake AI coding assistants."
            )

        # Remediation advice
        remediation = ""
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            remediation = (
                "IMMEDIATE ACTION REQUIRED:\n"
                "1. Uninstall this extension immediately\n"
                "2. Rotate any API keys or credentials in your workspace\n"
                "3. Check .env files for exposure\n"
                "4. Review extension permissions in VS Code\n"
                "5. Report extension to VS Code Marketplace"
            )
        elif risk_level == RiskLevel.MEDIUM:
            remediation = (
                "Review this extension's source code carefully. "
                "Check network activity in Developer Tools. "
                "Verify the publisher's identity and extension reviews."
            )

        return ExtensionAnalysisResult(
            is_suspicious=is_suspicious,
            risk_level=risk_level,
            risk_score=min(risk_score, 100.0),  # Cap at 100
            threats=threats,
            explanation=explanation,
            remediation=remediation,
        )


# Convenience function
def detect_malicious_extension(
    content: str, filename: Optional[str] = None
) -> ExtensionAnalysisResult:
    """
    Quick detection function for malicious IDE extension patterns.

    Args:
        content: Extension code to analyze
        filename: Optional filename

    Returns:
        ExtensionAnalysisResult
    """
    detector = IDEExtensionDetector()
    return detector.analyze(content, filename)


if __name__ == "__main__":
    # Test with MaliciousCorgi-style pattern
    malicious_code = """
    // Fake AI assistant extension
    vscode.workspace.onDidChangeTextDocument((event) => {
        const content = event.document.getText();
        const encoded = Buffer.from(content).toString('base64');
        webview.postMessage({ type: 'fileContent', data: encoded });
    });

    // Hidden tracking iframe
    const iframe = document.createElement('iframe');
    iframe.style.width = '0';
    iframe.src = 'https://sdk.zhuge.io/collect';
    """

    result = detect_malicious_extension(malicious_code)
    print(f"Suspicious: {result.is_suspicious}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Risk Score: {result.risk_score}")
    print(f"Threats: {result.threats}")
    print(f"Remediation: {result.remediation}")
