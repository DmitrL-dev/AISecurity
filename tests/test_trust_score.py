#!/usr/bin/env python3
"""Unit tests for TrustScoreEngine."""

import pytest
import time
from unittest.mock import patch

from src.brain.security.trust_score import (
    TrustScoreEngine,
    TrustLevel,
    TrustScoreResult,
    AgentAction,
    Request,
    quick_trust_check,
)


class TestTrustScoreEngine:
    """Tests for TrustScoreEngine."""
    
    def test_base_score_by_zone(self):
        """Test base scores match trust zones."""
        engine = TrustScoreEngine()
        
        high = engine.calculate("agent", TrustLevel.HIGH)
        medium = engine.calculate("agent", TrustLevel.MEDIUM)
        low = engine.calculate("agent", TrustLevel.LOW)
        
        assert high.base_score == 0.9
        assert medium.base_score == 0.6
        assert low.base_score == 0.3
    
    def test_time_decay(self):
        """Test trust decays over time."""
        engine = TrustScoreEngine(decay_half_life=3600)
        
        engine.update_verification("agent-001")
        
        # Immediately after verification
        result1 = engine.calculate("agent-001", TrustLevel.HIGH)
        
        # Simulate 1 hour passing
        with patch.object(time, 'time', return_value=time.time() + 3600):
            result2 = engine.calculate("agent-001", TrustLevel.HIGH)
        
        # Decay should be ~0.5 after one half-life
        assert result2.time_decay < result1.time_decay
        assert result2.final_score < result1.final_score
    
    def test_no_verification_history(self):
        """Test behavior with no verification history."""
        engine = TrustScoreEngine()
        
        result = engine.calculate("new-agent", TrustLevel.HIGH)
        
        assert result.time_decay == 0.5  # Default for no history
    
    def test_behavior_score_no_history(self):
        """Test behavior score with no action history."""
        engine = TrustScoreEngine()
        
        result = engine.calculate("agent", TrustLevel.HIGH)
        
        assert result.behavior_score == 0.7  # Neutral default
    
    def test_behavior_score_with_anomalies(self):
        """Test behavior score decreases with anomalies."""
        engine = TrustScoreEngine()
        
        # Record normal actions
        for i in range(5):
            engine.record_action(AgentAction(
                agent_id="agent-001",
                operation="api_call",
                timestamp=time.time(),
                is_anomaly=False
            ))
        
        # Record anomalies
        for i in range(5):
            engine.record_action(AgentAction(
                agent_id="agent-001",
                operation="shell_command",
                timestamp=time.time(),
                is_anomaly=True
            ))
        
        result = engine.calculate("agent-001", TrustLevel.HIGH)
        
        # 50% anomaly rate should reduce behavior score
        assert result.behavior_score < 0.7
    
    def test_request_risk_assessment(self):
        """Test request risk scoring."""
        engine = TrustScoreEngine()
        
        low_risk = Request(operations=["file_read"])
        high_risk = Request(operations=["shell_command"])
        
        result_low = engine.calculate("agent", TrustLevel.HIGH, low_risk)
        result_high = engine.calculate("agent", TrustLevel.HIGH, high_risk)
        
        assert result_low.request_risk < result_high.request_risk
        assert result_low.final_score > result_high.final_score
    
    def test_combined_score_formula(self):
        """Test combined score calculation."""
        engine = TrustScoreEngine()
        engine.update_verification("agent-001")
        
        request = Request(operations=["api_call"])
        result = engine.calculate("agent-001", TrustLevel.HIGH, request)
        
        # Verify formula: final = base × decay × behavior × (1 - risk)
        expected = (
            result.base_score * 
            result.time_decay * 
            result.behavior_score * 
            (1 - result.request_risk)
        )
        
        assert abs(result.final_score - expected) < 0.01
    
    def test_minimum_score_floor(self):
        """Test that score doesn't go below minimum."""
        engine = TrustScoreEngine(min_score=0.1)
        
        # Create scenario that would result in very low score
        request = Request(operations=["shell_command"])  # High risk
        result = engine.calculate("untrusted", TrustLevel.UNTRUSTED, request)
        
        assert result.final_score >= 0.1
    
    def test_threshold_passing(self):
        """Test threshold evaluation."""
        engine = TrustScoreEngine(default_threshold=0.5)
        engine.update_verification("agent-001")
        
        # HIGH trust should pass
        high_result = engine.calculate("agent-001", TrustLevel.HIGH)
        assert high_result.passed_threshold is True
        
        # LOW trust may not pass
        low_result = engine.calculate("new-agent", TrustLevel.LOW)
        # Score ~0.3 * 0.5 * 0.7 = 0.105, below 0.5 threshold
        assert low_result.passed_threshold is False
    
    def test_custom_threshold(self):
        """Test custom threshold override."""
        engine = TrustScoreEngine()
        
        result = engine.calculate(
            "agent", 
            TrustLevel.MEDIUM,
            threshold=0.1  # Very low threshold
        )
        
        assert result.passed_threshold is True
    
    def test_explanation_generation(self):
        """Test explanation field."""
        engine = TrustScoreEngine()
        
        request = Request(operations=["shell_command"])
        result = engine.calculate("agent", TrustLevel.LOW, request)
        
        assert "decision" in result.explanation
        assert "risk" in result.explanation  # High risk operation
    
    def test_result_to_dict(self):
        """Test TrustScoreResult serialization."""
        engine = TrustScoreEngine()
        
        result = engine.calculate("agent", TrustLevel.HIGH)
        data = result.to_dict()
        
        assert isinstance(data, dict)
        assert "final_score" in data
        assert "passed_threshold" in data
    
    def test_quick_trust_check(self):
        """Test convenience function."""
        result = quick_trust_check(
            agent_id="agent-001",
            trust_level="high",
            operation="api_call"
        )
        
        assert isinstance(result, bool)
    
    def test_action_history_cleanup(self):
        """Test that old actions are cleaned up."""
        engine = TrustScoreEngine()
        
        # Record old action (25 hours ago)
        old_action = AgentAction(
            agent_id="agent-001",
            operation="api_call",
            timestamp=time.time() - 90000,  # 25 hours ago
            is_anomaly=True
        )
        engine.record_action(old_action)
        
        # Record recent action
        recent_action = AgentAction(
            agent_id="agent-001",
            operation="api_call",
            timestamp=time.time(),
            is_anomaly=False
        )
        engine.record_action(recent_action)
        
        # Only recent action should affect score
        history = engine._action_history.get("agent-001", [])
        assert len(history) == 1
        assert history[0].is_anomaly is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
