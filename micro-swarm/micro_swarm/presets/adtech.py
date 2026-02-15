"""AdTech preset — timing, geo, device domains.

Extracted from VirtualConv domain_config.py.
"""

from __future__ import annotations

from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.meta_learner import CrossDomainMetaLearner


TIMING_DOMAIN = DomainConfig(
    name="timing",
    description="Request timing analysis for bot/fraud detection.",
    features=(
        FeatureSpec("time_since_last_request",
                    NormMethod.MIN_MAX, 0, 300_000, 5000, 10000),
        FeatureSpec("session_duration_ms", NormMethod.MIN_MAX,
                    0, 1_800_000, 60000, 120000),
        FeatureSpec("request_rate_per_min",
                    NormMethod.MIN_MAX, 0, 1000, 10, 50),
        FeatureSpec("time_on_page_ms", NormMethod.MIN_MAX,
                    0, 600_000, 30000, 60000),
        FeatureSpec("scroll_velocity", NormMethod.MIN_MAX, 0, 10000, 100, 500),
        FeatureSpec("click_interval_std",
                    NormMethod.MIN_MAX, 0, 5000, 200, 500),
        FeatureSpec("idle_time_ratio", NormMethod.MIN_MAX, 0, 1, 0.3, 0.3),
        FeatureSpec("burst_count", NormMethod.MIN_MAX, 0, 50, 2, 5),
    ),
)

GEO_DOMAIN = DomainConfig(
    name="geo",
    description="Geographic and network-based signals.",
    features=(
        FeatureSpec("lat_normalized", NormMethod.MIN_MAX, -90, 90, 0, 45),
        FeatureSpec("lon_normalized", NormMethod.MIN_MAX, -180, 180, 0, 90),
        FeatureSpec("is_vpn", NormMethod.NONE, 0, 1, 0.1, 0.3),
        FeatureSpec("is_datacenter", NormMethod.NONE, 0, 1, 0.05, 0.2),
        FeatureSpec("timezone_offset_hours",
                    NormMethod.MIN_MAX, -12, 14, 0, 6),
        FeatureSpec("geo_velocity_kmh", NormMethod.MIN_MAX, 0, 1000, 0, 100),
        FeatureSpec("asn_reputation_score",
                    NormMethod.MIN_MAX, 0, 1, 0.5, 0.3),
        FeatureSpec("country_risk_score", NormMethod.MIN_MAX, 0, 1, 0.2, 0.3),
    ),
)

DEVICE_DOMAIN = DomainConfig(
    name="device",
    description="Device fingerprinting signals.",
    features=(
        FeatureSpec("screen_resolution_score",
                    NormMethod.MIN_MAX, 0, 1, 0.7, 0.2),
        FeatureSpec("has_touch", NormMethod.NONE, 0, 1, 0.5, 0.5),
        FeatureSpec("user_agent_entropy", NormMethod.MIN_MAX, 0, 10, 4, 2),
        FeatureSpec("plugin_count", NormMethod.MIN_MAX, 0, 50, 5, 10),
        FeatureSpec("canvas_hash_uniqueness",
                    NormMethod.MIN_MAX, 0, 1, 0.8, 0.2),
        FeatureSpec("webgl_hash_uniqueness",
                    NormMethod.MIN_MAX, 0, 1, 0.8, 0.2),
        FeatureSpec("font_count", NormMethod.MIN_MAX, 0, 200, 30, 50),
        FeatureSpec("timezone_mismatch", NormMethod.NONE, 0, 1, 0.05, 0.2),
    ),
)


def build_adtech() -> SwarmOrchestrator:
    """Build AdTech SwarmOrchestrator with 3 domains."""
    domains = {
        "timing": TIMING_DOMAIN,
        "geo": GEO_DOMAIN,
        "device": DEVICE_DOMAIN,
    }
    models = {
        name: MicroModel(MicroModelConfig(n_features=8, seed=42 + i))
        for i, name in enumerate(domains)
    }
    return SwarmOrchestrator(
        models=models, domains=domains,
        meta_learner=CrossDomainMetaLearner(n_domains=len(domains)),
    )
