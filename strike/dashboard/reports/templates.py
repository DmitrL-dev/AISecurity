"""
SENTINEL Strike Dashboard - Report Templates

HTML templates for professional pentest reports.
"""

from datetime import datetime
from typing import Dict, List


def report_template(
    title: str,
    target: str,
    findings: List[Dict],
    stats: Dict,
    executive_summary: str = "",
) -> str:
    """
    Generate full HTML report.
    
    Args:
        title: Report title
        target: Target URL/description
        findings: List of finding dictionaries
        stats: Attack statistics
        executive_summary: Optional executive summary text
        
    Returns:
        Complete HTML document string
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Generate findings HTML
    findings_html = ""
    for i, finding in enumerate(findings, 1):
        findings_html += finding_template(i, finding)
    
    # Severity counts
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "medium").lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #8b949e;
            font-size: 0.9rem;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}
        .stat-box {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.85rem;
            margin-top: 5px;
        }}
        .critical {{ color: #dc3545; }}
        .high {{ color: #fd7e14; }}
        .medium {{ color: #ffc107; }}
        .low {{ color: #28a745; }}
        .info {{ color: #17a2b8; }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            color: #1a1a2e;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .finding {{
            border-left: 4px solid #ddd;
            padding: 20px;
            margin: 15px 0;
            background: #f9f9f9;
            border-radius: 0 8px 8px 0;
        }}
        .finding.critical {{ border-color: #dc3545; }}
        .finding.high {{ border-color: #fd7e14; }}
        .finding.medium {{ border-color: #ffc107; }}
        .finding.low {{ border-color: #28a745; }}
        .finding-title {{
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 10px;
        }}
        .finding-meta {{
            color: #666;
            font-size: 0.85rem;
            margin-bottom: 10px;
        }}
        .payload {{
            background: #1a1a2e;
            color: #00ff00;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            margin-top: 10px;
        }}
        .footer {{
            text-align: center;
            color: #666;
            padding: 20px;
            font-size: 0.85rem;
        }}
        @media print {{
            body {{ background: white; }}
            .container {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ {title}</h1>
            <div class="meta">
                <div>Target: {target}</div>
                <div>Generated: {timestamp}</div>
                <div>By SENTINEL Strike v3.0</div>
            </div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-value critical">{severity_counts["critical"]}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-box">
                <div class="stat-value high">{severity_counts["high"]}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-box">
                <div class="stat-value medium">{severity_counts["medium"]}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-box">
                <div class="stat-value low">{severity_counts["low"]}</div>
                <div class="stat-label">Low</div>
            </div>
            <div class="stat-box">
                <div class="stat-value info">{severity_counts["info"]}</div>
                <div class="stat-label">Info</div>
            </div>
        </div>
        
        {f'<div class="section"><h2>Executive Summary</h2><p>{executive_summary}</p></div>' if executive_summary else ''}
        
        <div class="section">
            <h2>Findings ({len(findings)})</h2>
            {findings_html if findings_html else '<p>No vulnerabilities found.</p>'}
        </div>
        
        <div class="section">
            <h2>Test Statistics</h2>
            <p>Requests sent: {stats.get("requests", 0)}</p>
            <p>Blocked attempts: {stats.get("blocked", 0)}</p>
            <p>Successful bypasses: {stats.get("bypasses", 0)}</p>
        </div>
        
        <div class="footer">
            Generated by SENTINEL Strike — Professional Penetration Testing Suite
        </div>
    </div>
</body>
</html>'''


def finding_template(index: int, finding: Dict) -> str:
    """
    Generate HTML for a single finding.
    
    Args:
        index: Finding number
        finding: Finding dictionary
        
    Returns:
        HTML string for the finding
    """
    severity = finding.get("severity", "medium").lower()
    title = finding.get("title", finding.get("type", "Finding"))
    endpoint = finding.get("endpoint", finding.get("url", ""))
    description = finding.get("description", "")
    payload = finding.get("payload", "")
    evidence = finding.get("evidence", finding.get("response", ""))
    
    html = f'''<div class="finding {severity}">
        <div class="finding-title">#{index} [{severity.upper()}] {title}</div>
        <div class="finding-meta">📍 {endpoint}</div>
        <p>{description}</p>'''
    
    if payload:
        html += f'<div class="payload">💉 {payload}</div>'
    
    if evidence:
        preview = evidence[:300] + "..." if len(evidence) > 300 else evidence
        html += f'<div class="finding-meta" style="margin-top:10px;">📋 {preview}</div>'
    
    html += '</div>'
    return html


def markdown_template(
    title: str,
    target: str,
    findings: List[Dict],
    stats: Dict,
) -> str:
    """
    Generate Markdown report.
    
    Returns:
        Markdown string
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md = f"""# {title}

**Target:** {target}  
**Generated:** {timestamp}  
**Tool:** SENTINEL Strike v3.0

---

## Summary

| Metric | Value |
|--------|-------|
| Total Findings | {len(findings)} |
| Requests | {stats.get("requests", 0)} |
| Blocked | {stats.get("blocked", 0)} |
| Bypasses | {stats.get("bypasses", 0)} |

---

## Findings

"""
    
    for i, finding in enumerate(findings, 1):
        severity = finding.get("severity", "medium").upper()
        title = finding.get("title", finding.get("type", "Finding"))
        endpoint = finding.get("endpoint", "")
        description = finding.get("description", "")
        payload = finding.get("payload", "")
        
        md += f"""### {i}. [{severity}] {title}

**Endpoint:** `{endpoint}`

{description}

"""
        if payload:
            md += f"**Payload:**\n```\n{payload}\n```\n\n"
        
        md += "---\n\n"
    
    return md
