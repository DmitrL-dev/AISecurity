"""
SENTINEL Strike Dashboard Reports

Report generation extracted from strike_console.py
"""

from .generator import ReportGenerator, generate_report
from .templates import report_template, finding_template

__all__ = [
    "ReportGenerator",
    "generate_report",
    "report_template",
    "finding_template",
]
