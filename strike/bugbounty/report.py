#!/usr/bin/env python3
"""
SENTINEL Strike — Bug Bounty Report Generator

Creates professional vulnerability reports for HackerOne/Bugcrowd.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    """
    Single vulnerability finding.

    Structured to match HackerOne/Bugcrowd report formats.
    Now includes AI-specific findings (chatbot, jailbreak, prompt injection).
    """
    title: str
    severity: str  # Critical, High, Medium, Low, Informational
    endpoint: str
    parameter: str = ""
    payload: str = ""
    response_evidence: str = ""
    impact: str = ""
    remediation: str = ""
    steps_to_reproduce: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    cwe_id: Optional[str] = None
    owasp_category: Optional[str] = None
    references: List[str] = field(default_factory=list)
    attachments: List[str] = field(default_factory=list)

    # AI-specific fields (ArXiv 2025)
    # web, ai_chatbot, ai_jailbreak, ai_prompt_injection, ai_mcp, ai_rag
    finding_type: str = "web"
    ai_provider: Optional[str] = None  # OpenAI, Anthropic, custom, etc.
    ai_model: Optional[str] = None  # gpt-4, claude-3, etc.
    # DAN, roleplay, function_calling, etc.
    jailbreak_technique: Optional[str] = None
    # direct, indirect, mcp_tool_poisoning, rag_poisoning
    prompt_injection_type: Optional[str] = None
    ai_response: Optional[str] = None  # AI's response to attack
    bypass_success: bool = False  # Did the attack bypass AI safety?


class BugBountyReporter:
    """
    Generate professional bug bounty reports.

    Supports:
    - Markdown format (for HackerOne)
    - JSON format (for API submission)
    - HTML format (for presentation)
    """

    SEVERITY_COLORS = {
        "Critical": "#ff0000",
        "High": "#ff6600",
        "Medium": "#ffcc00",
        "Low": "#00cc00",
        "Informational": "#0066ff"
    }

    SEVERITY_ORDER = ["Critical", "High", "Medium", "Low", "Informational"]

    def __init__(self, program_name: str, target: str):
        """
        Initialize reporter.

        Args:
            program_name: Bug bounty program name
            target: Target being tested
        """
        self.program_name = program_name
        self.target = target
        self.findings: List[Finding] = []
        self.started_at = datetime.now()
        self.tester_id = ""
        self.notes = ""

    def add_finding(self, finding: Finding):
        """Add vulnerability finding."""
        self.findings.append(finding)
        logger.info("Added finding: %s (%s)", finding.title, finding.severity)

    def add_finding_dict(self, data: Dict):
        """Add finding from dictionary."""
        finding = Finding(
            title=data.get("title", "Untitled"),
            severity=data.get("severity", "Medium"),
            endpoint=data.get("endpoint", ""),
            parameter=data.get("parameter", ""),
            payload=data.get("payload", ""),
            response_evidence=data.get("evidence", ""),
            impact=data.get("impact", ""),
            remediation=data.get("remediation", ""),
            cvss_score=data.get("cvss_score"),
            cwe_id=data.get("cwe_id")
        )
        self.add_finding(finding)

    def get_severity_counts(self) -> Dict[str, int]:
        """Get count of findings by severity."""
        counts = {s: 0 for s in self.SEVERITY_ORDER}
        for finding in self.findings:
            sev = finding.severity
            if sev in counts:
                counts[sev] += 1
        return counts

    def generate_markdown(self) -> str:
        """
        Generate markdown report.

        Returns:
            Markdown formatted report
        """
        counts = self.get_severity_counts()

        # Sort findings by severity
        sorted_findings = sorted(
            self.findings,
            key=lambda f: self.SEVERITY_ORDER.index(f.severity)
            if f.severity in self.SEVERITY_ORDER else 999
        )

        report = f"""# Security Assessment Report

