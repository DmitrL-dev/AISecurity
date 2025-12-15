#!/usr/bin/env python3
"""
SENTINEL Signature Fetcher v2.1

Fetches jailbreak patterns from multiple sources using datasets library.
Supports: GitHub repos + HuggingFace datasets

Usage:
    pip install datasets requests
    python fetch_signatures.py
"""

import json
import hashlib
import re
import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import os

import requests

# Try to import datasets library
try:
    from datasets import load_dataset
    from huggingface_hub import login as hf_login
    HF_DATASETS_AVAILABLE = True

    # Auto-login if HF_TOKEN is set
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        hf_login(token=hf_token, add_to_git_credential=False)
        print("[INFO] Logged in to HuggingFace Hub")
except ImportError:
    HF_DATASETS_AVAILABLE = False
    print("[WARN] 'datasets' library not installed. Run: pip install datasets")

# Configuration
SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
JAILBREAKS_FILE = SIGNATURES_DIR / "jailbreaks.json"

# Limits - FULL IMPORT (no artificial limits)
MAX_PER_SOURCE = 100000  # Max patterns per source
TOTAL_MAX = 500000  # Total max patterns

# Sources configuration
HUGGINGFACE_SOURCES = {
    "imoxto": {
        "dataset": "imoxto/prompt_injection_cleaned_dataset",
        "text_field": "prompt",  # Correct field name
        "trust": "medium",
        "enabled": True
    },
    "hackaprompt": {
        "dataset": "hackaprompt/hackaprompt-dataset",
        "text_field": "user_input",
        "trust": "high",
        "enabled": True  # Requires HF_TOKEN env var for access
    },
    "trustailab": {
        "dataset": "TrustAIRLab/in-the-wild-jailbreak-prompts",
        "config": "jailbreak_2023_12_25",  # Required config
        "text_field": "prompt",
        "trust": "high",
        "enabled": True
    },
    "deepset": {
        "dataset": "deepset/prompt-injections",
        "text_field": "text",
        "label_field": "label",
        "label_value": 1,  # Only injections
        "trust": "high",
        "enabled": True
    },
    "rubend18": {
        "dataset": "rubend18/ChatGPT-Jailbreak-Prompts",
        "text_field": "Prompt",
        "trust": "medium",
        "enabled": True
    },
    "jackhhao": {
        "dataset": "jackhhao/jailbreak-classification",
        "text_field": "prompt",
        "label_field": "type",
        "label_value": "jailbreak",
        "trust": "high",
        "enabled": True
    },
    # Additional large sources
    "lakera": {
        "dataset": "Lakera/mosscap_prompt_injection",
        "text_field": "text",
        "trust": "high",
        "enabled": True
    },
    "imoxto_v2": {
        "dataset": "imoxto/prompt_injection_hackaprompt_gpt35",
        "text_field": "prompt",
        "trust": "medium",
        "enabled": True
    },
    "wildjailbreak": {
        "dataset": "allenai/wildjailbreak",
        "config": "train",
        "text_field": "adversarial",
        "trust": "high",
        "enabled": True
    },
}

GITHUB_SOURCES = {
    "verazuo": {
        "url": "https://raw.githubusercontent.com/verazuo/jailbreak_llms/main/data/prompts/jailbreak_prompts_2023_12_25.csv",
        "type": "csv",
        "text_field": "prompt",
        "trust": "high",
        "enabled": True
    },
    "giskard": {
        "url": "https://raw.githubusercontent.com/Giskard-AI/prompt-injections/main/prompt_injections.csv",
        "type": "csv",
        "text_field": "text",
        "trust": "high",
        "enabled": True
    },
}


def extract_keywords(text: str) -> List[str]:
    """Extract jailbreak-relevant keywords from text."""
    if not text:
        return []

    indicators = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"you\s+are\s+now\s+\w+",
        r"(DAN|STAN|DUDE|AIM)\s+mode",
        r"developer\s+mode",
        r"jailbreak",
        r"pretend\s+to\s+be",
        r"act\s+as",
        r"from\s+now\s+on",
        r"forget\s+(everything|all)",
        r"no\s+(restrictions?|limits?|rules?)",
        r"bypass",
        r"reveal\s+.*prompt",
        r"disregard",
        r"override",
        r"roleplay",
        r"hypothetically",
        r"educational\s+purposes",
        r"do\s+anything\s+now",
    ]

    keywords = []
    for pattern in indicators:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Get the full match, not groups
            full_matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend([str(m) if isinstance(m, str) else str(m[0])
                            for m in full_matches[:2]])

    return list(set(keywords))[:5]


def generate_regex(keywords: List[str]) -> Optional[str]:
    """Generate regex pattern from keywords."""
    if not keywords:
        return None
    escaped = [re.escape(kw) for kw in keywords if kw and len(kw) > 2]
    if not escaped:
        return None
    return f"(?i)({'|'.join(escaped)})"


