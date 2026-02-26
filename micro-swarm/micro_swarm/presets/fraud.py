"""Fraud preset — transaction fraud detection domains.

Detects fraudulent transactions via velocity, amount, and pattern analysis.
"""

from __future__ import annotations

from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.meta_learner import CrossDomainMetaLearner


VELOCITY_DOMAIN = DomainConfig(
    name="velocity",
    description="Transaction velocity and frequency analysis.",
    features=(
        FeatureSpec("tx_per_hour", NormMethod.MIN_MAX, 0, 100, 5, 10),
        FeatureSpec("daily_tx_count", NormMethod.MIN_MAX, 0, 500, 10, 30),
        FeatureSpec("amount_std_24h", NormMethod.MIN_MAX, 0, 10000, 100, 500),
        FeatureSpec("unique_merchants_1h", NormMethod.MIN_MAX, 0, 50, 2, 5),
        FeatureSpec("card_usage_count", NormMethod.MIN_MAX, 0, 100, 5, 15),
        FeatureSpec("avg_time_between_tx",
                    NormMethod.MIN_MAX, 0, 86400, 3600, 7200),
        FeatureSpec("max_amount_ratio", NormMethod.MIN_MAX, 0, 100, 2, 5),
        FeatureSpec("velocity_change_ratio", NormMethod.MIN_MAX, 0, 10, 1, 2),
    ),
)

AMOUNT_DOMAIN = DomainConfig(
    name="amount",
    description="Transaction amount anomaly detection.",
    features=(
        FeatureSpec("amount_deviation", NormMethod.Z_SCORE,
                    0, 10000, 200, 500),
        FeatureSpec("is_round_number", NormMethod.NONE, 0, 1, 0.3, 0.4),
        FeatureSpec("split_pattern_score",
                    NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("amount_vs_avg", NormMethod.MIN_MAX, 0, 50, 1, 3),
        FeatureSpec("max_single_tx", NormMethod.MIN_MAX, 0, 100000, 500, 2000),
        FeatureSpec("refund_ratio", NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("micro_tx_count", NormMethod.MIN_MAX, 0, 50, 0, 5),
        FeatureSpec("amount_acceleration", NormMethod.MIN_MAX, -10, 10, 0, 2),
    ),
)

PATTERN_DOMAIN = DomainConfig(
    name="pattern",
    description="Behavioral pattern analysis for transaction fraud.",
    features=(
        FeatureSpec("hour_of_day", NormMethod.MIN_MAX, 0, 23, 12, 6),
        FeatureSpec("is_weekend", NormMethod.NONE, 0, 1, 0.3, 0.4),
        FeatureSpec("geo_distance_km", NormMethod.MIN_MAX, 0, 20000, 50, 500),
        FeatureSpec("device_switch_count", NormMethod.MIN_MAX, 0, 20, 1, 3),
        FeatureSpec("ip_change_count", NormMethod.MIN_MAX, 0, 50, 1, 5),
        FeatureSpec("shipping_billing_match", NormMethod.NONE, 0, 1, 0.8, 0.3),
        FeatureSpec("email_domain_age_days",
                    NormMethod.MIN_MAX, 0, 10000, 1000, 2000),
        FeatureSpec("account_age_days", NormMethod.MIN_MAX, 0, 5000, 365, 500),
    ),
)


def build_fraud() -> SwarmOrchestrator:
    """Build Fraud Detection SwarmOrchestrator."""
    domains = {
        "velocity": VELOCITY_DOMAIN,
        "amount": AMOUNT_DOMAIN,
        "pattern": PATTERN_DOMAIN,
    }
    models = {
        name: MicroModel(MicroModelConfig(n_features=8, seed=200 + i))
        for i, name in enumerate(domains)
    }
    return SwarmOrchestrator(
        models=models, domains=domains,
        meta_learner=CrossDomainMetaLearner(n_domains=len(domains)),
    )
