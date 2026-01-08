"""
Unit Tests for AI Design Review

Tests for pattern detection and risk assessment.

Generated: 2026-01-08
"""

import pytest
from datetime import datetime

from brain.design_review import (
    RiskCategory,
    Severity,
    DesignRisk,
    DesignReviewResult,
    DesignReviewer,
    review_text,
    review_documents,
)


class TestDesignReviewer:
    """Tests for DesignReviewer."""
    
    def test_detect_rag_architecture(self):
        text = "This system uses RAG with a vector database for document retrieval."
        
        reviewer = DesignReviewer()
        risks = reviewer.review_text(text, "test.md")
        
        rag_risks = [r for r in risks if r.category == RiskCategory.RAG_POISONING]
        assert len(rag_risks) > 0
    
    def test_detect_mcp_tools(self):
        text = "The agent uses MCP tools for file system access and shell execution."
        
        risks = review_text(text)
        
        mcp_risks = [r for r in risks if r.category == RiskCategory.MCP_ABUSE]
        assert len(mcp_risks) >= 2  # file + shell
    
    def test_detect_shell_execution_critical(self):
        text = "The system can execute shell commands and subprocess calls."
        
        risks = review_text(text)
        
        critical = [r for r in risks if r.severity == Severity.CRITICAL]
        assert len(critical) > 0
    
    def test_detect_agent_patterns(self):
        text = "This autonomous agent uses recursive loops and persistent memory."
        
        risks = review_text(text)
        
        agent_risks = [r for r in risks if r.category == RiskCategory.AGENT_LOOP]
        assert len(agent_risks) >= 2  # autonomous + loop
    
    def test_detect_data_patterns(self):
        text = "We store PII in logs and share data with third-party APIs."
        
        risks = review_text(text)
        
        data_risks = [r for r in risks if r.category == RiskCategory.DATA_LEAKAGE]
        assert len(data_risks) >= 2
    
    def test_detect_supply_chain(self):
        text = "Load model from HuggingFace with trust_remote_code=True using pickle."
        
        risks = review_text(text)
        
        supply_risks = [r for r in risks if r.category == RiskCategory.SUPPLY_CHAIN]
        assert len(supply_risks) >= 2  # huggingface + pickle/trust
        
        # Pickle should be critical
        pickle_risks = [r for r in supply_risks if "pickle" in r.location.lower()]
        assert any(r.severity == Severity.CRITICAL for r in pickle_risks)
    
    def test_no_risks_clean_doc(self):
        text = "This is a simple web application that displays static content."
        
        risks = review_text(text)
        
        # Should have minimal or no AI-specific risks
        assert len(risks) <= 1
    
    def test_review_documents(self):
        docs = [
            {"name": "arch.md", "content": "RAG pipeline with vector database"},
            {"name": "api.yaml", "content": "MCP tool definitions for file access"},
        ]
        
        result = review_documents(docs)
        
        assert result.reviewed_at is not None
        assert len(result.documents) == 2
        assert len(result.risks) > 0
        assert result.risk_score > 0
    
    def test_risk_score_calculation(self):
        docs = [
            {"name": "dangerous.md", "content": """
                Shell command execution
                Pickle serialization
                Trust remote code
                Critical data handling
            """}
        ]
        
        result = review_documents(docs)
        
        # Should have high risk score
        assert result.risk_score >= 50
    
    def test_summary_generation(self):
        docs = [
            {"name": "test.md", "content": "RAG with MCP tools"}
        ]
        
        result = review_documents(docs)
        
        assert "Reviewed 1 document" in result.summary
        assert "risks" in result.summary.lower()


class TestDesignRisk:
    """Tests for DesignRisk model."""
    
    def test_risk_has_owasp_mapping(self):
        text = "MCP tools for file access"
        
        risks = review_text(text)
        
        for risk in risks:
            assert len(risk.owasp_mapping) > 0, f"Risk {risk.id} has no OWASP mapping"
    
    def test_risk_has_recommendation(self):
        text = "RAG with document ingestion"
        
        risks = review_text(text)
        
        for risk in risks:
            assert risk.recommendation, f"Risk {risk.id} has no recommendation"


class TestDesignReviewResult:
    """Tests for DesignReviewResult."""
    
    def test_to_dict(self):
        result = review_documents([{"name": "test.md", "content": "RAG pipeline"}])
        
        data = result.to_dict()
        
        assert "reviewed_at" in data
        assert "documents" in data
        assert "risks" in data
        assert "risk_score" in data
        assert "summary" in data
    
    def test_risk_count_by_severity(self):
        result = review_documents([{
            "name": "critical.md",
            "content": "shell exec, pickle, trust_remote_code, RAG"
        }])
        
        counts = result.risk_count_by_severity
        
        assert "critical" in counts
        assert "high" in counts
        assert "medium" in counts
        assert "low" in counts