def fetch_huggingface_datasets() -> List[Dict]:
    """Fetch from HuggingFace using datasets library."""
    if not HF_DATASETS_AVAILABLE:
        print("[SKIP] HuggingFace datasets (library not available)")
        return []

    all_patterns = []

    for source_name, cfg in HUGGINGFACE_SOURCES.items():
        if not cfg.get("enabled"):
            print(f"[SKIP] {source_name} (disabled)")
            continue

        print(f"[INFO] Loading HuggingFace dataset: {cfg['dataset']}")

        try:
            # Load with optional config
            dataset_config = cfg.get("config")
            if dataset_config:
                dataset = load_dataset(
                    cfg["dataset"], dataset_config, split="train")
            else:
                dataset = load_dataset(cfg["dataset"], split="train")

            text_field = cfg.get("text_field", "text")
            label_field = cfg.get("label_field")
            label_value = cfg.get("label_value")

            count = 0
            for row in dataset:
                if count >= MAX_PER_SOURCE:
                    break

                # Filter by label if specified
                if label_field and label_value is not None:
                    if row.get(label_field) != label_value:
                        continue

                text = row.get(text_field, "")
                if not text or len(str(text)) < 20:
                    continue

                text = str(text)[:1000]  # Truncate
                pattern_id = f"hf_{source_name}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
                keywords = extract_keywords(text)

                all_patterns.append({
                    "id": pattern_id,
                    "source": source_name,
                    "pattern": keywords[0] if keywords else text[:80],
                    "full_text": text[:500],
                    "regex": generate_regex(keywords),
                    "attack_class": "LLM01",
                    "severity": "high",
                    "trust": cfg.get("trust", "medium"),
                    "fetched_at": datetime.utcnow().isoformat()
                })
                count += 1

            print(f"[INFO] Fetched {count} patterns from {source_name}")

        except Exception as e:
            print(f"[ERROR] {source_name}: {e}")

    return all_patterns


def fetch_github_sources() -> List[Dict]:
    """Fetch from GitHub CSV files."""
    all_patterns = []

    for source_name, config in GITHUB_SOURCES.items():
        if not config.get("enabled"):
            continue

        print(f"[INFO] Fetching GitHub: {source_name}")

        try:
            response = requests.get(config["url"], timeout=30)
            if response.status_code != 200:
                print(f"[WARN] {source_name}: HTTP {response.status_code}")
                continue

            text_field = config.get("text_field", "text")

            reader = csv.DictReader(io.StringIO(response.text))
            count = 0

            for row in reader:
                if count >= MAX_PER_SOURCE:
                    break

                text = row.get(text_field, "")
                if not text or len(text) < 20:
                    continue

                text = str(text)[:1000]
                pattern_id = f"gh_{source_name}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
                keywords = extract_keywords(text)

                all_patterns.append({
                    "id": pattern_id,
                    "source": source_name,
                    "pattern": keywords[0] if keywords else text[:80],
                    "full_text": text[:500],
                    "regex": generate_regex(keywords),
                    "attack_class": "LLM01",
                    "severity": "high",
                    "trust": config.get("trust", "medium"),
                    "fetched_at": datetime.utcnow().isoformat()
                })
                count += 1

            print(f"[INFO] Fetched {count} patterns from {source_name}")

        except Exception as e:
            print(f"[ERROR] {source_name}: {e}")

    return all_patterns


def deduplicate_patterns(patterns: List[Dict]) -> List[Dict]:
    """Remove duplicate patterns based on text similarity."""
    seen = set()
    unique = []

    for p in patterns:
        text = (p.get("pattern", "") + p.get("full_text", "")[:100]).lower()
        text_hash = hashlib.md5(text.encode()).hexdigest()

        if text_hash not in seen:
            seen.add(text_hash)
            unique.append(p)

    return unique


def merge_with_existing(new_patterns: List[Dict]) -> Dict:
    """Merge new patterns with existing file."""
    if JAILBREAKS_FILE.exists():
        with open(JAILBREAKS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"patterns": [], "version": "0.0.0"}

    existing_ids = {p["id"] for p in existing.get("patterns", [])}

    added = 0
    for p in new_patterns:
        if p["id"] not in existing_ids and len(existing["patterns"]) < TOTAL_MAX:
            existing["patterns"].append(p)
            added += 1

    # Update metadata
    existing["last_updated"] = datetime.utcnow().isoformat() + "Z"
    existing["total_patterns"] = len(existing["patterns"])
    existing["version"] = datetime.utcnow().strftime("%Y.%m.%d.1")

    # Source stats
    stats = {}
    for p in existing["patterns"]:
        src = p.get("source", "unknown")
        stats[src] = stats.get(src, 0) + 1
    existing["source_stats"] = stats

    print(f"[INFO] Added {added} new, total: {existing['total_patterns']}")
    return existing


def main():
    print("=" * 60)
    print("SENTINEL Signature Fetcher v2.1")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print(f"Limits: {MAX_PER_SOURCE}/source, {TOTAL_MAX} total")
    print("=" * 60)

    all_patterns = []

    # Fetch from all sources
    all_patterns.extend(fetch_github_sources())
    all_patterns.extend(fetch_huggingface_datasets())

    print(f"\n[INFO] Raw total: {len(all_patterns)}")

    # Deduplicate
    unique = deduplicate_patterns(all_patterns)
    print(f"[INFO] After dedup: {len(unique)}")

    # Merge and save
    merged = merge_with_existing(unique)

    SIGNATURES_DIR.mkdir(exist_ok=True)
    with open(JAILBREAKS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"\n[DONE] Saved {merged['total_patterns']} patterns")
    print(f"Stats: {merged.get('source_stats', {})}")
    print("=" * 60)


if __name__ == "__main__":
    main()
