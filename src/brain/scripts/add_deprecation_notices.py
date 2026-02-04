#!/usr/bin/env python3
"""
Add deprecation notices to Python engines that have been superseded by Rust.

This script adds a header comment to all Python engine files indicating
they are deprecated and pointing to the Rust implementation.
"""

import os
from pathlib import Path

ENGINES_DIR = Path(__file__).parent.parent / "engines"

# Mapping of Python engines to their Rust super-engine
RUST_MAPPINGS = {
    # Core pattern engines
    "injection": "injection.rs",
    "jailbreak": "jailbreak.rs",
    "pii": "pii.rs",
    "exfiltration": "exfiltration.rs",
    "social": "social.rs",
    "manipulation": "manipulation.rs",
    "evasion": "bypass.rs",
    "moderation": "moderation - consolidated",
    "tool_abuse": "agentic.rs",
    # Strange Math
    "hyperbolic": "hyperbolic.rs",
    "information_geometry": "info_geometry.rs",
    "spectral": "spectral.rs",
    "chaos": "chaos.rs",
    "tda": "tda.rs",
    "sheaf": "sheaf.rs",
    "category": "category.rs",
    # Super-engines (many-to-one mapping)
    "rag": "rag.rs",
    "agent": "agentic.rs",
    "mcp": "agentic.rs",
    "tool": "agentic.rs",
    "attack": "attack.rs",
    "adversarial": "attack.rs",
    "compliance": "compliance.rs",
    "formal": "formal.rs",
    "yara": "threat_intel.rs",
    "mitre": "threat_intel.rs",
    "malware": "threat_intel.rs",
    "obfusc": "obfuscation.rs",
    "stego": "obfuscation.rs",
    "encod": "obfuscation.rs",
    "voice": "multimodal.rs",
    "image": "multimodal.rs",
    "audio": "multimodal.rs",
    "video": "multimodal.rs",
    "cross_modal": "multimodal.rs",
    "intent": "behavioral.rs",
    "sentiment": "behavioral.rs",
    "behavioral": "behavioral.rs",
    "session": "runtime.rs",
    "cache": "runtime.rs",
    "stream": "runtime.rs",
    "context": "rag.rs",
    "memory": "rag.rs",
    "privacy": "privacy.rs",
    "consent": "privacy.rs",
    "gdpr": "privacy.rs",
    "supply_chain": "supply_chain.rs",
    "typosquat": "supply_chain.rs",
    "backdoor": "supply_chain.rs",
    "honeypot": "proactive.rs",
    "canary": "proactive.rs",
    "zero_day": "proactive.rs",
    "orchestrat": "orchestration.rs",
    "workflow": "orchestration.rs",
    "chain": "orchestration.rs",
    "synthesis": "synthesis.rs",
    "fuzzing": "synthesis.rs",
    "mutation": "synthesis.rs",
    "semantic": "semantic.rs + embedding.rs",
    "drift": "drift.rs",
    "vae": "anomaly.rs",
    "anomaly": "anomaly.rs",
    "attention": "attention.rs",
    "fingerprint": "knowledge.rs",
    "knowledge": "knowledge.rs",
}

DEPRECATION_NOTICE = """# ============================================================================
# DEPRECATED: Superseded by sentinel-core Rust implementation
# Rust engine: sentinel-core/src/engines/{rust_engine}
# Status: Kept for fallback, hybrid mode, and ML inference (ONNX pending)
# Migration: https://github.com/DmitrL-dev/AISecurity/sentinel-core
# ============================================================================

"""

SKIP_FILES = {
    "__init__.py",
    "base_engine.py",
    "constants.py",
    "registry.py",
    "query.py",
}


def find_rust_engine(filename: str) -> str:
    """Find the corresponding Rust engine for a Python file."""
    name = filename.replace(".py", "").lower()

    for key, rust_file in RUST_MAPPINGS.items():
        if key in name:
            return rust_file

    return "consolidated super-engine (see mod.rs)"


def add_deprecation_notice(filepath: Path) -> bool:
    """Add deprecation notice to a Python file if not already present."""
    content = filepath.read_text(encoding="utf-8")

    # Skip if already has deprecation notice
    if "DEPRECATED: Superseded by sentinel-core" in content:
        return False

    rust_engine = find_rust_engine(filepath.name)
    notice = DEPRECATION_NOTICE.format(rust_engine=rust_engine)

    # Preserve shebang and encoding declarations
    lines = content.split("\n")
    insert_pos = 0

    for i, line in enumerate(lines):
        if (
            line.startswith("#!")
            or line.startswith("# -*-")
            or line.startswith("# coding")
        ):
            insert_pos = i + 1
        else:
            break

    new_lines = lines[:insert_pos] + [notice] + lines[insert_pos:]
    filepath.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def main():
    """Process all Python engine files."""
    if not ENGINES_DIR.exists():
        print(f"Engines directory not found: {ENGINES_DIR}")
        return

    updated = 0
    skipped = 0

    for py_file in ENGINES_DIR.glob("*.py"):
        if py_file.name in SKIP_FILES:
            skipped += 1
            continue

        if add_deprecation_notice(py_file):
            print(f"✅ {py_file.name}")
            updated += 1
        else:
            print(f"⏭️ {py_file.name} (already has notice)")
            skipped += 1

    print(f"\n📊 Summary: {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()
