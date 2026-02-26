#!/usr/bin/env python3
"""
Deep fix for Academy encoding issues.
Handles files that aren't valid UTF-8 at all.
"""

import os
from pathlib import Path


def fix_file_deep(filepath: Path) -> str:
    """Try multiple encodings to fix a file."""
    encodings_to_try = ["utf-8", "cp1251", "latin1", "utf-16"]

    for enc in encodings_to_try:
        try:
            with open(filepath, "r", encoding=enc) as f:
                content = f.read()

            # Check if content looks reasonable (has some ASCII)
            if content and any(c.isalpha() for c in content[:100]):
                # Try to detect and fix mojibake
                try:
                    # Common mojibake pattern: UTF-8 read as CP1251
                    fixed = content.encode("cp1251").decode("utf-8")
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    return f"FIXED (mojibake from {enc})"
                except:
                    # Just re-save as UTF-8
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(content)
                    return f"FIXED (converted from {enc})"
        except:
            continue

    return "FAILED - could not read with any encoding"


def main():
    import sys

    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/academy/ru")

    fixed = 0
    failed = 0

    for filepath in directory.rglob("*.md"):
        # Try to read as UTF-8 first
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            # Check for mojibake
            mojibake_indicators = [
                "\u0420\u0430",
                "\u0420\u0431",
                "\u0420\u0435",
                "\u0421\u0402",
                "\u0421\u0403",
                'вЂ"',
                "вЂ™",
            ]
            if any(p in content for p in mojibake_indicators):
                result = fix_file_deep(filepath)
                print(f"{filepath}: {result}")
                if "FIXED" in result:
                    fixed += 1
                else:
                    failed += 1
        except UnicodeDecodeError:
            # File is not valid UTF-8
            result = fix_file_deep(filepath)
            print(f"{filepath}: {result}")
            if "FIXED" in result:
                fixed += 1
            else:
                failed += 1

    print(f"\n=== RESULTS ===")
    print(f"Fixed: {fixed}")
    print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