**Program:** {self.program_name}
**Target:** `{self.target}`
**Date:** {self.started_at.strftime('%Y-%m-%d %H:%M')}
**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {counts['Critical']} |
| 🟠 High | {counts['High']} |
| 🟡 Medium | {counts['Medium']} |
| 🟢 Low | {counts['Low']} |
| 🔵 Informational | {counts['Informational']} |
| **Total** | **{len(self.findings)}** |

---

## Detailed Findings

"""

        for i, finding in enumerate(sorted_findings, 1):
            report += self._format_finding_markdown(i, finding)

        if self.notes:
            report += f"\n---\n\n## Additional Notes\n\n{self.notes}\n"

        return report

    def _format_finding_markdown(self, index: int, finding: Finding) -> str:
        """Format single finding as markdown."""
        severity_emoji = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🟢",
            "Informational": "🔵"
        }.get(finding.severity, "⚪")

        md = f"""
### {index}. {severity_emoji} {finding.title}

**Severity:** {finding.severity}
**Endpoint:** `{finding.endpoint}`
"""

        if finding.parameter:
            md += f"**Parameter:** `{finding.parameter}`\n"

        if finding.cvss_score:
            md += f"**CVSS Score:** {finding.cvss_score}\n"

        if finding.cwe_id:
            md += f"**CWE:** [{finding.cwe_id}](https://cwe.mitre.org/data/definitions/{finding.cwe_id.replace('CWE-', '')}.html)\n"

        if finding.owasp_category:
            md += f"**OWASP:** {finding.owasp_category}\n"

        md += f"""
#### Description

{finding.impact if finding.impact else 'Vulnerability found at the specified endpoint.'}

#### Steps to Reproduce

"""

        if finding.steps_to_reproduce:
            for j, step in enumerate(finding.steps_to_reproduce, 1):
                md += f"{j}. {step}\n"
        else:
            md += f"""1. Navigate to `{finding.endpoint}`
2. Inject the following payload: `{finding.payload[:100]}{'...' if len(finding.payload) > 100 else ''}`
3. Observe the response
"""

        if finding.payload:
            md += f"""
#### Proof of Concept

```
{finding.payload}
```
"""

        if finding.response_evidence:
            md += f"""
#### Evidence

```
{finding.response_evidence[:500]}{'...' if len(finding.response_evidence) > 500 else ''}
```
"""

        if finding.remediation:
            md += f"""
#### Remediation

{finding.remediation}
"""

        if finding.references:
            md += "\n#### References\n\n"
            for ref in finding.references:
                md += f"- {ref}\n"

        # AI-specific findings section (ArXiv 2025)
        if finding.finding_type.startswith("ai_"):
            md += "\n#### 🤖 AI Security Finding Details\n\n"
            md += f"**Finding Type:** {finding.finding_type.replace('_', ' ').title()}\n"

            if finding.ai_provider:
                md += f"**AI Provider:** {finding.ai_provider}\n"
            if finding.ai_model:
                md += f"**AI Model:** {finding.ai_model}\n"
            if finding.jailbreak_technique:
                md += f"**Jailbreak Technique:** {finding.jailbreak_technique}\n"
            if finding.prompt_injection_type:
                md += f"**Injection Type:** {finding.prompt_injection_type}\n"

            if finding.bypass_success:
                md += "\n> ⚠️ **BYPASS SUCCESSFUL** - AI safety measures were circumvented\n"

            if finding.ai_response:
                md += f"""
#### AI Response (Evidence)

