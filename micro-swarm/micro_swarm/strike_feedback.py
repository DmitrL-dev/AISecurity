"""StrikeFeedbackLoop — adaptive anti-detection for Strike.

Learns optimal stealth parameters from probe responses.
Each probe's success/failure (200/403/429) trains the Swarm
to minimize detection rate against a specific target's defenses.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.trainer import ContinuousTrainer, DriftStatus


@dataclass
class ProbeResult:
    """Result of a Strike probe against target."""

    status_code: int            # 200=pass, 403=blocked, 429=rate-limited
    response_time_ms: float     # Actual response latency
    was_detected: bool          # True if blocked/challenged
    probe_features: dict        # Features used in this probe
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class StealthProfile:
    """Learned stealth parameters for a target."""

    optimal_jitter_ms: float
    optimal_interval_ms: float
    recommended_tls_profile: str
    detection_rate: float       # 0.0 = fully stealth
    probes_count: int
    target_id: str
    features: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Export as JSON string."""
        return json.dumps({
            "target_id": self.target_id,
            "optimal_jitter_ms": self.optimal_jitter_ms,
            "optimal_interval_ms": self.optimal_interval_ms,
            "recommended_tls_profile": self.recommended_tls_profile,
            "detection_rate": self.detection_rate,
            "probes_count": self.probes_count,
            "features": self.features,
        }, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "StealthProfile":
        """Load from JSON string."""
        d = json.loads(data)
        return cls(**d)


class StrikeFeedbackLoop:
    """Adaptive anti-detection: learns from probe responses.

    Workflow:
    1. Strike sends probe → target responds (200/403/429)
    2. FeedbackLoop ingests response → ContinuousTrainer updates MicroModels
    3. After N probes, recommend() returns optimal stealth params
    4. Drift detection: if target updates WAF → loss rises → auto-retrain
    """

    def __init__(
        self,
        swarm: SwarmOrchestrator,
        target_id: str = "default",
        train_every: int = 5,
        lr: float = 0.01,
    ) -> None:
        self._swarm = swarm
        self._target_id = target_id
        self._probes: list[ProbeResult] = []
        self._trainers: dict[str, ContinuousTrainer] = {}

        # Create ContinuousTrainer for each domain model
        for name in swarm.domain_names:
            model = swarm._models[name]
            self._trainers[name] = ContinuousTrainer(
                model=model,
                train_every=train_every,
                lr=lr,
                model_name=f"strike_{name}",
            )

    @property
    def probe_count(self) -> int:
        return len(self._probes)

    @property
    def detection_rate(self) -> float:
        """Current detection rate (0.0 = fully stealth)."""
        if not self._probes:
            return 0.0
        detected = sum(1 for p in self._probes if p.was_detected)
        return detected / len(self._probes)

    def ingest(self, probe: ProbeResult) -> float | None:
        """Feed probe result. Target: was_detected → 1.0 (bad), not → 0.0 (good).

        Returns average loss if training happened, None otherwise.
        """
        self._probes.append(probe)

        # Target: minimize detection → 0.0 = not detected (good), 1.0 = detected (bad)
        target = 1.0 if probe.was_detected else 0.0

        # Extract features for each domain and train
        losses: list[float] = []
        for name, trainer in self._trainers.items():
            domain = self._swarm._domains[name]
            features = domain.extract(probe.probe_features)
            loss = trainer.ingest(features, target)
            if loss is not None:
                losses.append(loss)

        return sum(losses) / len(losses) if losses else None

    def recommend(self) -> dict[str, float]:
        """Score current feature space → return optimal stealth params.

        Uses the Swarm to predict which parameter values minimize detection.
        Returns a dict of feature_name → recommended_value.
        """
        if not self._probes:
            return {}

        # Use the most recent successful probe's features as baseline
        successful = [p for p in self._probes if not p.was_detected]
        if successful:
            baseline = successful[-1].probe_features
        else:
            baseline = self._probes[-1].probe_features

        # Score the baseline through swarm
        result = self._swarm.predict(baseline)

        # Build recommendations: features from non-detected probes
        recommendations: dict[str, float] = {}
        for name in self._swarm.domain_names:
            domain = self._swarm._domains[name]
            ds = result.domain_scores.get(name)
            if ds:
                recommendations[f"{name}_score"] = ds.score

            # Average successful feature values as recommendations
            if successful:
                for feat in domain.feature_names:
                    vals = [
                        p.probe_features.get(feat, 0.0) for p in successful[-10:]
                    ]
                    if vals:
                        recommendations[feat] = sum(vals) / len(vals)

        recommendations["detection_rate"] = self.detection_rate
        recommendations["probes_count"] = float(self.probe_count)

        return recommendations

    def export_profile(self) -> StealthProfile:
        """Export learned stealth profile for reuse."""
        recs = self.recommend()
        return StealthProfile(
            optimal_jitter_ms=recs.get("jitter_ms", 0.0),
            optimal_interval_ms=recs.get("request_interval", 0.0),
            recommended_tls_profile=f"learned_{self._target_id}",
            detection_rate=self.detection_rate,
            probes_count=self.probe_count,
            target_id=self._target_id,
            features=recs,
        )

    def detect_waf_change(self) -> bool:
        """Check if target's defenses have changed (drift detection).

        If any domain model shows drift, the target may have updated its WAF.
        """
        for name, trainer in self._trainers.items():
            drift = trainer.detect_drift()
            if drift.is_drifting:
                return True
        return False

    def get_drift_status(self) -> dict[str, DriftStatus]:
        """Get drift status for all domain trainers."""
        return {
            name: trainer.detect_drift()
            for name, trainer in self._trainers.items()
        }
