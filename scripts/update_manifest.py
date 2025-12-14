#!/usr/bin/env python3
"""
SENTINEL Manifest Updater

Updates manifest.json with:
- Current version (date-based)
- SHA256 hashes of signature files
- File sizes and counts
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

SIGNATURES_DIR = Path(__file__).parent.parent / "signatures"
MANIFEST_FILE = SIGNATURES_DIR / "manifest.json"


def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def count_items(filepath: Path, key: str) -> int:
    """Count items in a JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return len(data.get(key, []))
    except:
        return 0


def main():
    """Main entry point."""
    print("=" * 60)
    print("SENTINEL Manifest Updater")
    print("=" * 60)
    
    # Load existing manifest
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"files": {}}
    
    # Update version
    manifest["version"] = datetime.utcnow().strftime("%Y.%m.%d.1")
    manifest["timestamp"] = datetime.utcnow().isoformat() + "Z"
    
    # Update file info
    files_info = {
        "jailbreaks": ("jailbreaks.json", "patterns"),
        "keywords": ("keywords.json", "keyword_sets"),
        "pii": ("pii.json", "patterns"),
    }
    
    for name, (filename, count_key) in files_info.items():
        filepath = SIGNATURES_DIR / filename
        if filepath.exists():
            manifest["files"][name] = {
                "path": filename,
                "sha256": calculate_sha256(filepath),
                "size": filepath.stat().st_size,
                "count": count_items(filepath, count_key)
            }
            print(f"[INFO] {filename}: {manifest['files'][name]['count']} items, {manifest['files'][name]['size']} bytes")
    
    # Save manifest
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("=" * 60)
    print(f"[OK] Manifest updated: v{manifest['version']}")


if __name__ == "__main__":
    main()
