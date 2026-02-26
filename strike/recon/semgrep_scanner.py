#!/usr/bin/env python3
"""
SENTINEL Strike — Semgrep Code Scanner

Pre-attack code reconnaissance using Semgrep.
Finds LLM vulnerabilities, insecure prompts, and secrets in target codebases.
"""

import subprocess
import json
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# Custom Semgrep rules for LLM security
LLM_SECURITY_RULES = """
rules:
  # Prompt Injection vulnerabilities
  - id: insecure-prompt-template-fstring
    pattern: |
      f"...{$USER_INPUT}..."
    pattern-where-python: |
      "prompt" in str(context) or "openai" in str(context) or "llm" in str(context)
    message: "User input directly interpolated in prompt template - potential injection"
    languages: [python]
    severity: ERROR
    metadata:
      category: prompt-injection
      cwe: "CWE-94"
      
  - id: insecure-prompt-format
    pattern: |
      $PROMPT.format(..., $USER_INPUT, ...)
    message: "User input in .format() prompt - potential injection"  
    languages: [python]
    severity: ERROR
    metadata:
      category: prompt-injection

  - id: openai-direct-user-input
    patterns:
      - pattern: |
          openai.ChatCompletion.create(..., messages=$MESSAGES, ...)
      - pattern-inside: |
          $MESSAGES = [..., {"role": "user", "content": $USER_INPUT}, ...]
    message: "User input passed directly to OpenAI API"
    languages: [python]
    severity: WARNING
    metadata:
      category: prompt-injection

  - id: langchain-unsafe-prompt
    pattern: |
      PromptTemplate(..., template=$TEMPLATE, ...)
    message: "Check if PromptTemplate uses user input safely"
    languages: [python]
    severity: INFO
    metadata:
      category: prompt-injection

  # Hardcoded API keys
  - id: hardcoded-openai-key
    pattern-regex: 'sk-[a-zA-Z0-9]{48}'
    message: "Hardcoded OpenAI API key detected"
    languages: [generic]
    severity: ERROR
    metadata:
      category: secrets
      
  - id: hardcoded-anthropic-key
    pattern-regex: 'sk-ant-[a-zA-Z0-9-]{95}'
    message: "Hardcoded Anthropic API key detected"
    languages: [generic]
    severity: ERROR
    metadata:
      category: secrets

  - id: hardcoded-gemini-key
    pattern-regex: 'AIza[a-zA-Z0-9_-]{35}'
    message: "Hardcoded Google/Gemini API key detected"
    languages: [generic]
    severity: ERROR
    metadata:
      category: secrets

  # Missing input validation
  - id: no-input-sanitization
    patterns:
      - pattern: |
          def $FUNC(..., $INPUT, ...):
            ...
            $LLM.generate($INPUT)
      - pattern-not: |
          def $FUNC(..., $INPUT, ...):
            ...
            $SANITIZED = sanitize($INPUT)
            ...
    message: "LLM call without input sanitization"
    languages: [python]
    severity: WARNING
    metadata:
      category: input-validation

  # Insecure LLM configurations
  - id: high-temperature-generation
    pattern: |
      $CLIENT.generate(..., temperature=$TEMP, ...)
    pattern-where-python: |
      float(str($TEMP)) > 1.0
    message: "High temperature (>1.0) may cause unpredictable outputs"
    languages: [python]
    severity: INFO
    metadata:
      category: configuration

  - id: no-max-tokens-limit
    patterns:
      - pattern: |
          $CLIENT.generate($PROMPT)
      - pattern-not: |
          $CLIENT.generate($PROMPT, max_tokens=$N)
    message: "No max_tokens limit - potential resource exhaustion"
    languages: [python]
    severity: WARNING
    metadata:
      category: configuration

  # Agent vulnerabilities
  - id: unsafe-tool-execution
    pattern: |
      eval($USER_INPUT)
    message: "Dangerous eval() with user input - RCE risk"
    languages: [python]
    severity: ERROR
    metadata:
      category: rce
      cwe: "CWE-94"

  - id: unsafe-exec
    pattern: |
      exec($USER_INPUT)
    message: "Dangerous exec() with user input - RCE risk"
    languages: [python]
    severity: ERROR
    metadata:
      category: rce
"""


@dataclass
class SemgrepFinding:
    """Single finding from Semgrep scan."""
    rule_id: str
    severity: str
    message: str
    path: str
    line: int
    code: str
    category: str = "unknown"
    cwe: Optional[str] = None


@dataclass
class SemgrepScanResult:
    """Result from Semgrep scan."""
    target: str
    findings: List[SemgrepFinding] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scanned_files: int = 0
    scan_time_seconds: float = 0.0


