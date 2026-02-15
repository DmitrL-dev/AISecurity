"""Strike preset — adaptive stealth domains for anti-detection.

Enterprise-only. Learns optimal stealth parameters (timing, fingerprint,
behavioral mimicry) from probe responses against target defenses.
"""

from __future__ import annotations

from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.meta_learner import CrossDomainMetaLearner


STEALTH_TIMING_DOMAIN = DomainConfig(
    name="stealth_timing",
    description="Request timing stealth: jitter, intervals, backoff patterns.",
    features=(
        FeatureSpec("jitter_ms", NormMethod.MIN_MAX, 0, 5000, 500, 1000),
        FeatureSpec("request_interval", NormMethod.MIN_MAX,
                    0, 60000, 5000, 10000),
        FeatureSpec("burst_size", NormMethod.MIN_MAX, 1, 50, 3, 5),
        FeatureSpec("cooldown_period", NormMethod.MIN_MAX,
                    0, 300000, 30000, 60000),
        FeatureSpec("time_of_day", NormMethod.MIN_MAX, 0, 24, 12, 6),
        FeatureSpec("ramp_up_speed", NormMethod.MIN_MAX, 0, 1, 0.3, 0.2),
        FeatureSpec("backoff_factor", NormMethod.MIN_MAX, 1, 10, 2, 2),
        FeatureSpec("session_duration", NormMethod.MIN_MAX,
                    0, 3600000, 300000, 600000),
    ),
)

FINGERPRINT_DOMAIN = DomainConfig(
    name="fingerprint",
    description="TLS/HTTP fingerprint mimicry for WAF evasion.",
    features=(
        FeatureSpec("tls_version", NormMethod.MIN_MAX, 0, 5, 3, 1),
        FeatureSpec("cipher_suite_idx", NormMethod.MIN_MAX, 0, 50, 15, 10),
        FeatureSpec("ja3_hash_entropy", NormMethod.MIN_MAX, 0, 8, 4, 2),
        FeatureSpec("header_order_score", NormMethod.MIN_MAX, 0, 1, 0.7, 0.2),
        FeatureSpec("user_agent_freshness",
                    NormMethod.MIN_MAX, 0, 1, 0.8, 0.2),
        FeatureSpec("accept_language_match",
                    NormMethod.MIN_MAX, 0, 1, 0.9, 0.1),
        FeatureSpec("compression_support", NormMethod.NONE, 0, 1, 0.9, 0.2),
        FeatureSpec("http2_settings_score",
                    NormMethod.MIN_MAX, 0, 1, 0.7, 0.2),
    ),
)

BEHAVIORAL_MIMICRY_DOMAIN = DomainConfig(
    name="behavioral_mimicry",
    description="Human behavioral mimicry to bypass bot detection.",
    features=(
        FeatureSpec("click_pattern_score", NormMethod.MIN_MAX, 0, 1, 0.6, 0.2),
        FeatureSpec("scroll_depth", NormMethod.MIN_MAX, 0, 1, 0.4, 0.3),
        FeatureSpec("page_dwell_time", NormMethod.MIN_MAX,
                    0, 300000, 30000, 60000),
        FeatureSpec("navigation_sequence", NormMethod.MIN_MAX, 0, 1, 0.5, 0.3),
        FeatureSpec("mouse_movement_entropy", NormMethod.MIN_MAX, 0, 8, 4, 2),
        FeatureSpec("form_fill_speed", NormMethod.MIN_MAX, 0, 1, 0.5, 0.2),
        FeatureSpec("referrer_chain_length", NormMethod.MIN_MAX, 0, 10, 2, 3),
        FeatureSpec("cookie_acceptance_ratio",
                    NormMethod.MIN_MAX, 0, 1, 0.8, 0.2),
    ),
)


def build_strike() -> SwarmOrchestrator:
    """Build Strike Stealth SwarmOrchestrator for adaptive anti-detection."""
    domains = {
        "stealth_timing": STEALTH_TIMING_DOMAIN,
        "fingerprint": FINGERPRINT_DOMAIN,
        "behavioral_mimicry": BEHAVIORAL_MIMICRY_DOMAIN,
    }
    models = {
        name: MicroModel(MicroModelConfig(n_features=8, seed=300 + i))
        for i, name in enumerate(domains)
    }
    return SwarmOrchestrator(
        models=models, domains=domains,
        meta_learner=CrossDomainMetaLearner(n_domains=len(domains)),
    )
