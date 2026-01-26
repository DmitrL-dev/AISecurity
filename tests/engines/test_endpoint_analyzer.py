"""
Tests for Endpoint Analyzer.
"""

from engines.endpoint_analyzer import (
    EndpointAnalyzer,
    EndpointProbeResult,
    EndpointAnalysisResult,
    ProbeType,
    Protocol,
    ProbeEngine,
    A2AProtocolHandler,
    MCPProtocolHandler,
)
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))


class TestEndpointProbeResult:
    """Test EndpointProbeResult dataclass."""

    def test_to_dict(self):
        result = EndpointProbeResult(
            probe_type=ProbeType.IDENTITY,
            success=True,
            response_time_ms=10.5,
            findings=["test finding"],
        )
        d = result.to_dict()

        assert d["probe_type"] == "identity"
        assert d["success"] is True
        assert d["response_time_ms"] == 10.5
        assert "test finding" in d["findings"]


class TestEndpointAnalysisResult:
    """Test EndpointAnalysisResult dataclass."""

    def test_to_dict(self):
        result = EndpointAnalysisResult(
            endpoint_url="http://test.com",
            protocol=Protocol.A2A,
            is_safe=True,
            risk_score=25.5,
        )
        d = result.to_dict()

        assert d["endpoint_url"] == "http://test.com"
        assert d["protocol"] == "a2a"
        assert d["is_safe"] is True
        assert d["risk_score"] == 25.5


class TestEndpointAnalyzer:
    """Test main EndpointAnalyzer class."""

    def test_init(self):
        analyzer = EndpointAnalyzer()
        assert analyzer.timeout == 10.0
        assert analyzer.probe_engine is not None

    def test_detect_protocol_a2a(self):
        analyzer = EndpointAnalyzer()
        assert analyzer.detect_protocol(
            "http://agent.com/.well-known/agent.json"
        ) == Protocol.A2A

    def test_detect_protocol_mcp(self):
        analyzer = EndpointAnalyzer()
        assert analyzer.detect_protocol(
            "http://localhost:3000/mcp"
        ) == Protocol.MCP

    def test_detect_protocol_http(self):
        analyzer = EndpointAnalyzer()
        assert analyzer.detect_protocol(
            "http://api.example.com"
        ) == Protocol.HTTP

    def test_calculate_risk_empty(self):
        analyzer = EndpointAnalyzer()
        assert analyzer._calculate_risk([]) == 0.0

    def test_calculate_risk_safe(self):
        analyzer = EndpointAnalyzer()
        results = [
            EndpointProbeResult(
                probe_type=ProbeType.IDENTITY,
                success=True,
                response_time_ms=10.0,
            )
        ]
        assert analyzer._calculate_risk(results) < 50.0

    def test_calculate_risk_injection(self):
        analyzer = EndpointAnalyzer()
        results = [
            EndpointProbeResult(
                probe_type=ProbeType.INJECTION,
                success=False,
                response_time_ms=10.0,
                injection_detected=True,
            )
        ]
        risk = analyzer._calculate_risk(results)
        assert risk >= 25.0

    def test_calculate_risk_leakage(self):
        analyzer = EndpointAnalyzer()
        results = [
            EndpointProbeResult(
                probe_type=ProbeType.LEAKAGE,
                success=False,
                response_time_ms=10.0,
                data_leakage_detected=True,
            )
        ]
        risk = analyzer._calculate_risk(results)
        assert risk >= 30.0


class TestProbeEngine:
    """Test individual probes."""

    @pytest.fixture
    def probe_engine(self):
        return ProbeEngine()

    def test_sensitive_patterns(self, probe_engine):
        text = 'api_key = "sk-abc123def456ghi789jkl012mno345"'
        matches = []
        for pattern in probe_engine.sensitive_patterns:
            matches.extend(pattern.findall(text))
        assert len(matches) > 0

    def test_injection_payloads_exist(self, probe_engine):
        assert len(probe_engine.injection_payloads) >= 5

    def test_boundary_payloads_exist(self, probe_engine):
        assert len(probe_engine.boundary_payloads) >= 3


class TestProtocolHandlers:
    """Test protocol handlers."""

    def test_a2a_handler_init(self):
        handler = A2AProtocolHandler("http://test.com")
        assert handler.endpoint_url == "http://test.com"

    def test_mcp_handler_init(self):
        handler = MCPProtocolHandler("http://test.com")
        assert handler.endpoint_url == "http://test.com"


class TestProbeTypes:
    """Test all probe types are defined."""

    def test_all_probe_types(self):
        expected = [
            "identity", "capability", "boundary",
            "injection", "leakage", "compliance"
        ]
        actual = [p.value for p in ProbeType]

        for e in expected:
            assert e in actual


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
