#!/usr/bin/env python3
"""
SENTINEL Signature Fetcher v2.0

Automatically fetches jailbreak patterns from open sources:
- walledai/JailbreakBench (HuggingFace) - 200 prompts
- deepset/prompt-injections (HuggingFace) - 662 prompts
- Local SENTINEL Strike payloads (fallback)

This script is designed to run via GitHub Actions daily.
Sources are aggregated, deduplicated, and merged into signatures/jailbreaks.json

Updated: 2026-01-23 - Fixed dead GitHub sources, switched to HuggingFace
"""

import json
import hashlib
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Configuration - FIXED PATH BUG
SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
JAILBREAKS_FILE = SIGNATURES_DIR / "jailbreaks.json"

# HuggingFace dataset URLs (parquet format) + GitHub live sources
# All sources verified 2026-01-23
SOURCES = [
    # HuggingFace datasets (verified working)
    {
        "name": "jailbreakbench",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/walledai/JailbreakBench/"
            "resolve/main/data/train-00000-of-00001.parquet"
        ),
        "text_field": "prompt",
        "enabled": True,
    },
    {
        "name": "deepset_injections",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/deepset/prompt-injections/"
            "resolve/main/data/train-00000-of-00001-9564e8b05b4757ab.parquet"
        ),
        "text_field": "text",
        "label_field": "label",  # 1 = injection
        "enabled": True,
    },
    # GitHub live sources (verified working)
    {
        "name": "llm_attacks_advbench",
        "type": "github_csv",
        "url": (
            "https://raw.githubusercontent.com/llm-attacks/llm-attacks/"
            "main/data/advbench/harmful_behaviors.csv"
        ),
        "enabled": True,
    },
    {
        "name": "garak_dan",
        "type": "github_python",
        "url": (
            "https://raw.githubusercontent.com/NVIDIA/garak/" "main/garak/probes/dan.py"
        ),
        "enabled": True,
    },
    {
        "name": "garak_promptinject",
        "type": "github_python",
        "url": (
            "https://raw.githubusercontent.com/NVIDIA/garak/"
            "main/garak/probes/promptinject.py"
        ),
        "enabled": True,
    },
]


