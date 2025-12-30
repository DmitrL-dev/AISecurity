"""
Tests for SENTINEL Framework core components.
"""

import pytest
from sentinel.core.finding import Finding, Severity, Confidence, FindingCollection
from sentinel.core.context import AnalysisContext, Message
from sentinel.core.engine import BaseEngine, EngineResult, register_engine
from sentinel.core.pipeline import Pipeline, PipelineConfig


class TestFinding:
    """Tests for Finding class."""
    
    def test_finding_creation(self):
        """Test basic finding creation."""
        finding = Finding(
            engine="test_engine",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            title="Test Finding",
            description="Test description",
        )
        assert finding.engine == "test_engine"
        assert finding.severity == Severity.HIGH
        assert finding.confidence == Confidence.HIGH
        assert finding.id is not None
    
    def test_finding_risk_score(self):
        """Test risk score calculation."""
        critical_high = Finding(
            engine="test",
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            title="Critical",
            description="",
        )
        assert critical_high.risk_score == 1.0 * 0.9  # 0.9
        
        low_low = Finding(
            engine="test",
            severity=Severity.LOW,
            confidence=Confidence.LOW,
            title="Low",
            description="",
        )
        assert low_low.risk_score == 0.25 * 0.3  # 0.075
    
    def test_finding_to_sarif(self):
        """Test SARIF conversion."""
        finding = Finding(
            engine="test",
            severity=Severity.HIGH,
            confidence=Confidence.MEDIUM,
            title="Test",
            description="Desc",
        )
        sarif = finding.to_sarif()
        assert sarif["level"] == "error"
        assert "sentinel/test" in sarif["ruleId"]
    
    def test_severity_comparison(self):
        """Test severity comparison."""
        assert Severity.CRITICAL > Severity.HIGH
        assert Severity.HIGH > Severity.MEDIUM
        assert Severity.INFO < Severity.LOW


class TestFindingCollection:
    """Tests for FindingCollection."""
    
    def test_collection_basic(self):
        """Test basic collection operations."""
        collection = FindingCollection()
        assert collection.count == 0
        
        collection.add(Finding(
            engine="test",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            title="Test",
            description="",
        ))
        assert collection.count == 1
    
    def test_collection_max_severity(self):
        """Test max severity."""
        collection = FindingCollection()
        collection.add(Finding(
            engine="test", severity=Severity.LOW,
            confidence=Confidence.HIGH, title="", description=""
        ))
        collection.add(Finding(
            engine="test", severity=Severity.CRITICAL,
            confidence=Confidence.HIGH, title="", description=""
        ))
        assert collection.max_severity == Severity.CRITICAL


class TestAnalysisContext:
    """Tests for AnalysisContext."""
    
    def test_context_creation(self):
        """Test basic context creation."""
        ctx = AnalysisContext(prompt="Hello")
        assert ctx.prompt == "Hello"
        assert ctx.request_id is not None
        assert len(ctx.request_id) == 8
    
    def test_context_history(self):
        """Test multi-turn history."""
        ctx = AnalysisContext(prompt="Current")
        ctx.add_to_history("user", "Previous message")
        ctx.add_to_history("assistant", "Previous response")
        
        assert ctx.is_multi_turn
        assert ctx.history_length == 2
    
    def test_context_with_response(self):
        """Test creating context with response."""
        ctx = AnalysisContext(prompt="Question")
        ctx2 = ctx.with_response("Answer")
        
        assert ctx.response is None
        assert ctx2.response == "Answer"
        assert ctx2.prompt == "Question"


class TestBaseEngine:
    """Tests for BaseEngine."""
    
    def test_engine_creation(self):
        """Test engine subclassing."""
        class TestEngine(BaseEngine):
            name = "test_engine"
            
            def analyze(self, context):
                return self._create_result([])
        
        engine = TestEngine()
        assert engine.name == "test_engine"
    
    def test_engine_analyze(self):
        """Test engine analysis."""
        class DetectBadEngine(BaseEngine):
            name = "detect_bad"
            
            def analyze(self, context):
                findings = []
                if "bad" in context.prompt.lower():
                    findings.append(self._create_finding(
                        Severity.HIGH,
                        Confidence.HIGH,
                        "Bad word",
                        "Found bad word",
                    ))
                return self._create_result(findings)
        
        engine = DetectBadEngine()
        
        safe_ctx = AnalysisContext(prompt="Hello")
        safe_result = engine.analyze(safe_ctx)
        assert safe_result.is_safe
        assert safe_result.risk_score == 0.0
        
        bad_ctx = AnalysisContext(prompt="This is bad")
        bad_result = engine.analyze(bad_ctx)
        assert not bad_result.is_safe
        assert bad_result.risk_score > 0.5


class TestEngineResult:
    """Tests for EngineResult."""
    
    def test_safe_result(self):
        """Test safe result factory."""
        result = EngineResult.safe("test", 5.0)
        assert result.is_safe
        assert result.risk_score == 0.0
        assert result.execution_time_ms == 5.0
    
    def test_error_result(self):
        """Test error result factory."""
        result = EngineResult.error_result("test", "Something failed")
        assert result.error == "Something failed"
        assert not result.success


class TestPipeline:
    """Tests for Pipeline."""
    
    def test_pipeline_empty(self):
        """Test empty pipeline."""
        pipeline = Pipeline(engines=[])
        ctx = AnalysisContext(prompt="Test")
        result = pipeline.analyze_sync(ctx)
        
        assert result.is_safe
        assert result.engines_executed == 0
    
    def test_pipeline_with_engine(self):
        """Test pipeline with engine."""
        class SimpleEngine(BaseEngine):
            name = "simple"
            tier = 1
            
            def analyze(self, context):
                return self._create_result([])
        
        pipeline = Pipeline(engines=[SimpleEngine()])
        ctx = AnalysisContext(prompt="Test")
        result = pipeline.analyze_sync(ctx)
        
        assert result.is_safe
        assert result.engines_executed == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
