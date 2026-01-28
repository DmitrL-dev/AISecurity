#!/usr/bin/env python3
"""
Fix Mojibake encoding in Academy files.
Mojibake: UTF-8 text incorrectly decoded as CP1251, then re-encoded as UTF-8.
Solution: Decode as UTF-8, encode as CP1251 (latin1), decode as UTF-8.
"""

import os
import sys
from pathlib import Path


def is_mojibake(text: str) -> bool:
    """Check if text contains Mojibake patterns."""
    # Common Mojibake patterns for Russian UTF-8 misinterpreted as CP1251
    # These are sequences that appear when UTF-8 Russian is read as CP1251
    mojibake_indicators = [
        "\u0420\u0430",  # "Ра" - common Mojibake start
        "\u0420\u0431",  # "Рб"
        "\u0420\u0435",  # "Ре"
        "\u0420\u043e",  # "Ро"
        "\u0421\u0402",  # "С‚"
        "\u0421\u0403",  # "Сѓ"
        "\u0421\u0404",  # special
        'вЂ"',  # em-dash mojibake
        "вЂ™",  # apostrophe mojibake
        "вЂў",  # bullet mojibake
    ]
    return any(pattern in text for pattern in mojibake_indicators)


def fix_mojibake(text: str) -> str:
    """Fix Mojibake by reversing the double encoding."""
    try:
        # The text was UTF-8, read as CP1251, then saved as UTF-8
        # To reverse: encode as CP1251, decode as UTF-8
        fixed = text.encode("cp1251").decode("utf-8")
        return fixed
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Try alternative: encode as latin1
        try:
            fixed = text.encode("latin1").decode("utf-8")
            return fixed
        except:
            return text  # Return original if can't fix


def check_file(filepath: Path) -> tuple:
    """Check if file has Mojibake and return status."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if is_mojibake(content):
            return True, "CORRUPTED"
        elif any(ord(c) > 127 for c in content):
            # Has non-ASCII but not Mojibake - likely correct Russian
            return False, "OK (has cyrillic)"
        else:
            return False, "OK (ascii only)"
    except Exception as e:
        return False, f"ERROR: {e}"


def fix_file(filepath: Path, dry_run: bool = False) -> bool:
    """Fix Mojibake in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not is_mojibake(content):
            return False

        fixed = fix_mojibake(content)

        if dry_run:
            print(f"Would fix: {filepath}")
            print(f"  Before: {content[:100]}...")
            print(f"  After:  {fixed[:100]}...")
        else:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(fixed)
            print(f"Fixed: {filepath}")

        return True
    except Exception as e:
        print(f"Error fixing {filepath}: {e}")
        return False


def scan_directory(directory: Path, extensions=None) -> dict:
    """Scan directory for files and check their status."""
    if extensions is None:
        extensions = [".md"]
    results = {"corrupted": [], "ok": [], "error": []}

    for ext in extensions:
        for filepath in directory.rglob(f"*{ext}"):
            is_bad, status = check_file(filepath)
            if is_bad:
                results["corrupted"].append(filepath)
            elif "ERROR" in status:
                results["error"].append((filepath, status))
            else:
                results["ok"].append(filepath)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Fix Mojibake encoding in files")
    parser.add_argument("path", help="File or directory to process")
    parser.add_argument(
        "--fix", action="store_true", help="Actually fix files (default: dry run)"
    )
    parser.add_argument("--scan", action="store_true", help="Only scan and report")
    args = parser.parse_args()

    path = Path(args.path)

    if args.scan:
        if path.is_dir():
            results = scan_directory(path)
            print(f"\n=== SCAN RESULTS ===")
            print(f"Corrupted: {len(results['corrupted'])}")
            print(f"OK: {len(results['ok'])}")
            print(f"Errors: {len(results['error'])}")

            if results["corrupted"]:
                print(f"\nCorrupted files:")
                for f in results["corrupted"]:
                    print(f"  - {f}")
        else:
            is_bad, status = check_file(path)
            print(f"{path}: {status}")
    else:
        if path.is_file():
            fix_file(path, dry_run=not args.fix)
        else:
            results = scan_directory(path)
            for filepath in results["corrupted"]:
                fix_file(filepath, dry_run=not args.fix)

            print(
                f"\n{'Fixed' if args.fix else 'Would fix'}: {len(results['corrupted'])} files"
            )


if __name__ == "__main__":
    main()
