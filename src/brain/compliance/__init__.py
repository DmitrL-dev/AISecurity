"""
Compliance Module

Unified compliance reporting across frameworks.

Generated: 2026-01-08
"""

from .report_generator import (
    ComplianceFramework,
    CoverageStatus,
    ComplianceRequirement,
    FrameworkCoverage,
    ComplianceReport,
    ComplianceReportGenerator,
    generate_report,
    generate_text_report,
    get_generator,
)

__all__ = [
    "ComplianceFramework",
    "CoverageStatus",
    "ComplianceRequirement",
    "FrameworkCoverage",
    "ComplianceReport",
    "ComplianceReportGenerator",
    "generate_report",
    "generate_text_report",
    "get_generator",
]
