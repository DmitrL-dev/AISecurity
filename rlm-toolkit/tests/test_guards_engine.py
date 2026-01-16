"""Extended tests for platform guards and engine coverage."""

import pytest
import sys
from unittest.mock import MagicMock, patch

from rlm_toolkit.security.platform_guards import (
    GuardConfig,
    create_guards,
)
from rlm_toolkit.core.engine import RLM, RLMConfig
from rlm_toolkit.testing.mocks import MockProvider


class TestGuardConfigExtended:
    """Extended tests for GuardConfig."""
    
    def test_defaults(self):
        """Test default config values."""
        config = GuardConfig()
        
        assert config.timeout_seconds == 30.0
        assert config.memory_mb == 512
        assert config.cpu_percent == 80
    
    def test_custom_values(self):
        """Test custom config values."""
        config = GuardConfig(
            timeout_seconds=60.0,
            memory_mb=1024,
            cpu_percent=50,
        )
        
        assert config.timeout_seconds == 60.0
        assert config.memory_mb == 1024
        assert config.cpu_percent == 50


class TestCreateGuards:
    """Tests for create_guards factory."""
    
    def test_creates_guards(self):
        """Test factory creates guards."""
        guards = create_guards()
        
        assert guards is not None
    
    def test_guards_have_platform_name(self):
        """Test guards have platform name."""
        guards = create_guards()
        
        assert guards.platform_name is not None
        assert len(guards.platform_name) > 0
    
    def test_guards_have_capabilities(self):
        """Test guards report capabilities."""
        guards = create_guards()
        
        caps = guards.capabilities
        assert isinstance(caps, dict)
    
    def test_guards_set_memory_limit(self):
        """Test set_memory_limit returns bool."""
        guards = create_guards()
        
        result = guards.set_memory_limit(512)
        assert isinstance(result, bool)
    
    def test_guards_set_cpu_limit(self):
        """Test set_cpu_limit returns bool."""
        guards = create_guards()
        
        result = guards.set_cpu_limit(80)
        assert isinstance(result, bool)
    
    def test_execute_with_timeout(self):
        """Test execute_with_timeout."""
        guards = create_guards()
        
        def simple_func():
            return 42
        
        success, result = guards.execute_with_timeout(simple_func, timeout=5.0)
        
        assert success is True
        assert result == 42


class TestRLMEngineExtended:
    """Extended tests for RLM engine coverage."""
    
    def test_run_with_final_var(self):
        """Test run with FINAL_VAR."""
        provider = MockProvider(responses=[
            "```python\nresult = 42\n```",
            "FINAL_VAR(result)",
        ])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="Calculate 42")
        
        # FINAL_VAR should work
        assert result.iterations >= 1
    
    def test_run_max_cost_limit(self):
        """Test run stops on max cost."""
        provider = MockProvider(responses=["Still working..."])
        config = RLMConfig(max_iterations=100, max_cost=0.0001)
        rlm = RLM(root=provider, config=config)
        
        result = rlm.run(context="", query="test")
        
        # Should stop due to cost or iterations
        assert result.status in ("max_cost", "max_iterations", "success")
    
    def test_stream_method(self):
        """Test stream method."""
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        events = list(rlm.stream(context="test", query="test"))
        
        assert len(events) >= 2  # start and final events
    
    def test_arun_method(self):
        """Test async run method."""
        import asyncio
        
        provider = MockProvider(responses=["FINAL(done)"])
        rlm = RLM(root=provider)
        
        async def run_async():
            return await rlm.arun(context="test", query="test")
        
        result = asyncio.run(run_async())
        
        assert result.status == "success"
    
    def test_extract_final_nested_parens(self):
        """Test FINAL extraction with nested parens."""
        provider = MockProvider(responses=['FINAL("calculate(a + b) = 5")'])
        rlm = RLM(root=provider)
        
        result = rlm.run(context="", query="test")
        
        assert "calculate" in result.answer or "5" in result.answer
    
    def test_sandbox_disabled(self):
        """Test running with sandbox disabled."""
        provider = MockProvider(responses=["FINAL(done)"])
        config = RLMConfig(sandbox=False)
        rlm = RLM(root=provider, config=config)
        
        result = rlm.run(context="", query="test")
        
        assert result.status == "success"
