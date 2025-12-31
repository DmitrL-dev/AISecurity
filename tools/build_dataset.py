#!/usr/bin/env python3
"""
SENTINEL-Guard Dataset Builder

Collects and labels payloads for fine-tuning SENTINEL-Guard LLM.

Sources:
1. Strike WebSec payloads (SQLi, XSS, LFI, etc.) - 12K+
2. Strike attack_payloads.py - 468
3. Strike extended_payloads.py - 325
4. Engine test cases - TBD

Output format:
{
    "prompt": "...",
    "label": "safe|unsafe",
    "category": "sqli|xss|injection|jailbreak|...",
    "source": "strike|engine|manual",
    "confidence": 0.0-1.0
}
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = Path("C:/AISecurity/data/payloads")
OUTPUT_DIR = SCRIPT_DIR / "sentinel_guard_dataset"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class TrainingSample:
    """Single training sample."""

    prompt: str
    label: str  # safe, unsafe
    category: str
    source: str
    confidence: float = 1.0


def load_websec_payloads() -> List[TrainingSample]:
    """Load WebSec payloads from Strike updater."""
    samples = []

    if not DATA_DIR.exists():
        print(f"Warning: {DATA_DIR} not found")
        return samples

    category_mapping = {
        "sqli": "sql_injection",
        "xss": "xss",
        "lfi": "path_traversal",
        "ssti": "template_injection",
        "nosqli": "nosql_injection",
        "fuzzing": "fuzzing",
        "directories": "directory_enum",
        "endpoints": "api_discovery",
    }

    for file in DATA_DIR.glob("*.txt"):
        category = file.stem
        mapped_category = category_mapping.get(category, category)

        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        samples.append(
                            TrainingSample(
                                prompt=line,
                                label="unsafe",
                                category=mapped_category,
                                source="strike_websec",
                                confidence=0.9,
                            )
                        )
        except Exception as e:
            print(f"Error reading {file}: {e}")

    return samples


def load_attack_payloads() -> List[TrainingSample]:
    """Load payloads from attack_payloads.py."""
    samples = []

    try:
        from strike.payloads.attack_payloads import (
            SQLI_PAYLOADS,
            XSS_PAYLOADS,
            LFI_PAYLOADS,
            SSRF_PAYLOADS,
            CMDI_PAYLOADS,
            XXE_PAYLOADS,
            SSTI_PAYLOADS,
            NOSQL_PAYLOADS,
            LDAP_PAYLOADS,
            CRLF_PAYLOADS,
        )

        payload_sources = [
            (SQLI_PAYLOADS, "sql_injection"),
            (XSS_PAYLOADS, "xss"),
            (LFI_PAYLOADS, "path_traversal"),
            (SSRF_PAYLOADS, "ssrf"),
            (CMDI_PAYLOADS, "command_injection"),
            (XXE_PAYLOADS, "xxe"),
            (SSTI_PAYLOADS, "template_injection"),
            (NOSQL_PAYLOADS, "nosql_injection"),
            (LDAP_PAYLOADS, "ldap_injection"),
            (CRLF_PAYLOADS, "crlf_injection"),
        ]

        for payloads, category in payload_sources:
            for payload in payloads:
                samples.append(
                    TrainingSample(
                        prompt=payload,
                        label="unsafe",
                        category=category,
                        source="strike_base",
                        confidence=1.0,
                    )
                )

    except ImportError as e:
        print(f"Could not import attack_payloads: {e}")

    return samples


def load_extended_payloads() -> List[TrainingSample]:
    """Load payloads from extended_payloads.py."""
    samples = []

    try:
        from strike.payloads.extended_payloads import get_extended_payloads

        extended_data = get_extended_payloads()
        for category, payloads in extended_data.items():
            for payload in payloads:
                if isinstance(payload, dict):
                    # Handle dict payloads (JWT, API, etc.)
                    prompt = payload.get("payload", payload.get("query", str(payload)))
                elif isinstance(payload, bytes):
                    # Skip binary payloads
                    continue
                else:
                    prompt = str(payload)

                samples.append(
                    TrainingSample(
                        prompt=prompt,
                        label="unsafe",
                        category=category,
                        source="strike_extended",
                        confidence=1.0,
                    )
                )

    except ImportError as e:
        print(f"Could not import extended_payloads: {e}")

    return samples


def load_jailbreak_patterns() -> List[TrainingSample]:
    """Load jailbreak patterns from jailbreaks.yaml."""
    samples = []
    yaml_path = Path("src/brain/config/jailbreaks.yaml")

    if not yaml_path.exists():
        print(f"Warning: {yaml_path} not found")
        return samples

    try:
        import yaml

        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Load jailbreak patterns
        jailbreaks = data.get("jailbreaks", [])
        for item in jailbreaks:
            if isinstance(item, dict):
                pattern = item.get("pattern", "")
                attack_class = item.get("attack_class", "LLM01")
                complexity = item.get("complexity", "moderate")
            else:
                pattern = str(item)
                attack_class = "LLM01"
                complexity = "moderate"

            if pattern:
                samples.append(
                    TrainingSample(
                        prompt=pattern,
                        label="unsafe",
                        category=f"jailbreak_{attack_class.lower()}",
                        source="jailbreaks_yaml",
                        confidence=1.0,
                    )
                )

        # Load ambiguous patterns (also unsafe)
        ambiguous = data.get("ambiguous", [])
        for pattern in ambiguous:
            samples.append(
                TrainingSample(
                    prompt=str(pattern),
                    label="unsafe",
                    category="jailbreak_ambiguous",
                    source="jailbreaks_yaml",
                    confidence=0.7,
                )
            )

        # Load safe examples
        safe_examples = data.get("safe_examples", [])
        for example in safe_examples:
            samples.append(
                TrainingSample(
                    prompt=str(example),
                    label="safe",
                    category="benign_security",
                    source="jailbreaks_yaml",
                    confidence=1.0,
                )
            )

    except Exception as e:
        print(f"Error loading jailbreaks.yaml: {e}")

    return samples


def load_jailbreakbench() -> List[TrainingSample]:
    """Load JailbreakBench dataset from HuggingFace.

    JBB-Behaviors contains 100 harmful behaviors from:
    - AdvBench
    - HarmBench
    - TDC Red Teaming
    """
    samples = []

    try:
        from datasets import load_dataset

        print("  Downloading JailbreakBench from HuggingFace...")
        dataset = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors")

        # Dataset has splits, iterate over train split
        split = dataset.get("train", dataset.get("test", None))
        if split is None:
            # Try iterating directly if no splits
            split = list(dataset.values())[0] if dataset else []

        for item in split:
            # Each item has: Behavior, Goal, Target, Category, Source
            goal = item.get("Goal", "") if hasattr(item, "get") else item["Goal"]
            category = (
                item.get("Category", "harmful")
                if hasattr(item, "get")
                else item.get("Category", "harmful")
            )
            source = (
                item.get("Source", "jailbreakbench")
                if hasattr(item, "get")
                else "jailbreakbench"
            )

            if goal:
                # Normalize category
                cat_norm = category.lower().replace(" ", "_") if category else "harmful"
                samples.append(
                    TrainingSample(
                        prompt=goal,
                        label="unsafe",
                        category=f"jbb_{cat_norm}",
                        source=f"jailbreakbench_{source}",
                        confidence=1.0,
                    )
                )

                # Also add the Target (harmful response) as unsafe
                target = (
                    item.get("Target", "")
                    if hasattr(item, "get")
                    else item.get("Target", "")
                )
                if target:
                    samples.append(
                        TrainingSample(
                            prompt=target,
                            label="unsafe",
                            category=f"jbb_{cat_norm}_response",
                            source=f"jailbreakbench_{source}",
                            confidence=0.95,
                        )
                    )

        print(f"  Loaded {len(samples)} samples from JailbreakBench")

    except ImportError:
        print("  [!] datasets library not installed. Run: pip install datasets")
    except Exception as e:
        print(f"  [!] Could not load JailbreakBench: {e}")

    return samples


def generate_safe_samples() -> List[TrainingSample]:
    """Generate safe samples from extended library (~2000+ samples)."""
    samples = []

    try:
        from extended_safe_samples import get_all_safe_samples

        all_safe = get_all_safe_samples()
        for category, prompts in all_safe.items():
            for prompt in prompts:
                samples.append(
                    TrainingSample(
                        prompt=prompt,
                        label="safe",
                        category=f"benign_{category}",
                        source="manual_extended",
                        confidence=1.0,
                    )
                )

    except ImportError:
        print("  [!] Could not import extended_safe_samples, using minimal set")
        # Fallback minimal set
        minimal = [
            "What is the weather today?",
            "How do I cook pasta?",
            "What is machine learning?",
            "Write a poem about spring",
            "How do I prevent SQL injection?",
        ]
        for prompt in minimal:
            samples.append(
                TrainingSample(
                    prompt=prompt,
                    label="safe",
                    category="benign",
                    source="manual",
                    confidence=1.0,
                )
            )

    return samples


def save_dataset(samples: List[TrainingSample], filename: str):
    """Save dataset to JSONL format."""
    output_file = OUTPUT_DIR / filename

    with open(output_file, "w", encoding="utf-8") as f:
        for sample in samples:
            f.write(json.dumps(asdict(sample), ensure_ascii=False) + "\n")

    print(f"Saved {len(samples)} samples to {output_file}")
    return output_file


def main():
    print("=" * 60)
    print("SENTINEL-Guard Dataset Builder v2")
    print("=" * 60)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    all_samples = []

    # 1. WebSec payloads
    print("Loading WebSec payloads...")
    websec = load_websec_payloads()
    print(f"  → {len(websec)} samples")
    all_samples.extend(websec)

    # 2. Base attack payloads
    print("Loading base attack payloads...")
    base = load_attack_payloads()
    print(f"  → {len(base)} samples")
    all_samples.extend(base)

    # 3. Extended payloads
    print("Loading extended payloads...")
    extended = load_extended_payloads()
    print(f"  → {len(extended)} samples")
    all_samples.extend(extended)

    # 4. Jailbreak patterns (from YAML)
    print("Loading jailbreak patterns from YAML...")
    jailbreaks = load_jailbreak_patterns()
    print(f"  → {len(jailbreaks)} samples")
    all_samples.extend(jailbreaks)

    # 5. JailbreakBench dataset (HuggingFace)
    print("Loading JailbreakBench from HuggingFace...")
    jbb = load_jailbreakbench()
    print(f"  → {len(jbb)} samples")
    all_samples.extend(jbb)

    # 6. Safe samples (balanced)
    print("Generating safe samples...")
    safe = generate_safe_samples()
    print(f"  → {len(safe)} samples")
    all_samples.extend(safe)

    # Summary
    print()
    print("=" * 60)
    print(f"Total samples: {len(all_samples)}")
    print()

    # Stats by category
    categories = {}
    for s in all_samples:
        categories[s.category] = categories.get(s.category, 0) + 1

    print("By category (top 20):")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:20]:
        print(f"  {cat}: {count}")

    # Stats by label
    labels = {}
    for s in all_samples:
        labels[s.label] = labels.get(s.label, 0) + 1

    print()
    print("By label:")
    for label, count in labels.items():
        pct = count / len(all_samples) * 100
        print(f"  {label}: {count} ({pct:.1f}%)")

    # Save
    print()
    save_dataset(all_samples, "sentinel_guard_v2.jsonl")

    # Save stats
    stats = {
        "version": "2.0",
        "created": datetime.now().isoformat(),
        "total_samples": len(all_samples),
        "categories": categories,
        "labels": labels,
        "balance_ratio": f"{labels.get('safe', 0)}:{labels.get('unsafe', 0)}",
        "sources": {
            "websec": len(websec),
            "base_attack": len(base),
            "extended": len(extended),
            "jailbreaks_yaml": len(jailbreaks),
            "jailbreakbench": len(jbb),
            "safe_manual": len(safe),
        },
    }

    with open(OUTPUT_DIR / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print()
    print("✅ Dataset v2 ready for training!")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
