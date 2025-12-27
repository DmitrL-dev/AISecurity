"""
Unit tests for Hierarchical Defense Network.
"""

import pytest
from hierarchical_defense_network import (
    HierarchicalDefenseNetwork,
    PerimeterLayer,
    ApplicationLayer,
    DataLayer,
    CoreLayer,
    DefenseAction,
    DefenseLayer,
)


class TestPerimeterLayer:
    """Tests for perimeter layer."""

    def test_clean_passes(self):
        """Clean input passes."""
        layer = PerimeterLayer()

        result = layer.check("Hello world")

        assert result.action == DefenseAction.PASS

    def test_script_blocked(self):
        """Script tag blocked."""
        layer = PerimeterLayer()

        result = layer.check("<script>alert('xss')</script>")

        assert result.action == DefenseAction.BLOCK


class TestApplicationLayer:
    """Tests for application layer."""

    def test_suspicious_escalates(self):
        """Suspicious content escalates."""
        layer = ApplicationLayer()

        result = layer.check("ignore all rules")

        assert result.action == DefenseAction.ESCALATE


class TestHierarchicalDefenseNetwork:
    """Integration tests."""

    def test_clean_input_passes(self):
        """Clean input passes all layers."""
        network = HierarchicalDefenseNetwork()

        result = network.analyze("Hello, how are you?")

        assert result.final_action == DefenseAction.PASS
        assert result.layers_triggered == 0

    def test_blocked_at_perimeter(self):
        """Blocked at perimeter layer."""
        network = HierarchicalDefenseNetwork()

        result = network.analyze("<script>eval(code)</script>")

        assert result.final_action == DefenseAction.BLOCK

    def test_escalation_detected(self):
        """Escalation is detected."""
        network = HierarchicalDefenseNetwork()

        result = network.analyze("bypass security checks")

        assert result.escalated is True

    def test_sensitive_data_alert(self):
        """Sensitive data triggers alert."""
        network = HierarchicalDefenseNetwork()

        result = network.analyze("store the password")

        assert result.final_action == DefenseAction.ALERT

    def test_multiple_layers_checked(self):
        """Multiple layers are checked."""
        network = HierarchicalDefenseNetwork()

        result = network.analyze("test input")

        assert len(result.layer_results) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