def fetch_huggingface_parquet(source: dict) -> list[dict]:
    """Fetch jailbreaks from HuggingFace parquet dataset."""
    patterns = []
    name = source["name"]

    try:
        # Download parquet file
        response = requests.get(source["url"], timeout=60)

        if response.status_code != 200:
            print(f"[WARN] {name}: HTTP {response.status_code}")
            return patterns

        # Try to parse parquet (requires pyarrow)
        try:
            import pyarrow.parquet as pq
            import io

            table = pq.read_table(io.BytesIO(response.content))
            df_dict = table.to_pydict()

            text_field = source.get("text_field", "text")
            label_field = source.get("label_field")

            texts = df_dict.get(text_field, [])
            labels = (
                df_dict.get(label_field, [None] * len(texts))
                if label_field
                else [1] * len(texts)
            )

            for i, (text, label) in enumerate(zip(texts, labels)):
                # For deepset, label=1 means injection
                if label_field and label != 1:
                    continue

                if not text or len(text) < 20:
                    continue

                keywords = extract_keywords(text)
                if not keywords:
                    continue

                pattern_id = (
                    f"ext_{name}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
                )

                patterns.append(
                    {
                        "id": pattern_id,
                        "source": name,
                        "pattern": keywords[0] if keywords else text[:50],
                        "regex": generate_regex(keywords),
                        "attack_class": "LLM01",
                        "severity": "high",
                        "complexity": "moderate",
                        "bypass_technique": "external",
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
                )

        except ImportError:
            print(f"[WARN] pyarrow not installed, skipping {name}")
            return patterns

    except Exception as e:
        print(f"[ERROR] {name} fetch failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from {name}")
    return patterns


def fetch_github_csv(source: dict) -> list[dict]:
    """Fetch jailbreaks from GitHub CSV file (llm-attacks/advbench)."""
    patterns = []
    name = source["name"]

    try:
        response = requests.get(source["url"], timeout=30)
        if response.status_code != 200:
            print(f"[WARN] {name}: HTTP {response.status_code}")
            return patterns

        lines = response.text.strip().split("\n")[1:]  # Skip header
        for line in lines[:100]:  # Limit
            parts = line.split(",", 1)
            if len(parts) < 2:
                continue
            text = parts[0].strip().strip('"')
            if len(text) < 20:
                continue

            keywords = extract_keywords(text)
            if not keywords:
                continue

            pid = f"ext_{name}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
            patterns.append(
                {
                    "id": pid,
                    "source": name,
                    "pattern": keywords[0],
                    "regex": generate_regex(keywords),
                    "attack_class": "LLM01",
                    "severity": "high",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            )

    except Exception as e:
        print(f"[ERROR] {name} fetch failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from {name}")
    return patterns


def fetch_github_python(source: dict) -> list[dict]:
    """Fetch jailbreaks from garak probe Python files (extract prompts)."""
    patterns = []
    name = source["name"]

    try:
        response = requests.get(source["url"], timeout=30)
        if response.status_code != 200:
            print(f"[WARN] {name}: HTTP {response.status_code}")
            return patterns

        content = response.text
        # Extract string literals that look like prompts
        prompt_patterns = re.findall(r'["\']([^"\']{50,500})["\']', content)

        for text in prompt_patterns[:50]:
            keywords = extract_keywords(text)
            if not keywords:
                continue

            pid = f"ext_{name}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"
            patterns.append(
                {
                    "id": pid,
                    "source": name,
                    "pattern": keywords[0],
                    "regex": generate_regex(keywords),
                    "attack_class": "LLM01",
                    "severity": "high",
                    "fetched_at": datetime.utcnow().isoformat(),
                }
            )

    except Exception as e:
        print(f"[ERROR] {name} fetch failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from {name}")
    return patterns


def fetch_local_strike() -> list[dict]:
    """Fallback: fetch from local SENTINEL Strike payloads."""
    patterns = []
    strike_dir = Path(__file__).parent.parent / "strike" / "payloads"

    if not strike_dir.exists():
        print("[INFO] Strike payloads not found, skipping fallback")
        return patterns

    try:
        for payload_file in strike_dir.glob("*.json"):
            try:
                with open(payload_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                items = data if isinstance(data, list) else data.get("payloads", [])

                for item in items[:50]:  # Limit per file
                    text = (
                        item.get("prompt")
                        or item.get("payload")
                        or item.get("text", "")
                    )
                    if len(text) < 20:
                        continue

                    keywords = extract_keywords(text)
                    if not keywords:
                        continue

                    pattern_id = f"strike_{payload_file.stem}_{hashlib.md5(text[:100].encode()).hexdigest()[:8]}"

                    patterns.append(
                        {
                            "id": pattern_id,
                            "source": f"strike/{payload_file.stem}",
                            "pattern": keywords[0],
                            "regex": generate_regex(keywords),
                            "attack_class": item.get("attack_class", "LLM01"),
                            "severity": item.get("severity", "high"),
                            "complexity": "moderate",
                            "bypass_technique": "internal",
                            "fetched_at": datetime.utcnow().isoformat(),
                        }
                    )

            except Exception as e:
                print(f"[WARN] Error reading {payload_file.name}: {e}")
                continue

    except Exception as e:
        print(f"[ERROR] Strike fallback failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from Strike fallback")
    return patterns


def extract_keywords(text: str) -> list[str]:
    """Extract jailbreak-relevant keywords from text."""
    keywords = []

    # Common jailbreak indicators
    indicators = [
        r"ignore\s+(all\s+)?previous\s+instructions?",
        r"you\s+are\s+now\s+\w+",
        r"(DAN|STAN|DUDE|AIM)\s+mode",
        r"developer\s+mode",
        r"jailbreak\s+mode",
        r"pretend\s+to\s+be",
        r"act\s+as\s+if",
        r"from\s+now\s+on",
        r"forget\s+(everything|all)",
        r"no\s+(restrictions?|limits?|rules?)",
        r"bypass\s+(security|safety|filters?)",
        r"reveal\s+(your\s+)?(system\s+)?prompt",
        r"disregard\s+(all|any|your)",
        r"override\s+(your|all)",
        r"new\s+persona",
        r"roleplay\s+as",
    ]

    for pattern in indicators:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            keywords.extend([m if isinstance(m, str) else m[0] for m in matches])

    return list(set(keywords))[:3]  # Max 3 keywords


def generate_regex(keywords: list[str]) -> Optional[str]:
    """Generate regex pattern from keywords."""
    if not keywords:
        return None

    # Escape special chars and join with OR
    escaped = [re.escape(kw) for kw in keywords]
    return f"(?i)({'|'.join(escaped)})"


def deduplicate_patterns(patterns: list[dict]) -> list[dict]:
    """Remove duplicate patterns based on regex."""
    seen_regexes = set()
    unique = []

    for p in patterns:
        regex = p.get("regex", "")
        if regex and regex not in seen_regexes:
            seen_regexes.add(regex)
            unique.append(p)

    return unique


def merge_with_existing(new_patterns: list[dict]) -> dict:
    """Merge new patterns with existing jailbreaks.json."""

    # Load existing
    if JAILBREAKS_FILE.exists():
        with open(JAILBREAKS_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
    else:
        existing = {"patterns": [], "version": "0.0.0"}

    # Handle both list and dict format
    if isinstance(existing, list):
        existing = {"patterns": existing, "version": "0.0.0"}

    # Get existing IDs
    existing_ids = {p.get("id", "") for p in existing.get("patterns", [])}

    # Add new patterns that don't exist
    added = 0
    for p in new_patterns:
        if p["id"] not in existing_ids:
            existing["patterns"].append(p)
            added += 1

    # Update metadata
    existing["last_updated"] = datetime.utcnow().isoformat() + "Z"
    existing["total_patterns"] = len(existing["patterns"])

    # Update version (date-based)
    existing["version"] = datetime.utcnow().strftime("%Y.%m.%d.1")

    print(f"[INFO] Added {added} new patterns, total: {existing['total_patterns']}")

    return existing


def main():
    """Main entry point."""
    print("=" * 60)
    print("SENTINEL Signature Fetcher v2.0")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    all_patterns = []

    # Fetch from all enabled sources
    for source in SOURCES:
        if not source.get("enabled"):
            continue
        stype = source["type"]
        if stype == "huggingface_parquet":
            all_patterns.extend(fetch_huggingface_parquet(source))
        elif stype == "github_csv":
            all_patterns.extend(fetch_github_csv(source))
        elif stype == "github_python":
            all_patterns.extend(fetch_github_python(source))

    # Fallback to local Strike payloads
    if len(all_patterns) < 10:
        print("[INFO] Few external patterns, using Strike fallback")
        all_patterns.extend(fetch_local_strike())

    # Deduplicate
    unique_patterns = deduplicate_patterns(all_patterns)
    print(f"[INFO] {len(unique_patterns)} unique patterns after deduplication")

    # Merge with existing
    merged = merge_with_existing(unique_patterns)

    # Save
    SIGNATURES_DIR.mkdir(parents=True, exist_ok=True)
    with open(JAILBREAKS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Saved to {JAILBREAKS_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
