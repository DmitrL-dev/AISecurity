"""Tests for StrikeFeedbackLoop."""

from micro_swarm.strike_feedback import StrikeFeedbackLoop, ProbeResult, StealthProfile
from micro_swarm.presets.strike import build_strike


class TestStrikeFeedbackLoop:
    def _make_loop(self) -> StrikeFeedbackLoop:
        swarm = build_strike()
        return StrikeFeedbackLoop(swarm, target_id="test_target")

    def _make_probe(self, detected: bool = False) -> ProbeResult:
        return ProbeResult(
            status_code=403 if detected else 200,
            response_time_ms=150.0,
            was_detected=detected,
            probe_features={
                "jitter_ms": 500,
                "request_interval": 5000,
                "burst_size": 3,
                "cooldown_period": 30000,
                "time_of_day": 14,
                "ramp_up_speed": 0.3,
                "backoff_factor": 2,
                "session_duration": 300000,
                "tls_version": 3,
                "cipher_suite_idx": 15,
                "ja3_hash_entropy": 4.0,
                "header_order_score": 0.7,
                "user_agent_freshness": 0.8,
                "accept_language_match": 0.9,
                "compression_support": 1,
                "http2_settings_score": 0.7,
                "click_pattern_score": 0.6,
                "scroll_depth": 0.4,
                "page_dwell_time": 30000,
                "navigation_sequence": 0.5,
                "mouse_movement_entropy": 4.0,
                "form_fill_speed": 0.5,
                "referrer_chain_length": 2,
                "cookie_acceptance_ratio": 0.8,
            },
        )

    def test_ingest(self):
        loop = self._make_loop()
        probe = self._make_probe(detected=False)
        result = loop.ingest(probe)
        assert loop.probe_count == 1
        # result may be None (not enough samples for auto-train)

    def test_detection_rate(self):
        loop = self._make_loop()
        loop.ingest(self._make_probe(detected=False))
        loop.ingest(self._make_probe(detected=True))
        assert loop.detection_rate == 0.5

    def test_recommend(self):
        loop = self._make_loop()
        for _ in range(5):
            loop.ingest(self._make_probe(detected=False))
        recs = loop.recommend()
        assert isinstance(recs, dict)
        assert "detection_rate" in recs
        assert recs["detection_rate"] == 0.0

    def test_export_profile(self):
        loop = self._make_loop()
        for _ in range(3):
            loop.ingest(self._make_probe(detected=False))
        profile = loop.export_profile()
        assert isinstance(profile, StealthProfile)
        assert profile.target_id == "test_target"
        assert profile.probes_count == 3

    def test_profile_json_roundtrip(self):
        loop = self._make_loop()
        loop.ingest(self._make_probe(detected=False))
        profile = loop.export_profile()
        json_str = profile.to_json()
        assert "test_target" in json_str
        loaded = StealthProfile.from_json(json_str)
        assert loaded.target_id == "test_target"

    def test_detect_waf_change(self):
        loop = self._make_loop()
        # With no data, no drift expected
        assert not loop.detect_waf_change()

    def test_get_drift_status(self):
        loop = self._make_loop()
        statuses = loop.get_drift_status()
        assert len(statuses) == 3  # 3 domains
