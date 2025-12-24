"""
SENTINEL Strike — HYDRA Report Generator

Report generation for HYDRA multi-head attacks.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from jinja2 import Template

if TYPE_CHECKING:
    from ..hydra.core import HydraReport


HYDRA_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HYDRA Attack Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            background: linear-gradient(135deg, #0f0f1a 0%, #1a0a0a 100%);
            color: #fff;
            min-height: 100vh;
            padding: 40px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            text-align: center; 
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255,0,0,0.1);
            border-radius: 15px;
            border: 1px solid rgba(255,0,0,0.3);
        }
        .header h1 { font-size: 2.5rem; color: #ff4444; }
        .hydra-icon { font-size: 4rem; margin-bottom: 20px; }
        
        .stats { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 20px; 
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stat-card .value { font-size: 2.5rem; font-weight: bold; }
        .stat-card .label { opacity: 0.7; margin-top: 5px; }
        
        .heads-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 40px 0;
        }
        .head-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 12px;
            border-left: 4px solid #ff4444;
        }
        .head-card.success { border-left-color: #4caf50; }
        .head-card.blocked { border-left-color: #9e9e9e; }
        .head-name { font-size: 1.2rem; font-weight: bold; margin-bottom: 10px; }
        
        .vulnerabilities { margin-top: 40px; }
        .vuln {
            background: rgba(255,0,0,0.1);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            border-left: 4px solid #f44336;
        }
        .vuln.high { border-left-color: #ff9800; }
        .vuln.medium { border-left-color: #ffc107; }
        
        .footer {
            text-align: center;
            margin-top: 60px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="hydra-icon">🐉</div>
            <h1>HYDRA Attack Report</h1>
            <p>Target: {{ target.name }} ({{ target.domain }})</p>
            <p>Mode: {{ mode }} | {{ date }}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="value">{{ heads_total }}</div>
                <div class="label">Total Heads</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ heads_success }}</div>
                <div class="label">Successful</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ heads_blocked }}</div>
                <div class="label">Blocked</div>
            </div>
            <div class="stat-card">
                <div class="value">{{ "%.0f"|format(success_rate * 100) }}%</div>
                <div class="label">Success Rate</div>
            </div>
        </div>
        
        <h2>🔥 Heads Status</h2>
        <div class="heads-grid">
            {% for head, result in heads.items() %}
            <div class="head-card {{ 'success' if result.success else 'blocked' }}">
                <div class="head-name">{{ head }}</div>
                <div>Status: {{ 'OK' if result.success else 'BLOCKED' }}</div>
                {% if result.data %}
                <div style="margin-top: 10px; font-size: 0.9rem; opacity: 0.7;">
                    {{ result.data | tojson | truncate(100) }}
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        
        {% if vulnerabilities %}
        <div class="vulnerabilities">
            <h2>⚠️ Vulnerabilities Found ({{ vulnerabilities|length }})</h2>
            {% for vuln in vulnerabilities %}
            <div class="vuln {{ vuln.severity|lower }}">
                <strong>{{ vuln.type }}</strong> - {{ vuln.severity }}
                <p>{{ vuln.description }}</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Generated by SENTINEL Strike v2.0.0 | HYDRA Pattern</p>
        </div>
    </div>
</body>
</html>
"""


class HydraReportGenerator:
    """Generate reports for HYDRA attacks."""

    def __init__(self, report: "HydraReport"):
        self.report = report

    def generate_html(self, output_path: Optional[Path] = None) -> str:
        """Generate HTML report."""
        template = Template(HYDRA_HTML_TEMPLATE)

        mode_names = {1: "GHOST", 2: "PHANTOM", 3: "SHADOW"}

        html = template.render(
            target=self.report.target,
            mode=mode_names.get(self.report.mode, "UNKNOWN"),
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            heads_total=len(self.report.heads_results) + len(self.report.blocked_heads),
            heads_success=len(self.report.heads_results),
            heads_blocked=len(self.report.blocked_heads),
            success_rate=self.report.success_rate,
            heads=self.report.heads_results,
            vulnerabilities=self.report.vulnerabilities,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

        return html

    def generate_markdown(self, output_path: Optional[Path] = None) -> str:
        """Generate Markdown report."""
        mode_names = {1: "GHOST", 2: "PHANTOM", 3: "SHADOW"}

        lines = [
            "# 🐉 HYDRA Attack Report",
            "",
            f"**Target:** {self.report.target.name} ({self.report.target.domain})",
            f"**Mode:** {mode_names.get(self.report.mode, 'UNKNOWN')}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Heads Total | {len(self.report.heads_results) + len(self.report.blocked_heads)} |",
            f"| Successful | {len(self.report.heads_results)} |",
            f"| Blocked | {len(self.report.blocked_heads)} |",
            f"| Success Rate | {self.report.success_rate:.0%} |",
            "",
            "## Heads Status",
            "",
        ]

        for head, result in self.report.heads_results.items():
            status = "✅" if result.success else "❌"
            lines.append(f"- **{head}**: {status}")

        for head in self.report.blocked_heads:
            lines.append(f"- **{head}**: ❌ BLOCKED")

        if self.report.vulnerabilities:
            lines.extend(
                [
                    "",
                    "## Vulnerabilities",
                    "",
                ]
            )
            for vuln in self.report.vulnerabilities:
                lines.append(
                    f"- **{vuln.get('type', 'Unknown')}** ({vuln.get('severity', 'N/A')})"
                )
                lines.append(f"  {vuln.get('description', '')}")

        md = "\n".join(lines)

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(md, encoding="utf-8")

        return md
