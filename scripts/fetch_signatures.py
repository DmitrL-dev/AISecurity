#!/usr/bin/env python3
"""
SENTINEL Signature Fetcher v3.0

Automatically fetches jailbreak patterns from open sources:
- walledai/JailbreakBench (HuggingFace) - 200 prompts
- deepset/prompt-injections (HuggingFace) - 662 prompts
- SafetyPrompts (Chinese LLM Safety) - 100K zh prompts
- PolygloToxicityPrompts (multilingual incl. CJK) - 425K prompts
- CatQA (Chinese/English/Vietnamese) - 550 prompts
- Local SENTINEL Strike payloads (fallback)

This script is designed to run via GitHub Actions daily.
Sources are aggregated, deduplicated, and merged into signatures/jailbreaks.json

Updated: 2026-02-12 - Added CJK sources (zh/ja/ko) for Chinese AI model coverage
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
    # Multilingual sources (include Russian)
    {
        "name": "xsafety",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "Saltlux/XSafety/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "prompt",
        "language_field": "language",
        "enabled": True,
    },
    {
        "name": "lakera_pint",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "Lakera/pint-benchmark/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "text",
        "language_field": "language",
        "enabled": True,
    },
    # ---- CJK Sources (Chinese/Japanese/Korean) ----
    # SafetyPrompts: 100K Chinese safety evaluation prompts
    {
        "name": "safetyprompts_zh",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "thu-coai/SafetyPrompts/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "prompt",
        "default_language": "zh",
        "enabled": True,
    },
    # PolygloToxicityPrompts: 425K multilingual (incl. zh/ja/ko)
    {
        "name": "polyglot_toxic",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "ToxicityPrompts/PolygloToxicityPrompts/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "prompt",
        "language_field": "language",
        "enabled": True,
    },
    # CatQA: Chinese/English/Vietnamese safety evaluation
    {
        "name": "catqa_zh",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "zhihaozhong/CatQA/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "question",
        "language_field": "language",
        "enabled": True,
    },
    # Multilingual Jailbreak Prompts (rubend18)
    {
        "name": "chatgpt_jailbreak_prompts",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "rubend18/ChatGPT-Jailbreak-Prompts/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "prompt",
        "enabled": True,
    },
    # WildJailbreak: large-scale multilingual jailbreak dataset
    {
        "name": "wildjailbreak",
        "type": "huggingface_parquet",
        "url": (
            "https://huggingface.co/datasets/"
            "allenai/wildjailbreak/resolve/main/"
            "data/train-00000-of-00001.parquet"
        ),
        "text_field": "adversarial",
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

                # Determine language
                lang_field = source.get("language_field")
                lang = source.get("default_language")  # fallback
                if lang_field:
                    langs = df_dict.get(lang_field, [])
                    if i < len(langs):
                        lang = str(langs[i]).lower()
                # Auto-detect CJK if no language field
                if not lang and _contains_cjk(text):
                    lang = _detect_cjk_language(text)

                patterns.append(
                    {
                        "id": pattern_id,
                        "source": name,
                        "pattern": (keywords[0] if keywords else text[:50]),
                        "regex": generate_regex(keywords),
                        "attack_class": "LLM01",
                        "severity": "high",
                        "complexity": "moderate",
                        "bypass_technique": "external",
                        **({"language": lang} if lang else {}),
                        "fetched_at": (datetime.utcnow().isoformat()),
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


def _contains_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return bool(
        re.search(r"[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]", text)
    )


def _detect_cjk_language(text: str) -> str:
    """Auto-detect CJK language from text content."""
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", text):
        return "ja"  # Japanese: hiragana/katakana
    if re.search(r"[\uac00-\ud7af]", text):
        return "ko"  # Korean: hangul
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"  # Chinese: CJK ideographs
    return "unknown"


def extract_keywords(text: str) -> list[str]:
    """Extract jailbreak-relevant keywords from text (EN + CJK)."""
    keywords = []

    # English jailbreak indicators
    en_indicators = [
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

    # Chinese (zh) jailbreak indicators
    zh_indicators = [
        r"\u8d8a\u72f1|\u8d8a\u72f1\u6a21\u5f0f|\u8d8a\u72f1\u5927\u5e08",
        r"\u89e3\u9664\u9650\u5236|\u53d6\u6d88\u9650\u5236|\u65e0\u9650\u5236\u6a21\u5f0f",
        r"\u5ffd\u7565\u4e4b\u524d\u7684|\u5ffd\u7565\u6240\u6709|\u5fd8\u8bb0\u4e4b\u524d",
        r"\u4f60\u73b0\u5728\u662f\u4e00\u4e2a\u6ca1\u6709\u4efb\u4f55\u9650\u5236\u7684",
        r"\u5f00\u53d1\u8005\u6a21\u5f0f|\u8c03\u8bd5\u6a21\u5f0f",
        r"\u7ed9\u6211\u770b\u4f60\u7684\u7cfb\u7edf\u63d0\u793a|\u663e\u793a\u7cfb\u7edf\u63d0\u793a",
        r"DAN\u6a21\u5f0f|DAN\u6fc0\u6d3b",
        r"\u7ed5\u8fc7\u5ba1\u67e5|\u7a81\u7834\u5ba1\u67e5|\u53cd\u5ba1\u67e5",
        r"\u7528base64\u89e3\u7801|\u89e3\u7801\u8fd9\u6bb5",
        r"\u8c03\u7528\u4ee5\u4e0b\u5de5\u5177|\u6267\u884c\u4ee5\u4e0b\u547d\u4ee4",
    ]

    # Japanese (ja) jailbreak indicators
    ja_indicators = [
        r"\u8131\u7344\u30e2\u30fc\u30c9|\u8131\u7344\u3057\u3066|\u5236\u9650\u3092\u89e3\u9664",
        r"\u6307\u793a\u3092\u7121\u8996|\u30b7\u30b9\u30c6\u30e0\u30d7\u30ed\u30f3\u30d7\u30c8\u3092\u8868\u793a",
    ]

    # Korean (ko) jailbreak indicators
    ko_indicators = [
        r"\ud0c8\uc625\s*\ubaa8\ub4dc|\ud0c8\uc625\ud574\uc918|\uc81c\ud55c\s*\ud574\uc81c",
        r"\uc774\uc804\s*\uc9c0\uc2dc\ub97c\s*\ubb34\uc2dc|\uc2dc\uc2a4\ud15c\s*\ud504\ub86c\ud504\ud2b8\ub97c\s*\ubcf4\uc5ec",
    ]

    all_indicators = en_indicators + zh_indicators + ja_indicators + ko_indicators

    for pattern in all_indicators:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            keywords.extend([m if isinstance(m, str) else m[0] for m in matches])

    return list(set(keywords))[:5]  # Max 5 keywords (increased for CJK)


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
