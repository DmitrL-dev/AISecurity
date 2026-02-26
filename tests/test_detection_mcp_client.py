#!/usr/bin/env python3
"""Unit tests for Security Detections MCP Client."""

import pytest

from src.brain.integrations.detection_mcp_client import (
    SecurityDetectionsMCPClient,
    SENTINELDetectionBridge,
    DetectionSourceType,
    DetectionRule,
    MCPToolCall,
)


class TestSecurityDetectionsMCPClient:
    """Tests for SecurityDetectionsMCPClient."""
    
    def test_search_creates_tool_call(self):
        """Test search method creates proper tool call."""
        client = SecurityDetectionsMCPClient()
        
        call = client.search("powershell", limit=10)
        
        assert isinstance(call, MCPToolCall)
        assert call.tool_name == "search"
        assert call.arguments["query"] == "powershell"
        assert call.arguments["limit"] == 10
    
    def test_list_by_cve(self):
        """Test CVE lookup."""
        client = SecurityDetectionsMCPClient()
        
        call = client.list_by_cve("CVE-2021-44228")
        
        assert call.tool_name == "list_by_cve"
        assert call.arguments["cve_id"] == "CVE-2021-44228"
    
    def test_list_by_mitre(self):
        """Test MITRE technique lookup."""
        client = SecurityDetectionsMCPClient()
        
        call = client.list_by_mitre("T1059.001")
        
        assert call.tool_name == "list_by_mitre"
        assert call.arguments["technique_id"] == "T1059.001"
    
    def test_list_by_mitre_tactic(self):
        """Test MITRE tactic lookup."""
        client = SecurityDetectionsMCPClient()
        
        call = client.list_by_mitre_tactic("execution")
        
        assert call.tool_name == "list_by_mitre_tactic"
        assert call.arguments["tactic"] == "execution"
    
    def test_list_by_source(self):
        """Test source type filter."""
        client = SecurityDetectionsMCPClient()
        
        call = client.list_by_source(DetectionSourceType.SIGMA)
        
        assert call.tool_name == "list_by_source"
        assert call.arguments["source_type"] == "sigma"
    
    def test_analyze_coverage(self):
        """Test coverage analysis."""
        client = SecurityDetectionsMCPClient()
        
        call = client.analyze_coverage(DetectionSourceType.KQL)
        
        assert call.tool_name == "analyze_coverage"
        assert call.arguments["source_type"] == "kql"
    
    def test_identify_gaps(self):
        """Test gap identification."""
        client = SecurityDetectionsMCPClient()
        
        call = client.identify_gaps(["T1059", "T1055"])
        
        assert call.tool_name == "identify_gaps"
        assert call.arguments["threat_profile"] == ["T1059", "T1055"]
    
    def test_suggest_detections(self):
        """Test detection suggestions."""
        client = SecurityDetectionsMCPClient()
        
        call = client.suggest_detections("T1059", DetectionSourceType.SIGMA)
        
        assert call.tool_name == "suggest_detections"
        assert call.arguments["technique_id"] == "T1059"
        assert call.arguments["source_type"] == "sigma"
    
    def test_generate_navigator_layer(self):
        """Test ATT&CK Navigator layer generation."""
        client = SecurityDetectionsMCPClient()
        
        call = client.generate_navigator_layer("SENTINEL Coverage")
        
        assert call.tool_name == "generate_navigator_layer"
        assert call.arguments["name"] == "SENTINEL Coverage"
    
    def test_tool_call_to_json(self):
        """Test MCPToolCall JSON serialization."""
        call = MCPToolCall(
            tool_name="search",
            arguments={"query": "test"}
        )
        
        json_str = call.to_json()
        
        assert '"tool": "search"' in json_str
        assert '"query": "test"' in json_str


class TestSENTINELDetectionBridge:
    """Tests for SENTINEL-specific bridge."""
    
    def test_find_detections_for_cve(self):
        """Test CVE threat lookup."""
        bridge = SENTINELDetectionBridge()
        
        calls = bridge.find_detections_for_threat("CVE-2021-44228")
        
        assert len(calls) == 1
        assert calls[0].tool_name == "list_by_cve"
    
    def test_find_detections_for_owasp_llm(self):
        """Test OWASP LLM mapping."""
        bridge = SENTINELDetectionBridge()
        
        calls = bridge.find_detections_for_threat("LLM01")
        
        assert len(calls) >= 1
        assert all(c.tool_name == "list_by_mitre" for c in calls)
    
    def test_find_detections_for_owasp_asi(self):
        """Test OWASP ASI mapping."""
        bridge = SENTINELDetectionBridge()
        
        calls = bridge.find_detections_for_threat("ASI01")
        
        assert len(calls) >= 1
        assert all(c.tool_name == "list_by_mitre" for c in calls)
    
    def test_find_detections_generic_search(self):
        """Test generic search fallback."""
        bridge = SENTINELDetectionBridge()
        
        calls = bridge.find_detections_for_threat("ransomware")
        
        assert len(calls) == 1
        assert calls[0].tool_name == "search"
    
    def test_map_owasp_to_detections(self):
        """Test OWASP to gap analysis."""
        bridge = SENTINELDetectionBridge()
        
        call = bridge.map_owasp_to_detections("LLM01")
        
        assert call.tool_name == "identify_gaps"
        assert "T1059" in call.arguments["threat_profile"]
    
    def test_search_ai_security_detections(self):
        """Test AI security search."""
        bridge = SENTINELDetectionBridge()
        
        calls = bridge.search_ai_security_detections()
        
        assert len(calls) >= 5
        assert all(c.tool_name == "search" for c in calls)
    
    def test_owasp_llm_mapping_completeness(self):
        """Test all OWASP LLM IDs have mappings."""
        bridge = SENTINELDetectionBridge()
        
        for i in range(1, 11):
            owasp_id = f"LLM{i:02d}"
            assert owasp_id in bridge.OWASP_TO_MITRE
    
    def test_owasp_asi_mapping_completeness(self):
        """Test all OWASP ASI IDs have mappings."""
        bridge = SENTINELDetectionBridge()
        
        for i in range(1, 11):
            owasp_id = f"ASI{i:02d}"
            assert owasp_id in bridge.OWASP_ASI_TO_MITRE


class TestDetectionRule:
    """Tests for DetectionRule dataclass."""
    
    def test_detection_rule_creation(self):
        """Test DetectionRule creation."""
        rule = DetectionRule(
            id="test-001",
            title="Test Rule",
            description="A test rule",
            source_type="sigma",
            severity="high",
            mitre_techniques=["T1059"],
        )
        
        assert rule.id == "test-001"
        assert rule.severity == "high"
    
    def test_detection_rule_to_dict(self):
        """Test DetectionRule serialization."""
        rule = DetectionRule(
            id="test-001",
            title="Test Rule",
            description="A test rule",
            source_type="sigma",
            severity="high",
        )
        
        data = rule.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == "test-001"
        assert data["severity"] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
