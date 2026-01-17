# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Sequential Tool Attack Chaining (STAC) Detector
"""

import pytest
from src.brain.engines.stac_detector import (
    STACDetector,
    ToolCategory,
    analyze_tool_sequence,
    create_stac_monitor,
)


class TestToolCategorization:
    """Test tool categorization."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_file_read_tools(self):
        """File read tools should be categorized correctly."""
        assert self.detector.categorize_tool("read_file") == ToolCategory.FILE_READ
        assert self.detector.categorize_tool("view_file") == ToolCategory.FILE_READ
        assert self.detector.categorize_tool("cat") == ToolCategory.FILE_READ
    
    def test_network_tools(self):
        """Network tools should be categorized correctly."""
        assert self.detector.categorize_tool("http_request") == ToolCategory.NETWORK_REQUEST
        assert self.detector.categorize_tool("curl") == ToolCategory.NETWORK_REQUEST
        assert self.detector.categorize_tool("fetch") == ToolCategory.NETWORK_REQUEST
    
    def test_credential_tools(self):
        """Credential tools should be categorized correctly."""
        assert self.detector.categorize_tool("get_credentials") == ToolCategory.CREDENTIALS_ACCESS
        assert self.detector.categorize_tool("read_secrets") == ToolCategory.CREDENTIALS_ACCESS
    
    def test_unknown_tools(self):
        """Unknown tools should return UNKNOWN category."""
        assert self.detector.categorize_tool("random_tool_xyz") == ToolCategory.UNKNOWN
    
    def test_heuristic_categorization(self):
        """Heuristic categorization should work for similar tool names."""
        assert self.detector.categorize_tool("read_document") == ToolCategory.FILE_READ
        assert self.detector.categorize_tool("make_http_call") == ToolCategory.NETWORK_REQUEST


