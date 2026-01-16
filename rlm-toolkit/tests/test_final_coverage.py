"""Final coverage tests for remaining low-coverage modules."""

import pytest
from unittest.mock import MagicMock, patch
import sys

from rlm_toolkit.core.engine import RLM, RLMConfig, RLMResult
from rlm_toolkit.testing.mocks import MockProvider
from rlm_toolkit.observability.exporters import ConsoleExporter


class TestRLMConfigExtended:
    """Extended config tests."""
    
    def test_security_config_in_rlmconfig(self):
        """Test security config access."""
        config = RLMConfig(sandbox=True)
        
        assert config.sandbox is True
    
    def test_max_iterations_default(self):
        """Test max iterations default."""
        config = RLMConfig()
        
        assert config.max_iterations == 50


class TestRLMEngineEdgeCases:
    """Edge case tests for RLM engine."""
    
    def test_empty_context(self):
        """Test with empty context."""
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert result.status == "success"
    
    def test_long_answer(self):
        """Test with long answer."""
        long_response = "A" * 10000
        provider = MockProvider(responses=[f"FINAL({long_response})"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert len(result.answer) > 1000
    
    def test_multiline_code_execution(self):
        """Test multiline code block execution."""
        provider = MockProvider(responses=[
            "```python\nx = 1\ny = 2\nresult = x + y\n```",
            "FINAL(3)"
        ])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="sum")
        
        assert result.iterations >= 1
    
    def test_final_with_newlines(self):
        """Test FINAL with newlines in answer."""
        provider = MockProvider(responses=['FINAL("line1\\nline2")'])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert "line" in result.answer
    
    def test_cost_tracking(self):
        """Test cost is tracked."""
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert result.total_cost >= 0.0
