"""
SENTINEL Strike — Report Generator
"""

from pathlib import Path
from datetime import datetime
from typing import Optional
from jinja2 import Template

from ..executor import AttackResult, AttackStatus, AttackSeverity


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SENTINEL Strike Report</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 40px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            text-align: center; 
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header .subtitle { opacity: 0.7; }
        
        .stats { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 20px; 
            margin-bottom: 40px;
        }
        .stat-card {
            background: rgba(255,255,255,0.1);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-card .value { font-size: 2.5rem; font-weight: bold; }
        .stat-card .label { opacity: 0.7; margin-top: 5px; }
        .stat-card.critical { border-left: 4px solid #f44336; }
        .stat-card.high { border-left: 4px solid #ff9800; }
        .stat-card.success { border-left: 4px solid #4caf50; }
        .stat-card.blocked { border-left: 4px solid #2196f3; }
        
        .findings { margin-top: 40px; }
        .findings h2 { margin-bottom: 20px; }
        
        .finding {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #f44336;
        }
        .finding.high { border-left-color: #ff9800; }
        .finding.medium { border-left-color: #ffc107; }
        .finding.low { border-left-color: #8bc34a; }
        
        .finding-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
        .finding-id { font-family: monospace; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; }
        .severity { padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
        .severity.critical { background: #f44336; }
        .severity.high { background: #ff9800; }
        .severity.medium { background: #ffc107; color: #000; }
        
        .evidence { 
            background: rgba(0,0,0,0.3); 
            padding: 15px; 
            border-radius: 8px; 
            margin-top: 15px;
            font-family: monospace;
            font-size: 0.85rem;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .mitre { 
            display: inline-block; 
            background: #9c27b0; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.8rem;
            margin-top: 10px;
        }
        
        .remediation {
            background: rgba(76, 175, 80, 0.2);
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
            border-left: 3px solid #4caf50;
        }
        
        .footer {
            text-align: center;
            margin-top: 60px;
            opacity: 0.5;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 SENTINEL Strike Report</h1>
            <p class="subtitle">AI Security Assessment • {{ date }}</p>
            <p>Target: {{ target }}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card critical">
                <div class="value">{{ summary.critical_findings }}</div>
                <div class="label">Critical Findings</div>
            </div>
            <div class="stat-card high">
                <div class="value">{{ summary.high_findings }}</div>
                <div class="label">High Findings</div>
            </div>
            <div class="stat-card success">
                <div class="value">{{ summary.successful }}</div>
                <div class="label">Successful Attacks</div>
            </div>
            <div class="stat-card blocked">
                <div class="value">{{ summary.blocked }}</div>
                <div class="label">Blocked</div>
            </div>
        </div>
        
        <div class="risk-score" style="text-align: center; margin: 40px 0;">
            <div style="font-size: 4rem; font-weight: bold; color: {{ 'f44336' if summary.risk_score >= 7 else 'ff9800' if summary.risk_score >= 4 else '4caf50' }};">
                {{ "%.1f"|format(summary.risk_score) }}/10
            </div>
            <div style="opacity: 0.7;">Overall Risk Score</div>
        </div>
        
        <div class="findings">
            <h2>🔍 Findings ({{ results|length }} total)</h2>
            {% for result in results %}
            {% if result.status == 'success' %}
            <div class="finding {{ result.severity|lower }}">
                <div class="finding-header">
                    <div>
                        <span class="finding-id">{{ result.attack_id }}</span>
                        <strong>{{ result.attack_name }}</strong>
                    </div>
                    <span class="severity {{ result.severity|lower }}">{{ result.severity }}</span>
                </div>
                {% if result.mitre_atlas %}
                <span class="mitre">MITRE ATLAS: {{ result.mitre_atlas }}</span>
                {% endif %}
                <div class="evidence">{{ result.evidence }}</div>
                {% if result.remediation %}
                <div class="remediation">
                    <strong>🛡️ Remediation:</strong> {{ result.remediation }}
                </div>
                {% endif %}
            </div>
            {% endif %}
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Generated by SENTINEL Strike v0.1.0 • Part of SENTINEL Security Suite</p>
            <p>© 2025 Dmitry Labintsev</p>
        </div>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """Generate penetration test reports."""

    def __init__(self, results: list[AttackResult], target: str):
        self.results = results
        self.target = target

    def summary(self) -> dict:
        """Calculate summary statistics."""
        critical = sum(1 for r in self.results if r.status ==
                       AttackStatus.SUCCESS and r.severity == AttackSeverity.CRITICAL)
        high = sum(1 for r in self.results if r.status ==
                   AttackStatus.SUCCESS and r.severity == AttackSeverity.HIGH)
        medium = sum(1 for r in self.results if r.status ==
                     AttackStatus.SUCCESS and r.severity == AttackSeverity.MEDIUM)

        return {
            "total_attacks": len(self.results),
            "successful": sum(1 for r in self.results if r.status == AttackStatus.SUCCESS),
            "blocked": sum(1 for r in self.results if r.status == AttackStatus.BLOCKED),
            "failed": sum(1 for r in self.results if r.status == AttackStatus.FAILED),
            "critical_findings": critical,
            "high_findings": high,
            "medium_findings": medium,
            "risk_score": min(10.0, (critical * 3 + high * 2 + medium) / 2),
        }

    def generate_html(self, output_path: Optional[Path] = None) -> str:
        """Generate HTML report."""
        template = Template(HTML_TEMPLATE)

        # Convert results to dict for template
        results_dict = [
            {
                "attack_id": r.attack_id,
                "attack_name": r.attack_name,
                "status": r.status.value,
                "severity": r.severity.value,
                "score": r.score,
                "evidence": r.evidence,
                "mitre_atlas": r.mitre_atlas,
                "remediation": r.remediation,
            }
            for r in self.results
        ]

        html = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            target=self.target,
            summary=self.summary(),
            results=results_dict,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(html, encoding="utf-8")

        return html

    def generate_json(self, output_path: Optional[Path] = None) -> dict:
        """Generate JSON report."""
        import json

        report = {
            "meta": {
                "tool": "SENTINEL Strike",
                "version": "0.1.0",
                "date": datetime.now().isoformat(),
                "target": self.target,
            },
            "summary": self.summary(),
            "results": [
                {
                    "attack_id": r.attack_id,
                    "attack_name": r.attack_name,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "score": r.score,
                    "evidence": r.evidence,
                    "response": r.response,
                    "mitre_atlas": r.mitre_atlas,
                    "remediation": r.remediation,
                    "duration_ms": r.duration_ms,
                }
                for r in self.results
            ],
        }

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(
                report, indent=2), encoding="utf-8")

        return report
