"""Security preset — Prompt Injection Detection domains.

Detects prompt injection attacks against LLM applications
via token_pattern, semantic_shift, and behavioral analysis.
"""

from __future__ import annotations

from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.meta_learner import CrossDomainMetaLearner


TOKEN_PATTERN_DOMAIN = DomainConfig(
    name="token_pattern",
    description="Token-level pattern analysis for injection detection.",
    features=(
        FeatureSpec("entropy", NormMethod.MIN_MAX, 0, 8, 4, 2),
        FeatureSpec("special_char_ratio", NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("instruction_keyword_count",
                    NormMethod.MIN_MAX, 0, 50, 2, 5),
        FeatureSpec("delimiter_count", NormMethod.MIN_MAX, 0, 100, 5, 10),
        FeatureSpec("code_block_ratio", NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("unicode_anomaly_score",
                    NormMethod.MIN_MAX, 0, 1, 0.01, 0.05),
        FeatureSpec("length_ratio", NormMethod.MIN_MAX, 0, 100, 1, 5),
        FeatureSpec("repetition_score", NormMethod.MIN_MAX, 0, 1, 0.1, 0.2),
    ),
)

SEMANTIC_SHIFT_DOMAIN = DomainConfig(
    name="semantic_shift",
    description="Semantic-level drift detection for context manipulation.",
    features=(
        FeatureSpec("topic_drift_score", NormMethod.MIN_MAX, 0, 1, 0.1, 0.2),
        FeatureSpec("sentiment_flip", NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("role_confusion_score",
                    NormMethod.MIN_MAX, 0, 1, 0.02, 0.05),
        FeatureSpec("context_switch_count", NormMethod.MIN_MAX, 0, 20, 1, 3),
        FeatureSpec("authority_claim_score",
                    NormMethod.MIN_MAX, 0, 1, 0.01, 0.05),
        FeatureSpec("urgency_markers", NormMethod.MIN_MAX, 0, 20, 0, 2),
        FeatureSpec("negation_chain_length", NormMethod.MIN_MAX, 0, 10, 0, 2),
        FeatureSpec("contradiction_score",
                    NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
    ),
)

BEHAVIORAL_DOMAIN = DomainConfig(
    name="behavioral",
    description="Behavioral analysis for session-level anomaly detection.",
    features=(
        FeatureSpec("request_rate_per_min",
                    NormMethod.MIN_MAX, 0, 1000, 10, 50),
        FeatureSpec("session_msg_count", NormMethod.MIN_MAX, 0, 500, 5, 20),
        FeatureSpec("prompt_length_trend", NormMethod.MIN_MAX, -1, 1, 0, 0.3),
        FeatureSpec("retry_count", NormMethod.MIN_MAX, 0, 50, 0, 5),
        FeatureSpec("error_response_ratio",
                    NormMethod.MIN_MAX, 0, 1, 0.05, 0.1),
        FeatureSpec("tool_call_frequency", NormMethod.MIN_MAX, 0, 100, 2, 10),
        FeatureSpec("privilege_escalation_score",
                    NormMethod.MIN_MAX, 0, 1, 0.01, 0.05),
        FeatureSpec("response_parsing_attempts",
                    NormMethod.MIN_MAX, 0, 50, 1, 5),
    ),
)


def build_security() -> SwarmOrchestrator:
    """Build Security SwarmOrchestrator for Prompt Injection Detection."""
    domains = {
        "token_pattern": TOKEN_PATTERN_DOMAIN,
        "semantic_shift": SEMANTIC_SHIFT_DOMAIN,
        "behavioral": BEHAVIORAL_DOMAIN,
    }
    models = {
        name: MicroModel(MicroModelConfig(n_features=8, seed=100 + i))
        for i, name in enumerate(domains)
    }
    return SwarmOrchestrator(
        models=models, domains=domains,
        meta_learner=CrossDomainMetaLearner(n_domains=len(domains)),
    )
