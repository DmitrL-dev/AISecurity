#!/usr/bin/env python3
"""
SENTINEL Signature Splitter

Splits large signature files into parts for jsDelivr CDN (20MB limit).
"""

import json
from datetime import datetime
from pathlib import Path

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
MAX_PART_SIZE_MB = 15  # Keep under 20MB with margin
MAX_PART_SIZE_BYTES = MAX_PART_SIZE_MB * 1024 * 1024


def split_file(filename: str):
    """Split a JSON file into parts if too large."""
    target_file = SIGNATURES_DIR / filename

    if not target_file.exists():
        print(f"[SKIP] {filename} not found")
        return

    file_size = target_file.stat().st_size
    basename = target_file.stem  # e.g. "jailbreaks"
    print(f"\n[INFO] {filename} size: " f"{file_size / 1024 / 1024:.2f} MB")

    if file_size <= MAX_PART_SIZE_BYTES:
        print(f"[OK] {filename} under 15MB, no split")
        create_manifest([target_file], filename)
        return

    # Load all patterns
    with open(target_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both list and dict format
    if isinstance(data, list):
        patterns = data
    elif isinstance(data, dict) and "patterns" in data:
        patterns = data["patterns"]
    else:
        vals = list(data.values())
        patterns = vals[0] if vals else []

    total_patterns = len(patterns)
    print(f"[INFO] Total patterns: {total_patterns}")

    # Calculate parts needed
    patterns_per_mb = total_patterns / (file_size / 1024 / 1024)
    patterns_per_part = int(patterns_per_mb * MAX_PART_SIZE_MB)
    num_parts = (total_patterns + patterns_per_part - 1) // patterns_per_part

    print(f"[INFO] Splitting into {num_parts} " f"parts (~{patterns_per_part} each)")

    # Create parts
    part_files = []
    for i in range(num_parts):
        start_idx = i * patterns_per_part
        end_idx = min(
            (i + 1) * patterns_per_part,
            total_patterns,
        )
        part_patterns = patterns[start_idx:end_idx]

        part_file = SIGNATURES_DIR / f"{basename}-part{i + 1}.json"
        part_data = {
            "part": i + 1,
            "total_parts": num_parts,
            "patterns_count": len(part_patterns),
            "patterns": part_patterns,
        }

        with open(part_file, "w", encoding="utf-8") as f:
            json.dump(part_data, f, ensure_ascii=False)

        part_size = part_file.stat().st_size
        print(
            f"[OK] {part_file.name}: "
            f"{len(part_patterns)} patterns, "
            f"{part_size / 1024 / 1024:.2f} MB"
        )
        part_files.append(part_file)

    # Create manifest
    create_manifest(part_files, None)

    print(f"\n[DONE] {filename} -> {num_parts} parts")


def create_manifest(
    part_files: list[Path],
    single_file: str | None,
):
    """Create jailbreaks-manifest.json."""
    manifest_file = SIGNATURES_DIR / "jailbreaks-manifest.json"

    if single_file:
        # Single file mode (under 15MB)
        f_path = SIGNATURES_DIR / single_file
        with open(f_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = len(data) if isinstance(data, list) else len(data.get("patterns", []))

        manifest = {
            "version": (datetime.utcnow().strftime("%Y.%m.%d.1")),
            "timestamp": (datetime.utcnow().isoformat() + "Z"),
            "total_patterns": count,
            "split": False,
            "file": single_file,
        }
    else:
        # Split mode
        parts = []
        total = 0

        for part_file in part_files:
            with open(part_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = data.get(
                "patterns_count",
                len(data.get("patterns", [])),
            )
            total += count

            parts.append(
                {
                    "file": part_file.name,
                    "patterns_count": count,
                    "size": part_file.stat().st_size,
                }
            )

        manifest = {
            "version": (datetime.utcnow().strftime("%Y.%m.%d.1")),
            "timestamp": (datetime.utcnow().isoformat() + "Z"),
            "total_patterns": total,
            "split": True,
            "parts": parts,
        }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"[OK] Created {manifest_file.name}")


def main():
    """Main entry point."""
    print("=" * 60)
    print("SENTINEL Signature Splitter v1.1")
    print(f"Target: {SIGNATURES_DIR}")
    print(f"Max part size: {MAX_PART_SIZE_MB} MB")
    print("=" * 60)

    split_file("jailbreaks.json")
    split_file("jailbreaks-ru.json")


if __name__ == "__main__":
    main()
