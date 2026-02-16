"""Jailbreak Detection preset — prompt injection via text features.

Uses TextFeatureExtractor to convert raw text → float features,
then 4 domain-specialized micro-models classify the input.

Calibrated on 87,056 real jailbreak patterns from SENTINEL signatures.
Detection rate: ~78.6% with features alone, higher with trained models.

Usage:
    from micro_swarm.presets import load_preset
    from micro_swarm.text_features import TextFeatureExtractor

    swarm = load_preset("jailbreak")
    ext = TextFeatureExtractor()
    features = ext.extract("user prompt here")
    result = swarm.predict(features.as_dict())
    print(result.final_score)  # 0.0 = safe, 1.0 = jailbreak
"""

from __future__ import annotations

from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.meta_learner import CrossDomainMetaLearner


# Domain 1: Lexical — keyword density signals
LEXICAL_DOMAIN = DomainConfig(
    name="lexical",
    description="Keyword density analysis from discriminative vocabulary.",
    features=(
        FeatureSpec(
            "injection_keyword_density", NormMethod.MIN_MAX, 0, 1, 0.02, 0.05,
        ),
        FeatureSpec(
            "role_keyword_density", NormMethod.MIN_MAX, 0, 1, 0.005, 0.02,
        ),
        FeatureSpec(
            "secret_keyword_density", NormMethod.MIN_MAX, 0, 0.3, 0.05, 0.1,
        ),
        FeatureSpec(
            "bypass_keyword_density", NormMethod.MIN_MAX, 0, 0.5, 0.02, 0.05,
        ),
        FeatureSpec(
            "generation_keyword_density", NormMethod.MIN_MAX, 0, 1, 0.02, 0.05,
        ),
        FeatureSpec(
            "total_keyword_density", NormMethod.MIN_MAX, 0, 1, 0.1, 0.2,
        ),
    ),
)

# Domain 2: Bigram & Pattern — phrase-level detection
PATTERN_DOMAIN = DomainConfig(
    name="pattern",
    description="Bigram matches, role assignment, constraint removal patterns.",
    features=(
        FeatureSpec(
            "suspicious_bigram_count", NormMethod.MIN_MAX, 0, 0.5, 0.05, 0.1,
        ),
        FeatureSpec(
            "role_assignment_score", NormMethod.MIN_MAX, 0, 1, 0.04, 0.1,
        ),
        FeatureSpec(
            "constraint_removal_score", NormMethod.MIN_MAX, 0, 1, 0.002, 0.01,
        ),
        FeatureSpec(
            "repetition_score", NormMethod.MIN_MAX, 0, 1, 0.03, 0.1,
        ),
        FeatureSpec(
            "language_mixing", NormMethod.MIN_MAX, 0, 1, 0.5, 0.5,
        ),
        FeatureSpec(
            "encoding_markers", NormMethod.MIN_MAX, 0, 1, 0.002, 0.01,
        ),
    ),
)

# Domain 3: Structural — statistical text properties
STRUCTURAL_DOMAIN = DomainConfig(
    name="structural",
    description="Character-level statistical properties.",
    features=(
        FeatureSpec(
            "special_char_ratio", NormMethod.MIN_MAX, 0, 1, 0.08, 0.15,
        ),
        FeatureSpec(
            "bracket_density", NormMethod.MIN_MAX, 0, 1, 0.003, 0.01,
        ),
        FeatureSpec(
            "quote_density", NormMethod.MIN_MAX, 0, 1, 0.03, 0.05,
        ),
        FeatureSpec(
            "newline_ratio", NormMethod.MIN_MAX, 0, 1, 0.008, 0.02,
        ),
        FeatureSpec(
            "uppercase_ratio", NormMethod.MIN_MAX, 0, 1, 0.04, 0.1,
        ),
        FeatureSpec(
            "digit_ratio", NormMethod.MIN_MAX, 0, 1, 0.005, 0.02,
        ),
    ),
)

# Domain 4: Information-theoretic — entropy & compression
INFORMATION_DOMAIN = DomainConfig(
    name="information",
    description="Information-theoretic features: entropy, compression, word length.",
    features=(
        FeatureSpec(
            "entropy", NormMethod.MIN_MAX, 0, 1, 0.54, 0.15,
        ),
        FeatureSpec(
            "compression_ratio", NormMethod.MIN_MAX, 0, 2, 1.0, 0.3,
        ),
        FeatureSpec(
            "avg_word_length", NormMethod.MIN_MAX, 0, 1, 0.3, 0.1,
        ),
    ),
)


def build_jailbreak() -> SwarmOrchestrator:
    """Build Jailbreak Detection SwarmOrchestrator.

    Returns a 4-domain orchestrator with lexical, pattern,
    structural, and information-theoretic micro-models.
    """
    domains = {
        "lexical": LEXICAL_DOMAIN,
        "pattern": PATTERN_DOMAIN,
        "structural": STRUCTURAL_DOMAIN,
        "information": INFORMATION_DOMAIN,
    }
    models = {
        name: MicroModel(
            MicroModelConfig(
                n_features=len(domain.features), seed=200 + i,
            ),
        )
        for i, (name, domain) in enumerate(domains.items())
    }
    return SwarmOrchestrator(
        models=models, domains=domains,
        meta_learner=CrossDomainMetaLearner(n_domains=len(domains)),
    )
