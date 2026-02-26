"""
SENTINEL Strike Dashboard - UI Components

HTML formatters and generators for the dashboard.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from html import escape

from .themes import LOG_CLASSES, SEVERITY_CLASSES


def format_log_entry(
    message: str,
    log_type: str = "info",
    timestamp: Optional[datetime] = None,
) -> str:
    """
    Format a log message as HTML.
    
    Args:
        message: Log message text
        log_type: Type of log (info, success, warning, error, attack, bypass, stealth)
        timestamp: Optional timestamp (uses now if not provided)
        
    Returns:
        HTML string for the log entry
    """
    ts = timestamp or datetime.now()
    css_class = LOG_CLASSES.get(log_type, "log-info")
    
    return f'''<div class="log-entry">
        <span class="log-time">[{ts.strftime("%H:%M:%S")}]</span>
        <span class="{css_class}">{escape(message)}</span>
    </div>'''


def format_finding(
    title: str,
    severity: str,
    endpoint: str,
    description: str,
    payload: str = "",
    evidence: str = "",
) -> str:
    """
    Format a security finding as HTML.
    
    Args:
        title: Finding title
        severity: Severity level (critical, high, medium, low, info)
        endpoint: Affected endpoint
        description: Finding description
        payload: Payload used (optional)
        evidence: Response evidence (optional)
        
    Returns:
        HTML string for the finding
    """
    css_class = SEVERITY_CLASSES.get(severity.lower(), "finding medium")
    severity_upper = severity.upper()
    
    html = f'''<div class="{css_class}">
        <div class="finding-title">[{severity_upper}] {escape(title)}</div>
        <div class="finding-endpoint" style="color:#8b949e;font-size:0.85rem;">
            📍 {escape(endpoint)}
        </div>
        <div class="finding-desc" style="margin-top:8px;">
            {escape(description)}
        </div>'''
    
    if payload:
        html += f'''
        <div class="finding-payload" style="margin-top:8px;background:#0d1117;padding:8px;border-radius:4px;font-family:monospace;font-size:0.8rem;">
            💉 {escape(payload[:200])}{"..." if len(payload) > 200 else ""}
        </div>'''
    
    if evidence:
        html += f'''
        <div class="finding-evidence" style="margin-top:8px;color:#8b949e;font-size:0.8rem;">
            📋 Evidence: {escape(evidence[:150])}{"..." if len(evidence) > 150 else ""}
        </div>'''
    
    html += '</div>'
    return html


def format_stats(stats: Dict[str, int]) -> str:
    """
    Format attack statistics as HTML.
    
    Args:
        stats: Dictionary with stats (requests, blocked, bypasses, findings)
        
    Returns:
        HTML string for stats grid
    """
    return f'''<div class="stats-grid">
        <div class="stat-box">
            <div class="stat-value" style="color:#58a6ff;">{stats.get("requests", 0)}</div>
            <div class="stat-label">Requests</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color:#d29922;">{stats.get("blocked", 0)}</div>
            <div class="stat-label">Blocked</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color:#a371f7;">{stats.get("bypasses", 0)}</div>
            <div class="stat-label">Bypasses</div>
        </div>
        <div class="stat-box">
            <div class="stat-value" style="color:#f85149;">{stats.get("findings", 0)}</div>
            <div class="stat-label">Findings</div>
        </div>
    </div>'''


def format_progress_bar(
    current: int,
    total: int,
    width: int = 100,
    color: str = "#58a6ff",
) -> str:
    """
    Format a progress bar as HTML.
    
    Args:
        current: Current progress value
        total: Total value
        width: Bar width in percent
        color: Bar color
        
    Returns:
        HTML string for progress bar
    """
    pct = min(100, int((current / max(total, 1)) * 100))
    
    return f'''<div class="progress-bar" style="
        background:#0d1117;
        border-radius:4px;
        height:8px;
        width:{width}%;
    ">
        <div style="
            width:{pct}%;
            height:100%;
            background:{color};
            border-radius:4px;
            transition:width 0.3s ease;
        "></div>
    </div>
    <div style="color:#8b949e;font-size:0.75rem;margin-top:4px;">
        {current}/{total} ({pct}%)
    </div>'''


def format_attack_card(
    attack_type: str,
    status: str,
    payloads_tested: int,
    findings: int,
) -> str:
    """
    Format an attack type card as HTML.
    
    Args:
        attack_type: Type of attack (sqli, xss, etc.)
        status: Status (running, completed, skipped)
        payloads_tested: Number of payloads tested
        findings: Number of findings
        
    Returns:
        HTML string for attack card
    """
    status_colors = {
        "running": "#58a6ff",
        "completed": "#3fb950",
        "skipped": "#8b949e",
        "blocked": "#d29922",
    }
    color = status_colors.get(status, "#8b949e")
    
    icons = {
        "sqli": "💉",
        "xss": "🔥",
        "lfi": "📂",
        "ssrf": "🌐",
        "cmdi": "💻",
        "ssti": "📝",
        "xxe": "📄",
        "nosql": "🗃️",
    }
    icon = icons.get(attack_type.lower(), "⚡")
    
    return f'''<div class="attack-card" style="
        background:#0d1117;
        border:1px solid #30363d;
        border-left:3px solid {color};
        padding:12px;
        margin:8px 0;
        border-radius:0 6px 6px 0;
    ">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:bold;">{icon} {attack_type.upper()}</span>
            <span style="color:{color};font-size:0.85rem;">{status}</span>
        </div>
        <div style="color:#8b949e;font-size:0.8rem;margin-top:4px;">
            {payloads_tested} payloads • {findings} findings
        </div>
    </div>'''


def format_json_response(data: Any, indent: int = 2) -> str:
    """
    Format JSON data as styled HTML.
    
    Args:
        data: Data to format
        indent: JSON indentation
        
    Returns:
        HTML string with syntax highlighting
    """
    import json
    
    json_str = json.dumps(data, indent=indent, ensure_ascii=False)
    # Basic syntax highlighting
    json_str = escape(json_str)
    
    return f'''<pre style="
        background:#0d1117;
        border:1px solid #30363d;
        border-radius:6px;
        padding:12px;
        overflow-x:auto;
        font-family:'JetBrains Mono',monospace;
        font-size:0.85rem;
    ">{json_str}</pre>'''
