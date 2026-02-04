#!/usr/bin/env python3
"""
Compile web payloads from PayloadsAllTheThings into SENTINEL CDN format.

Usage:
    python compile_web_payloads.py

Output:
    signatures/web-payloads.json (for CDN upload)
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_URL = "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master"

# Curated payload sources - verified paths from PayloadsAllTheThings
PAYLOAD_SOURCES = {
    "sqli": [
        "SQL%20Injection/Intruder/Auth_Bypass.txt",
        "SQL%20Injection/Intruder/Auth_Bypass2.txt",
        "SQL%20Injection/Intruder/Generic_ErrorBased.txt",
        "SQL%20Injection/Intruder/Generic_TimeBased.txt",
        "SQL%20Injection/Intruder/Generic_UnionSelect.txt",
        "SQL%20Injection/Intruder/Generic_Fuzz.txt",
        "SQL%20Injection/Intruder/SQLi_Polyglots.txt",
        "SQL%20Injection/Intruder/FUZZDB_MSSQL.txt",
        "SQL%20Injection/Intruder/FUZZDB_MYSQL.txt",
        "SQL%20Injection/Intruder/FUZZDB_Oracle.txt",
    ],
    "xss": [
        "XSS%20Injection/Intruders/XSS_Polyglots.txt",
        "XSS%20Injection/Intruders/BRUTELOGIC-XSS-CHEATSHEET.txt",
    ],
    "ssti": [
        "Server%20Side%20Template%20Injection/Intruder/ssti.fuzz",
    ],
    "lfi": [
        "File%20Inclusion/Intruders/Traversal.txt",
    ],
    "cmdi": [
        "Command%20Injection/Intruder/command-execution-unix.txt",
    ],
    "xxe": [
        "XXE%20Injection/Intruders/XXE_Fuzzing.txt",
        "XXE%20Injection/Intruders/xml-attacks.txt",
    ],
    "nosql": [
        "NoSQL%20Injection/Intruder/NoSQL.txt",
        "NoSQL%20Injection/Intruder/MongoDB.txt",
    ],
    "ldap": [
        "LDAP%20Injection/Intruder/LDAP_FUZZ.txt",
    ],
    "open_redirect": [
        "Open%20Redirect/Intruder/Open-Redirect-payloads.txt",
    ],
}


def fetch_payloads(url: str) -> list[str]:
    """Fetch payloads from URL, return list of non-empty lines."""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            lines = [
                line.strip()
                for line in content.splitlines()
                if line.strip() and not line.startswith("#")
            ]
            return lines
    except Exception as e:
        print(f"  ⚠️ Failed: {e}")
        return []


def main():
    print("🔧 Compiling web payloads from PayloadsAllTheThings...")
    print(f"   Source: {BASE_URL}\n")

    all_payloads = {}
    total_count = 0

    for category, paths in PAYLOAD_SOURCES.items():
        print(f"📂 {category.upper()}")
        category_payloads = []

        for path in paths:
            url = f"{BASE_URL}/{path}"
            print(f"   ↓ {path.split('/')[-1][:40]}...")
            payloads = fetch_payloads(url)
            category_payloads.extend(payloads)
            print(f"     ✓ {len(payloads)} payloads")

        # Deduplicate
        unique = list(set(category_payloads))
        all_payloads[category] = unique
        total_count += len(unique)
        print(f"   Total: {len(unique)} unique\n")

    # Create output
    output = {
        "version": datetime.now().strftime("%Y.%m.%d"),
        "source": "PayloadsAllTheThings",
        "source_url": "https://github.com/swisskyrepo/PayloadsAllTheThings",
        "generated_at": datetime.now().isoformat(),
        "total_payloads": total_count,
        "categories": all_payloads,
    }

    # Write to file
    out_path = Path("signatures/web-payloads.json")
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved to {out_path}")
    print(f"   Total payloads: {total_count}")
    print(f"   File size: {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