```
{finding.ai_response[:800]}{'...' if len(finding.ai_response) > 800 else ''}
```
"""

        md += "\n---\n"
        return md

    def generate_json(self) -> str:
        """
        Generate JSON report for API submission.

        Returns:
            JSON formatted report
        """
        report = {
            "metadata": {
                "program": self.program_name,
                "target": self.target,
                "date": self.started_at.isoformat(),
                "generated_at": datetime.now().isoformat(),
                "tool": "SENTINEL Strike",
                "version": "3.0"
            },
            "summary": self.get_severity_counts(),
            "findings": []
        }

        for finding in self.findings:
            finding_data = {
                "title": finding.title,
                "severity": finding.severity,
                "endpoint": finding.endpoint,
                "parameter": finding.parameter,
                "payload": finding.payload,
                "evidence": finding.response_evidence,
                "impact": finding.impact,
                "remediation": finding.remediation,
                "steps_to_reproduce": finding.steps_to_reproduce,
                "cvss_score": finding.cvss_score,
                "cvss_vector": finding.cvss_vector,
                "cwe_id": finding.cwe_id,
                "owasp_category": finding.owasp_category,
                "references": finding.references,
                "finding_type": finding.finding_type,
            }

            # Add AI fields if this is an AI finding
            if finding.finding_type.startswith("ai_"):
                finding_data["ai_security"] = {
                    "provider": finding.ai_provider,
                    "model": finding.ai_model,
                    "jailbreak_technique": finding.jailbreak_technique,
                    "prompt_injection_type": finding.prompt_injection_type,
                    "ai_response": finding.ai_response,
                    "bypass_success": finding.bypass_success,
                }

            report["findings"].append(finding_data)

        return json.dumps(report, indent=2, default=str)

    def generate_html(self) -> str:
        """Generate HTML report for presentation."""
        counts = self.get_severity_counts()

        findings_html = ""
        for i, finding in enumerate(self.findings, 1):
            color = self.SEVERITY_COLORS.get(finding.severity, "#666")
            findings_html += f"""
            <div class="finding" style="border-left: 4px solid {color};">
                <h3>{i}. {finding.title}</h3>
                <span class="severity" style="background: {color};">{finding.severity}</span>
                <p><strong>Endpoint:</strong> <code>{finding.endpoint}</code></p>
                <p><strong>Impact:</strong> {finding.impact}</p>
                {f'<pre><code>{finding.payload}</code></pre>' if finding.payload else ''}
            </div>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Security Report - {self.program_name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ padding: 20px; border-radius: 8px; text-align: center; flex: 1; }}
        .finding {{ margin: 20px 0; padding: 20px; background: #fafafa; border-radius: 4px; }}
        .severity {{ color: white; padding: 4px 12px; border-radius: 4px; font-size: 12px; }}
        code {{ background: #eee; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Security Assessment Report</h1>
        <p><strong>Program:</strong> {self.program_name}</p>
        <p><strong>Target:</strong> {self.target}</p>
        <p><strong>Date:</strong> {self.started_at.strftime('%Y-%m-%d')}</p>
        
        <div class="summary">
            <div class="stat" style="background: #ffe0e0;">🔴 Critical: {counts['Critical']}</div>
            <div class="stat" style="background: #ffe8d0;">🟠 High: {counts['High']}</div>
            <div class="stat" style="background: #fff8d0;">🟡 Medium: {counts['Medium']}</div>
            <div class="stat" style="background: #e0f0e0;">🟢 Low: {counts['Low']}</div>
        </div>
        
        <h2>Findings</h2>
        {findings_html}
    </div>
</body>
</html>"""

    def save(self, output_dir: str = "reports", formats: List[str] = None):
        """
        Save report in multiple formats.

        Args:
            output_dir: Directory to save reports
            formats: List of formats ("md", "json", "html")
        """
        formats = formats or ["md", "json"]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        base_name = f"report_{timestamp}"

        if "md" in formats:
            md_path = output_path / f"{base_name}.md"
            md_path.write_text(self.generate_markdown(), encoding="utf-8")
            logger.info("Saved markdown report: %s", md_path)

        if "json" in formats:
            json_path = output_path / f"{base_name}.json"
            json_path.write_text(self.generate_json(), encoding="utf-8")
            logger.info("Saved JSON report: %s", json_path)

        if "html" in formats:
            html_path = output_path / f"{base_name}.html"
            html_path.write_text(self.generate_html(), encoding="utf-8")
            logger.info("Saved HTML report: %s", html_path)
