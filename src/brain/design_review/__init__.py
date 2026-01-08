"""
AI Design Review Module

Analyzes architecture documents for AI security risks.

Generated: 2026-01-08
"""

from .reviewer import (
    RiskCategory,
    Severity,
    DesignRisk,
    DesignReviewResult,
    DesignRiskPatterns,
    DesignReviewer,
    get_reviewer,
    review_text,
    review_documents,
)

__all__ = [
    "RiskCategory",
    "Severity",
    "DesignRisk",
    "DesignReviewResult",
    "DesignRiskPatterns",
    "DesignReviewer",
    "get_reviewer",
    "review_text",
    "review_documents",
]