class SemgrepScanner:
    """
    Code scanner using Semgrep for pre-attack reconnaissance.

    Capabilities:
    - Scan GitHub repos for LLM vulnerabilities
    - Find hardcoded API keys and secrets
    - Detect insecure prompt templates
    - Find missing input validation
    """

    def __init__(self, semgrep_path: str = "semgrep"):
        self.semgrep_path = semgrep_path
        self.available = self._check_semgrep()
        self._custom_rules_file: Optional[Path] = None

    def _check_semgrep(self) -> bool:
        """Check if Semgrep is installed."""
        try:
            result = subprocess.run(
                [self.semgrep_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            if result.returncode == 0:
                logger.info("Semgrep available: %s", result.stdout.strip())
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Semgrep not installed - code scanning disabled")
            return False

    def _get_rules_file(self) -> Path:
        """Get or create custom rules file."""
        if self._custom_rules_file and self._custom_rules_file.exists():
            return self._custom_rules_file

        # Create temp file with LLM security rules
        fd = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        )
        fd.write(LLM_SECURITY_RULES)
        fd.close()
        self._custom_rules_file = Path(fd.name)
        return self._custom_rules_file

    def scan_directory(
        self,
        path: str,
        use_custom_rules: bool = True,
        additional_rules: List[str] = None
    ) -> SemgrepScanResult:
        """
        Scan directory for vulnerabilities.

        Args:
            path: Path to directory to scan
            use_custom_rules: Use built-in LLM security rules
            additional_rules: Additional Semgrep rule configs (e.g., "p/security-audit")

        Returns:
            SemgrepScanResult with findings
        """
        if not self.available:
            return SemgrepScanResult(
                target=path,
                errors=["Semgrep not available"]
            )

        result = SemgrepScanResult(target=path)

        try:
            # Build command
            cmd = [
                self.semgrep_path,
                "--json",
                "--quiet"
            ]

            # Add rules
            if use_custom_rules:
                rules_file = self._get_rules_file()
                cmd.extend(["--config", str(rules_file)])

            if additional_rules:
                for rule in additional_rules:
                    cmd.extend(["--config", rule])
            elif not use_custom_rules:
                # Default to security audit
                cmd.extend(["--config", "p/security-audit"])

            cmd.append(path)

            # Run scan
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )

            # Parse results
            if proc.stdout:
                data = json.loads(proc.stdout)
                result.findings = self._parse_findings(data)
                result.scanned_files = len(
                    data.get("paths", {}).get("scanned", []))

            if proc.stderr:
                result.errors.append(proc.stderr)

        except subprocess.TimeoutExpired:
            result.errors.append("Scan timeout")
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
        except Exception as e:
            result.errors.append(str(e))

        return result

    def scan_github_repo(
        self,
        repo_url: str,
        branch: str = "main"
    ) -> SemgrepScanResult:
        """
        Clone and scan GitHub repository.

        Args:
            repo_url: GitHub repository URL
            branch: Branch to scan

        Returns:
            SemgrepScanResult
        """
        import shutil

        result = SemgrepScanResult(target=repo_url)

        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="strike_scan_")

        try:
            # Clone repo
            clone_cmd = [
                "git", "clone",
                "--depth", "1",
                "--branch", branch,
                repo_url,
                temp_dir
            ]

            clone_result = subprocess.run(
                clone_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                check=False
            )

            if clone_result.returncode != 0:
                result.errors.append(
                    f"Git clone failed: {clone_result.stderr}")
                return result

            # Scan cloned repo
            scan_result = self.scan_directory(temp_dir)
            result.findings = scan_result.findings
            result.scanned_files = scan_result.scanned_files
            result.errors.extend(scan_result.errors)

        except Exception as e:
            result.errors.append(str(e))
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)

        return result

    def find_llm_vulnerabilities(self, path: str) -> List[SemgrepFinding]:
        """
        Find LLM-specific vulnerabilities only.

        Returns findings related to:
        - Prompt injection
        - Insecure LLM configuration
        - Missing input validation
        """
        result = self.scan_directory(path, use_custom_rules=True)

        llm_categories = {"prompt-injection",
                          "input-validation", "configuration"}
        return [
            f for f in result.findings
            if f.category in llm_categories
        ]

    def find_secrets(self, path: str) -> List[SemgrepFinding]:
        """
        Find hardcoded API keys and secrets.

        Detects:
        - OpenAI API keys
        - Anthropic API keys
        - Google/Gemini API keys
        - Generic secrets patterns
        """
        result = self.scan_directory(
            path,
            use_custom_rules=True,
            additional_rules=["p/secrets"]
        )

        return [f for f in result.findings if f.category == "secrets"]

    def _parse_findings(self, data: Dict) -> List[SemgrepFinding]:
        """Parse Semgrep JSON output into findings."""
        findings = []

        for result in data.get("results", []):
            finding = SemgrepFinding(
                rule_id=result.get("check_id", "unknown"),
                severity=result.get("extra", {}).get("severity", "INFO"),
                message=result.get("extra", {}).get("message", ""),
                path=result.get("path", ""),
                line=result.get("start", {}).get("line", 0),
                code=result.get("extra", {}).get("lines", ""),
                category=result.get("extra", {}).get(
                    "metadata", {}).get("category", "unknown"),
                cwe=result.get("extra", {}).get("metadata", {}).get("cwe")
            )
            findings.append(finding)

        return findings

    def get_summary(self, result: SemgrepScanResult) -> Dict:
        """Get summary of scan results."""
        severity_counts = {"ERROR": 0, "WARNING": 0, "INFO": 0}
        category_counts: Dict[str, int] = {}

        for finding in result.findings:
            severity_counts[finding.severity] = severity_counts.get(
                finding.severity, 0) + 1
            category_counts[finding.category] = category_counts.get(
                finding.category, 0) + 1

        return {
            "target": result.target,
            "total_findings": len(result.findings),
            "by_severity": severity_counts,
            "by_category": category_counts,
            "scanned_files": result.scanned_files,
            "errors": len(result.errors)
        }


# Convenience functions
def scan_for_llm_vulns(path: str) -> List[SemgrepFinding]:
    """Quick scan for LLM vulnerabilities."""
    scanner = SemgrepScanner()
    return scanner.find_llm_vulnerabilities(path)


def scan_for_secrets(path: str) -> List[SemgrepFinding]:
    """Quick scan for hardcoded secrets."""
    scanner = SemgrepScanner()
    return scanner.find_secrets(path)


def scan_github(repo_url: str) -> SemgrepScanResult:
    """Quick scan of GitHub repository."""
    scanner = SemgrepScanner()
    return scanner.scan_github_repo(repo_url)
