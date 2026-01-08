"""
Unit Tests for Compliance Report Generator

Tests for compliance mappings and report generation.

Generated: 2026-01-08
"""

import pytest
from datetime import datetime

from brain.compliance import (
    ComplianceFramework,
    CoverageStatus,
    ComplianceRequirement,
    FrameworkCoverage,
    ComplianceReport,
    ComplianceReportGenerator,
    generate_report,
    generate_text_report,
)


class TestComplianceFramework:
    """Tests for ComplianceFramework enum."""
    
    def test_all_frameworks_defined(self):
        assert ComplianceFramework.OWASP_LLM.value == "owasp_llm"
        assert ComplianceFramework.OWASP_AGENTIC.value == "owasp_agentic"
        assert ComplianceFramework.EU_AI_ACT.value == "eu_ai_act"
        assert ComplianceFramework.NIST_AI_RMF.value == "nist_ai_rmf"


class TestFrameworkCoverage:
    """Tests for FrameworkCoverage calculations."""
    
    def test_coverage_percent_all_covered(self):
        fc = FrameworkCoverage(
            framework=ComplianceFramework.OWASP_LLM,
            total_requirements=10,
            covered=10,
            partial=0,
            not_covered=0,
            not_applicable=0
        )
        assert fc.coverage_percent == 100.0
    
    def test_coverage_percent_with_partial(self):
        fc = FrameworkCoverage(
            framework=ComplianceFramework.OWASP_LLM,
            total_requirements=10,
            covered=5,
            partial=4,
            not_covered=1,
            not_applicable=0
        )
        # 5 + 4*0.5 = 7, 7/10 = 70%
        assert fc.coverage_percent == 70.0
    
    def test_coverage_percent_with_na(self):
        fc = FrameworkCoverage(
            framework=ComplianceFramework.NIST_AI_RMF,
            total_requirements=10,
            covered=8,
            partial=0,
            not_covered=0,
            not_applicable=2
        )
        # 8 applicable, 8 covered = 100%
        assert fc.coverage_percent == 100.0


class TestComplianceReportGenerator:
    """Tests for report generation."""
    
    def test_owasp_llm_coverage(self):
        generator = ComplianceReportGenerator()
        fc = generator.get_framework_coverage(ComplianceFramework.OWASP_LLM)
        
        assert fc.total_requirements == 10
        assert fc.covered + fc.partial >= 6  # At least 60% coverage
    
    def test_owasp_agentic_coverage(self):
        generator = ComplianceReportGenerator()
        fc = generator.get_framework_coverage(ComplianceFramework.OWASP_AGENTIC)
        
        assert fc.total_requirements == 10
        assert fc.covered >= 5  # At least 50% fully covered
    
    def test_generate_report(self):
        report = generate_report()
        
        assert report.target == "SENTINEL"
        assert len(report.frameworks) == 4
        assert len(report.requirements) > 0
        assert report.summary is not None
    
    def test_generate_text_report(self):
        text = generate_text_report()
        
        assert "SENTINEL Compliance Report" in text
        assert "OWASP" in text
        assert "%" in text
    
    def test_report_to_dict(self):
        report = generate_report()
        data = report.to_dict()
        
        assert "generated_at" in data
        assert "frameworks" in data
        assert "requirements" in data
        assert "summary" in data


class TestComplianceMappings:
    """Tests for compliance requirement mappings."""
    
    def test_owasp_llm_has_all_10(self):
        generator = ComplianceReportGenerator()
        reqs = generator.requirements[ComplianceFramework.OWASP_LLM]
        
        ids = [r.id for r in reqs]
        for i in range(1, 11):
            expected = f"LLM{i:02d}"
            assert expected in ids, f"Missing {expected}"
    
    def test_owasp_agentic_has_all_10(self):
        generator = ComplianceReportGenerator()
        reqs = generator.requirements[ComplianceFramework.OWASP_AGENTIC]
        
        ids = [r.id for r in reqs]
        for i in range(1, 11):
            expected = f"ASI{i:02d}"
            assert expected in ids, f"Missing {expected}"
    
    def test_eu_ai_act_has_key_articles(self):
        generator = ComplianceReportGenerator()
        reqs = generator.requirements[ComplianceFramework.EU_AI_ACT]
        
        ids = [r.id for r in reqs]
        assert "EU-ART-9" in ids  # Risk Management
        assert "EU-ART-14" in ids  # Human Oversight
        assert "EU-ART-15" in ids  # Security
    
    def test_requirements_have_engines(self):
        generator = ComplianceReportGenerator()
        
        # Check that covered requirements have engines
        for framework, reqs in generator.requirements.items():
            for req in reqs:
                if req.status == CoverageStatus.COVERED:
                    assert len(req.engines) > 0 or req.engines == ["all_engines"], \
                        f"{req.id} is COVERED but has no engines"
