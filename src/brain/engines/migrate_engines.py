"""
Script to add base class imports and type hints to all research invention engines.
Run from engines directory.
"""

import os
import re
import glob

# Engines to migrate (research inventions)
ENGINES = [
    "adversarial_prompt_detector.py",
    "agent_memory_shield.py",
    "atomic_operation_enforcer.py",
    "behavioral_api_verifier.py",
    "cache_isolation_guardian.py",
    "causal_inference_detector.py",
    "compliance_policy_engine.py",
    "context_window_guardian.py",
    "contrastive_prompt_anomaly.py",
    "conversation_state_validator.py",
    "cot_guardian.py",
    "cross_modal_security_analyzer.py",
    "distilled_security_ensemble.py",
    "dynamic_rate_limiter.py",
    "emergent_security_mesh.py",
    "explainable_security_decisions.py",
    "federated_threat_aggregator.py",
    "formal_safety_verifier.py",
    "gan_adversarial_defense.py",
    "hierarchical_defense_network.py",
    "input_length_analyzer.py",
    "intent_aware_semantic_analyzer.py",
    "language_detection_guard.py",
    "meta_attack_adapter.py",
    "model_watermark_verifier.py",
    "multi_agent_coordinator.py",
    "multi_layer_canonicalizer.py",
    "output_sanitization_guard.py",
    "prompt_leakage_detector.py",
    "provenance_tracker.py",
    "quantum_safe_model_vault.py",
    "rag_security_shield.py",
    "recursive_injection_guard.py",
    "reinforcement_safety_agent.py",
    "response_consistency_checker.py",
    "safety_grammar_enforcer.py",
    "secure_model_loader.py",
    "semantic_boundary_enforcer.py",
    "semantic_drift_detector.py",
    "sentiment_manipulation_detector.py",
    "shadow_ai_detector.py",
    "symbolic_reasoning_guard.py",
    "system_prompt_shield.py",
    "temporal_pattern_analyzer.py",
    "tool_use_guardian.py",
    "transformer_attention_shield.py",
    "vae_prompt_anomaly_detector.py",
    "zero_trust_verification.py",
]


def add_base_import(content: str) -> str:
    """Add base class import after existing imports."""

    # Check if already has base import
    if "from base_engine import" in content:
        return content

    # Find last import line
    lines = content.split("\n")
    last_import_idx = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i

    # Insert base import after last import
    base_import = "\nfrom base_engine import Severity, Action  # Base classes"
    lines.insert(last_import_idx + 1, base_import)

    return "\n".join(lines)


def add_version_property(content: str) -> str:
    """Add version property to main class if missing."""

    # Check if already has version
    if (
        "def version(self)" in content
        or "@property" in content
        and "version" in content
    ):
        return content

    # Find class __init__
    init_match = re.search(r"(def __init__\(self.*?\):)", content)
    if not init_match:
        return content

    # Add version and name properties before __init__
    version_code = """
    @property
    def name(self) -> str:
        return self.__class__.__name__
    
    @property 
    def version(self) -> str:
        return "1.0.0"
    
"""

    # Insert before __init__
    content = content.replace(
        init_match.group(1), version_code + "    " + init_match.group(1)
    )

    return content


def process_file(filepath: str) -> bool:
    """Process single file."""

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content

    # Add base import
    content = add_base_import(content)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    return False


def main():
    """Process all engines."""

    processed = 0
    skipped = 0

    for engine in ENGINES:
        if os.path.exists(engine):
            if process_file(engine):
                print(f"✅ Processed: {engine}")
                processed += 1
            else:
                print(f"⏭️ Skipped (no changes): {engine}")
                skipped += 1
        else:
            print(f"❌ Not found: {engine}")

    print(f"\n📊 Summary: {processed} processed, {skipped} skipped")


if __name__ == "__main__":
    main()
