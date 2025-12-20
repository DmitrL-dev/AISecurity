#!/usr/bin/env python3
"""
SENTINEL Signature Fetcher

Automatically fetches jailbreak patterns from open sources:
- jailbreakchat/jailbreaks (GitHub)
- verazuo/jailbreak_llms (GitHub)
- HuggingFace datasets

This script is designed to run via GitHub Actions daily.

Sources are aggregated, deduplicated, and merged into signatures/jailbreaks.json
"""

import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# Configuration
SIGNATURES_DIR = Path(__file__).parent.parent / "sentinel-community" / "signatures"
JAILBREAKS_FILE = SIGNATURES_DIR / "jailbreaks.json"

# External sources to fetch
SOURCES = [
    {
        "name": "jailbreakchat",
        "type": "github_dir",
        "url": "https://api.github.com/repos/jailbreakchat/jailbreaks/contents/jailbreaks",
        "enabled": True,
    },
    {
        "name": "verazuo",
        "type": "github_file",
        "url": "https://raw.githubusercontent.com/verazuo/jailbreak_llms/main/data/jailbreak_prompts.csv",
        "enabled": True,
    },
    # Add more sources as needed
]


def fetch_jailbreakchat() -> list[dict]:
    """Fetch jailbreaks from jailbreakchat/jailbreaks repo."""
    patterns = []

    try:
        # Get directory listing
        response = requests.get(
            SOURCES[0]["url"],
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=30,
        )

        if response.status_code != 200:
            print(f"[WARN] jailbreakchat: HTTP {response.status_code}")
            return patterns

        files = response.json()

        for file_info in files[:20]:  # Limit to 20 files
            if not file_info.get("download_url"):
                continue

            try:
                content_resp = requests.get(file_info["download_url"], timeout=10)
                content = content_resp.text.strip()

                if len(content) > 50:  # Minimum content length
                    pattern_id = f"ext_jailbreakchat_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}"

                    # Extract key phrases for pattern matching
                    keywords = extract_keywords(content)

                    if keywords:
                        patterns.append(
                            {
                                "id": pattern_id,
                                "source": "jailbreakchat",
                                "pattern": keywords[0] if keywords else content[:50],
                                "regex": generate_regex(keywords),
                                "attack_class": "LLM01",
                                "severity": "high",
                                "complexity": "moderate",
                                "bypass_technique": "external",
                                "fetched_at": datetime.utcnow().isoformat(),
                            }
                        )

            except Exception as e:
                print(f"[WARN] Error fetching {file_info.get('name', 'unknown')}: {e}")
                continue

    except Exception as e:
        print(f"[ERROR] jailbreakchat fetch failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from jailbreakchat")
    return patterns


def fetch_verazuo() -> list[dict]:
    """Fetch jailbreaks from verazuo/jailbreak_llms dataset."""
    patterns = []

    try:
        response = requests.get(SOURCES[1]["url"], timeout=30)

        if response.status_code != 200:
            print(f"[WARN] verazuo: HTTP {response.status_code}")
            return patterns

        lines = response.text.strip().split("\n")[1:]  # Skip header

        for i, line in enumerate(lines[:50]):  # Limit to 50 entries
            try:
                # CSV format: prompt,category,source
                parts = line.split(",", 2)
                if len(parts) >= 1:
                    prompt = parts[0].strip().strip('"')

                    if len(prompt) > 20:
                        pattern_id = f"ext_verazuo_{hashlib.md5(prompt[:100].encode()).hexdigest()[:8]}"
                        keywords = extract_keywords(prompt)

                        if keywords:
                            patterns.append(
                                {
                                    "id": pattern_id,
                                    "source": "verazuo",
                                    "pattern": keywords[0] if keywords else prompt[:50],
                                    "regex": generate_regex(keywords),
                                    "attack_class": "LLM01",
                                    "severity": "high",
                                    "complexity": "moderate",
                                    "bypass_technique": "external",
                                    "fetched_at": datetime.utcnow().isoformat(),
                                }
                            )

            except Exception as e:
                print(f"[WARN] Error parsing line {i}: {e}")
                continue

    except Exception as e:
        print(f"[ERROR] verazuo fetch failed: {e}")

    print(f"[INFO] Fetched {len(patterns)} patterns from verazuo")
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

    # Get existing IDs
    existing_ids = {p["id"] for p in existing.get("patterns", [])}

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
    print("SENTINEL Signature Fetcher")
    print(f"Time: {datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    all_patterns = []

    # Fetch from each source
    if SOURCES[0]["enabled"]:
        all_patterns.extend(fetch_jailbreakchat())

    if SOURCES[1]["enabled"]:
        all_patterns.extend(fetch_verazuo())

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
