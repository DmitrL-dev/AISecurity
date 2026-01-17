"""
SENTINEL Strike Dashboard - Report Generator

Generates professional penetration test reports.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .templates import report_template, markdown_template

# Import state
try:
    from strike.dashboard.state import file_logger
except ImportError:
    from ..state import file_logger


class ReportGenerator:
    """
    Professional penetration test report generator.
    
    Generates reports from attack logs in multiple formats.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize report generator.
        
        Args:
            output_dir: Directory for generated reports
        """
        self.output_dir = output_dir or Path(__file__).parent.parent.parent / "reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        title: str,
        target: str,
        findings: List[Dict],
        stats: Optional[Dict] = None,
        format: str = "html",
        executive_summary: str = "",
    ) -> Path:
        """
        Generate report.
        
        Args:
            title: Report title
            target: Target URL
            findings: List of findings
            stats: Attack statistics
            format: Output format (html, md, json)
            executive_summary: Optional executive summary
            
        Returns:
            Path to generated report
        """
        stats = stats or {"requests": 0, "blocked": 0, "bypasses": 0}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "html":
            content = report_template(title, target, findings, stats, executive_summary)
            filename = f"report_{timestamp}.html"
        elif format == "md":
            content = markdown_template(title, target, findings, stats)
            filename = f"report_{timestamp}.md"
        elif format == "json":
            data = {
                "title": title,
                "target": target,
                "generated": datetime.now().isoformat(),
                "stats": stats,
                "findings": findings,
            }
            content = json.dumps(data, indent=2, ensure_ascii=False)
            filename = f"report_{timestamp}.json"
        else:
            raise ValueError(f"Unknown format: {format}")
        
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def generate_from_log(
        self,
        log_file: Optional[Path] = None,
        format: str = "html",
    ) -> Path:
        """
        Generate report from attack log file.
        
        Args:
            log_file: Path to JSONL log file. Uses latest if not specified.
            format: Output format
            
        Returns:
            Path to generated report
        """
        # Use latest log if not specified
        if log_file is None:
            log_file = file_logger.log_file
        
        if not log_file.exists():
            raise FileNotFoundError(f"Log file not found: {log_file}")
        
        # Parse log
        findings = []
        target = ""
        stats = {"requests": 0, "blocked": 0, "bypasses": 0, "findings": 0}
        
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line)
                    event_type = event.get("type", "")
                    
                    if event_type == "attack_start":
                        target = event.get("target", "")
                    elif event_type == "request":
                        stats["requests"] += 1
                    elif event_type == "blocked":
                        stats["blocked"] += 1
                    elif event_type == "bypass":
                        stats["bypasses"] += 1
                    elif event_type == "finding":
                        stats["findings"] += 1
                        findings.append(event)
                except json.JSONDecodeError:
                    continue
        
        title = f"Penetration Test Report - {target}"
        return self.generate(title, target, findings, stats, format)
    
    def list_reports(self) -> List[Dict]:
        """
        List all generated reports.
        
        Returns:
            List of report info dictionaries
        """
        reports = []
        for f in sorted(self.output_dir.glob("report_*"), reverse=True):
            reports.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                "format": f.suffix[1:],  # Remove leading dot
            })
        return reports


# Global instance
report_generator = ReportGenerator()


def generate_report(
    findings: List[Dict],
    target: str = "",
    format: str = "html",
) -> Path:
    """
    Convenience function to generate report.
    
    Args:
        findings: List of findings
        target: Target URL
        format: Output format
        
    Returns:
        Path to generated report
    """
    return report_generator.generate(
        title=f"Penetration Test Report - {target}",
        target=target,
        findings=findings,
        format=format,
    )
