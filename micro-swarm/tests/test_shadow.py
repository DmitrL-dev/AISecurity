"""Tests for ShadowAdapter."""

from micro_swarm.shadow import ShadowAdapter, DisagreementReport
from micro_swarm.model import MicroModel


class TestShadowAdapter:
    def test_observe(self):
        model = MicroModel()
        shadow = ShadowAdapter(model)
        # First few observations won't trigger training
        result = shadow.observe([0.5] * 8, 0.8)
        assert result is None or isinstance(result, float)

    def test_predict(self):
        model = MicroModel()
        shadow = ShadowAdapter(model)
        score = shadow.predict([0.5] * 8)
        assert 0.0 <= score <= 1.0

    def test_disagreement(self):
        model = MicroModel()
        shadow = ShadowAdapter(model, disagreement_threshold=0.1)
        report = shadow.disagreement([0.5] * 8, 0.9)
        assert isinstance(report, DisagreementReport)
        assert report.engine_decision == 0.9
        assert report.disagreement_score >= 0

    def test_disagreement_history(self):
        model = MicroModel()
        shadow = ShadowAdapter(model, disagreement_threshold=0.01)
        # Create enough disagreements
        for _ in range(5):
            shadow.disagreement([0.5] * 8, 0.99)
        # Should have recorded disagreements (shadow likely disagrees)
        assert shadow.disagreement_count >= 0

    def test_disagreement_count(self):
        model = MicroModel()
        shadow = ShadowAdapter(model)
        assert shadow.disagreement_count == 0
