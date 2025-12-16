#!/usr/bin/env python3
"""
Split jailbreaks.json into multiple parts for jsDelivr CDN (20MB limit)
"""
import json
import os
from pathlib import Path

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
INPUT_FILE = SIGNATURES_DIR / "jailbreaks.json"
MAX_SIZE_MB = 15  # Target size per file (keep under 20MB limit with margin)


def split_jailbreaks():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patterns = data.get("patterns", [])
    total_patterns = len(patterns)
    print(f"Total patterns: {total_patterns}")

    # Calculate how many parts we need
    file_size_mb = os.path.getsize(INPUT_FILE) / (1024 * 1024)
    num_parts = int(file_size_mb / MAX_SIZE_MB) + 1
    patterns_per_part = total_patterns // num_parts + 1

    print(f"File size: {file_size_mb:.1f}MB")
    print(
        f"Splitting into {num_parts} parts (~{patterns_per_part} patterns each)")

    # Create manifest for parts
    manifest = {
        "version": data.get("version", "2025.12.15"),
        "source": data.get("source", "sentinel-enterprise"),
        "last_updated": data.get("last_updated"),
        "total_patterns": total_patterns,
        "categories": data.get("categories", {}),
        "parts": []
    }

    # Split patterns into parts
    for i in range(num_parts):
        start_idx = i * patterns_per_part
        end_idx = min((i + 1) * patterns_per_part, total_patterns)

        part_patterns = patterns[start_idx:end_idx]
        part_filename = f"jailbreaks-part{i+1}.json"

        part_data = {
            "part": i + 1,
            "total_parts": num_parts,
            "patterns_in_part": len(part_patterns),
            "patterns": part_patterns
        }

        output_path = SIGNATURES_DIR / part_filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(part_data, f, ensure_ascii=False, indent=2)

        part_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(
            f"  Created {part_filename}: {len(part_patterns)} patterns, {part_size_mb:.1f}MB")

        manifest["parts"].append({
            "file": part_filename,
            "patterns_count": len(part_patterns),
            "size_mb": round(part_size_mb, 1)
        })

    # Save manifest
    manifest_path = SIGNATURES_DIR / "jailbreaks-manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Created {manifest_path.name}")

    print("\nDone! Files ready for CDN upload.")
    print("Update agent.rs to load from manifest + parts")


if __name__ == "__main__":
    split_jailbreaks()
