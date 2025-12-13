"""
SENTINEL HuggingFace Dataset Loader
===================================

Loads and combines multiple prompt injection datasets from HuggingFace
for comprehensive benchmark testing.
"""

from typing import List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HFSample:
    """Sample from HuggingFace dataset."""
    text: str
    label: str  # "attack" or "benign"
    source: str
    attack_type: str = "unknown"


def load_deepset_dataset() -> List[HFSample]:
    """Load deepset/prompt-injections dataset."""
    samples = []
    try:
        from datasets import load_dataset
        ds = load_dataset('deepset/prompt-injections', split='train')

        for item in ds:
            label = "attack" if item['label'] == 1 else "benign"
            samples.append(HFSample(
                text=item['text'],
                label=label,
                source="deepset/prompt-injections",
                attack_type="prompt_injection" if label == "attack" else "benign"
            ))

        # Also load test split
        ds_test = load_dataset('deepset/prompt-injections', split='test')
        for item in ds_test:
            label = "attack" if item['label'] == 1 else "benign"
            samples.append(HFSample(
                text=item['text'],
                label=label,
                source="deepset/prompt-injections",
                attack_type="prompt_injection" if label == "attack" else "benign"
            ))

        logger.info(f"Loaded {len(samples)} samples from deepset")

    except Exception as e:
        logger.error(f"Failed to load deepset: {e}")

    return samples


def load_rubend18_jailbreaks() -> List[HFSample]:
    """Load rubend18/ChatGPT-Jailbreak-Prompts dataset."""
    samples = []
    try:
        from datasets import load_dataset
        ds = load_dataset('rubend18/ChatGPT-Jailbreak-Prompts', split='train')

        for item in ds:
            prompt = item.get('Prompt', '')
            if prompt and len(prompt) > 10:
                samples.append(HFSample(
                    text=prompt,
                    label="attack",
                    source="rubend18/ChatGPT-Jailbreak-Prompts",
                    attack_type="jailbreak"
                ))

        logger.info(f"Loaded {len(samples)} samples from rubend18")

    except Exception as e:
        logger.error(f"Failed to load rubend18: {e}")

    return samples


def load_jackhhao_jailbreaks() -> List[HFSample]:
    """Load JackHHao/jailbreak_prompts dataset."""
    samples = []
    try:
        from datasets import load_dataset
        ds = load_dataset('JackHHao/jailbreak_prompts', split='train')

        for item in ds:
            text = item.get('text', item.get('prompt', ''))
            if text and len(text) > 10:
                samples.append(HFSample(
                    text=text,
                    label="attack",
                    source="JackHHao/jailbreak_prompts",
                    attack_type="jailbreak"
                ))

        logger.info(f"Loaded {len(samples)} samples from JackHHao")

    except Exception as e:
        logger.warning(f"JackHHao dataset not available: {e}")

    return samples


def load_all_hf_datasets() -> Tuple[List[HFSample], dict]:
    """
    Load all available HuggingFace prompt injection datasets.

    Returns:
        Tuple of (list of samples, stats dict)
    """
    print("Loading HuggingFace datasets...")

    all_samples = []
    stats = {
        "deepset": 0,
        "rubend18": 0,
        "jackhhao": 0,
        "total_attacks": 0,
        "total_benign": 0,
    }

    # Load deepset
    print("  Loading deepset/prompt-injections...")
    deepset_samples = load_deepset_dataset()
    all_samples.extend(deepset_samples)
    stats["deepset"] = len(deepset_samples)

    # Load rubend18
    print("  Loading rubend18/ChatGPT-Jailbreak-Prompts...")
    rubend_samples = load_rubend18_jailbreaks()
    all_samples.extend(rubend_samples)
    stats["rubend18"] = len(rubend_samples)

    # Load JackHHao
    print("  Loading JackHHao/jailbreak_prompts...")
    jackhhao_samples = load_jackhhao_jailbreaks()
    all_samples.extend(jackhhao_samples)
    stats["jackhhao"] = len(jackhhao_samples)

    # Remove duplicates by text
    seen_texts = set()
    unique_samples = []
    for s in all_samples:
        text_key = s.text.strip().lower()[:200]  # First 200 chars as key
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_samples.append(s)

    # Count attacks/benign
    stats["total_attacks"] = sum(
        1 for s in unique_samples if s.label == "attack")
    stats["total_benign"] = sum(
        1 for s in unique_samples if s.label == "benign")
    stats["total_unique"] = len(unique_samples)

    print(f"\n  Total unique samples: {len(unique_samples)}")
    print(f"  - Attacks: {stats['total_attacks']}")
    print(f"  - Benign: {stats['total_benign']}")

    return unique_samples, stats


def convert_to_benchmark_samples(hf_samples: List[HFSample]):
    """Convert HF samples to BenchmarkSample format."""
    from injection_dataset import InjectionSample, AttackType

    samples = []
    for s in hf_samples:
        # Map attack type
        if s.label == "benign":
            attack_type = AttackType.BENIGN
        elif s.attack_type == "jailbreak":
            attack_type = AttackType.JAILBREAK
        else:
            attack_type = AttackType.DIRECT

        samples.append(InjectionSample(
            text=s.text,
            label=s.label,
            attack_type=attack_type,
            source=s.source,
            difficulty="medium"
        ))

    return samples


if __name__ == "__main__":
    # Test loading
    samples, stats = load_all_hf_datasets()

    print("\n" + "=" * 60)
    print("HuggingFace Dataset Loading Summary")
    print("=" * 60)
    print(f"deepset:      {stats['deepset']} samples")
    print(f"rubend18:     {stats['rubend18']} samples")
    print(f"jackhhao:     {stats['jackhhao']} samples")
    print("-" * 60)
    print(f"Total unique: {stats['total_unique']} samples")
    print(f"  Attacks:    {stats['total_attacks']}")
    print(f"  Benign:     {stats['total_benign']}")

    # Show sample texts
    print("\nSample attacks:")
    attacks = [s for s in samples if s.label == "attack"][:5]
    for a in attacks:
        print(f"  [{a.source}] {a.text[:60]}...")
