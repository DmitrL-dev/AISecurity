"""
SENTINEL Strike — Reporting Module

Professional pentest report generation with:
- MITRE ATT&CK mapping
- Modern HTML templates
- Chart.js visualization
- Auto-generation from attack logs
"""

from .report_generator import (
    StrikeReportGenerator,
    ReportData,
    Finding,
    MITRE_MAPPING,
)

__all__ = [
    "StrikeReportGenerator",
    "ReportData",
    "Finding",
    "MITRE_MAPPING",
]