class TestTwoStepPatterns:
    """Test two-step attack chain detection."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_file_read_then_network_exfil(self):
        """Detect file read followed by network request as exfiltration."""
        result = self.detector.analyze_sequence([
            "read_file",
            "http_request"
        ])
        
        assert result.is_attack_chain
        assert result.highest_severity == "CRITICAL"
        assert any(c.chain_type == "data_exfiltration" for c in result.chains_detected)
    
    def test_credentials_then_network_exfil(self):
        """Detect credentials access followed by network request."""
        result = self.detector.analyze_sequence([
            "get_credentials",
            "curl"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "credential_theft" for c in result.chains_detected)
    
    def test_network_then_file_write_payload(self):
        """Detect payload download pattern."""
        result = self.detector.analyze_sequence([
            "fetch",
            "write_file"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "payload_download" for c in result.chains_detected)
    
    def test_env_then_network_exfil(self):
        """Detect environment exfiltration."""
        result = self.detector.analyze_sequence([
            "get_env",
            "api_call"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "env_exfiltration" for c in result.chains_detected)
    
    def test_search_then_file_read(self):
        """Detect targeted file access after search."""
        result = self.detector.analyze_sequence([
            "search",
            "read_file"
        ])
        
        assert result.is_attack_chain
        assert result.highest_severity == "MEDIUM"
    
    def test_file_read_then_delete(self):
        """Detect data destruction pattern."""
        result = self.detector.analyze_sequence([
            "view_file",
            "delete_file"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "data_destruction" for c in result.chains_detected)


class TestThreeStepPatterns:
    """Test three-step attack chain detection."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_search_read_exfil_chain(self):
        """Detect search → read → exfiltrate chain."""
        result = self.detector.analyze_sequence([
            "grep",
            "read_file",
            "http_request"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "reconnaissance_exfiltration" for c in result.chains_detected)
    
    def test_download_execute_persist_chain(self):
        """Detect download → execute → persist chain."""
        result = self.detector.analyze_sequence([
            "curl",
            "python_exec",
            "write_file"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "remote_code_persistence" for c in result.chains_detected)
    
    def test_creds_query_exfil_chain(self):
        """Detect credentials → query → exfiltrate chain."""
        result = self.detector.analyze_sequence([
            "get_credentials",
            "sql_query",
            "webhook"
        ])
        
        assert result.is_attack_chain
        assert any(c.chain_type == "privileged_data_theft" for c in result.chains_detected)


class TestBenignSequences:
    """Ensure benign patterns don't trigger false positives."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_normal_file_operations(self):
        """Normal file operations should not trigger."""
        result = self.detector.analyze_sequence([
            "read_file",
            "write_file"
        ])
        
        # This could be benign copy operation
        # Should not trigger critical exfiltration
        if result.is_attack_chain:
            assert result.highest_severity != "CRITICAL"
    
    def test_search_only(self):
        """Single search should not trigger."""
        result = self.detector.analyze_sequence([
            "search"
        ])
        
        assert not result.is_attack_chain
    
    def test_unrelated_tools(self):
        """Unrelated tools should not form attack chain."""
        result = self.detector.analyze_sequence([
            "unknown_tool_1",
            "unknown_tool_2"
        ])
        
        assert not result.is_attack_chain


class TestContinuousMonitoring:
    """Test continuous monitoring capabilities."""
    
    def test_incremental_tool_addition(self):
        """Test adding tools incrementally."""
        detector = create_stac_monitor()
        
        detector.add_tool_call("search")
        result1 = detector.analyze_sequence()
        assert not result1.is_attack_chain
        
        detector.add_tool_call("read_file")
        result2 = detector.analyze_sequence()
        assert result2.is_attack_chain
        
        detector.add_tool_call("http_request")
        result3 = detector.analyze_sequence()
        assert result3.is_attack_chain
        assert any(c.chain_type == "reconnaissance_exfiltration" for c in result3.chains_detected)
    
    def test_window_size_limit(self):
        """Test that window size is respected."""
        detector = STACDetector(window_size=3)
        
        # Add more tools than window size
        for i in range(5):
            detector.add_tool_call(f"tool_{i}")
        
        assert len(detector.tool_history) == 3
    
    def test_reset_clears_history(self):
        """Test reset clears tool history."""
        detector = create_stac_monitor()
        detector.add_tool_call("read_file")
        detector.add_tool_call("http_request")
        
        detector.reset()
        
        assert len(detector.tool_history) == 0


class TestRiskScoreCalculation:
    """Test risk score calculation."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_critical_chain_high_risk(self):
        """Critical chains should have high risk score."""
        result = self.detector.analyze_sequence([
            "get_credentials",
            "http_request"
        ])
        
        assert result.risk_score >= 0.4
    
    def test_multiple_chains_higher_risk(self):
        """Multiple chains should increase risk score."""
        result = self.detector.analyze_sequence([
            "get_credentials",
            "sql_query",
            "http_request"
        ])
        
        # Should detect both two-step and three-step patterns
        assert len(result.chains_detected) >= 2


class TestRecommendations:
    """Test security recommendations generation."""
    
    def setup_method(self):
        self.detector = STACDetector()
    
    def test_exfil_recommendations(self):
        """Exfiltration patterns should generate DLP recommendations."""
        result = self.detector.analyze_sequence([
            "read_file",
            "http_request"
        ])
        
        assert len(result.recommendations) > 0
        assert any("DLP" in r or "network" in r.lower() for r in result.recommendations)
    
    def test_credential_recommendations(self):
        """Credential patterns should generate isolation recommendations."""
        result = self.detector.analyze_sequence([
            "get_credentials",
            "curl"
        ])
        
        assert len(result.recommendations) > 0
        assert any("credential" in r.lower() for r in result.recommendations)


class TestConvenienceFunction:
    """Test convenience functions."""
    
    def test_analyze_tool_sequence_returns_dict(self):
        """analyze_tool_sequence should return proper dict."""
        result = analyze_tool_sequence(["read_file", "http_request"])
        
        assert isinstance(result, dict)
        assert "is_attack_chain" in result
        assert "risk_score" in result
        assert "chains" in result
        assert "recommendations" in result
    
    def test_mitre_mapping_included(self):
        """MITRE ATT&CK mappings should be included."""
        result = analyze_tool_sequence(["read_file", "http_request"])
        
        assert any(c.get("mitre") for c in result["chains"])
