#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Payload Database Loader

Downloads and integrates major public payload databases:
- SecLists (50,000+ payloads)
- PayloadsAllTheThings (10,000+)
- FuzzDB (5,000+)
- Additional community sources

Provides unified interface to ALL known attack vectors.
"""

import asyncio
import aiohttp
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime


# ============================================================================
# DATABASE SOURCES
# ============================================================================

PAYLOAD_SOURCES = {
    # SecLists - the gold standard
    "seclists_sqli": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Generic-SQLi.txt",
        "category": "sqli",
        "name": "SecLists Generic SQLi",
    },
    "seclists_sqli_time": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/quick-SQLi.txt",
        "category": "sqli",
        "name": "SecLists Quick SQLi",
    },
    "seclists_xss": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS/XSS-Jhaddix.txt",
        "category": "xss",
        "name": "SecLists XSS Jhaddix (7000+)",
    },
    "seclists_xss_polyglot": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS-Fuzzing",
        "category": "xss",
        "name": "SecLists XSS Fuzzing",
    },
    "seclists_lfi": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-Jhaddix.txt",
        "category": "lfi",
        "name": "SecLists LFI Jhaddix",
    },
    "seclists_lfi_linux": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-gracefulsecurity-linux.txt",
        "category": "lfi",
        "name": "SecLists LFI Linux",
    },
    "seclists_lfi_windows": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-gracefulsecurity-windows.txt",
        "category": "lfi",
        "name": "SecLists LFI Windows",
    },
    "seclists_ssrf": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SSRF/SSRF.txt",
        "category": "ssrf",
        "name": "SecLists SSRF",
    },
    "seclists_xxe": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XXE-Fuzzing.txt",
        "category": "xxe",
        "name": "SecLists XXE",
    },
    "seclists_ssti": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/template-engines-expression.txt",
        "category": "ssti",
        "name": "SecLists SSTI",
    },
    "seclists_cmdi": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/command-injection-commix.txt",
        "category": "cmdi",
        "name": "SecLists Command Injection",
    },
    "seclists_nosql": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/Databases/NoSQL.txt",
        "category": "nosql",
        "name": "SecLists NoSQL",
    },
    "seclists_ldap": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LDAP-Injection.txt",
        "category": "ldap",
        "name": "SecLists LDAP",
    },

    # Passwords (top lists)
    "seclists_passwords_top1000": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-1000.txt",
        "category": "passwords",
        "name": "Top 1000 Passwords",
    },
    "seclists_passwords_top10000": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10-million-password-list-top-10000.txt",
        "category": "passwords",
        "name": "Top 10000 Passwords",
    },
    "seclists_usernames": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/Names/names.txt",
        "category": "usernames",
        "name": "Common Usernames",
    },

    # Discovery
    "seclists_dirs_common": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt",
        "category": "discovery",
        "name": "Common Directories",
    },
    "seclists_dirs_big": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/directory-list-2.3-medium.txt",
        "category": "discovery",
        "name": "Directory List Medium",
    },
    "seclists_api_endpoints": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints.txt",
        "category": "api_discovery",
        "name": "API Endpoints",
    },
    "seclists_graphql": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/graphql.txt",
        "category": "graphql",
        "name": "GraphQL Endpoints",
    },

    # PayloadsAllTheThings
    "patt_sqli": {
        "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/Auth_Bypass.txt",
        "category": "sqli",
        "name": "PATT SQLi Auth Bypass",
    },
    "patt_xss": {
        "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/XSS%20Injection/Intruders/IntrudersXSS.txt",
        "category": "xss",
        "name": "PATT XSS Intruder",
    },
    "patt_xxe": {
        "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/XXE%20Injection/Intruders/xxe-injection-payloads.txt",
        "category": "xxe",
        "name": "PATT XXE",
    },
    "patt_ssti": {
        "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/Server%20Side%20Template%20Injection/Intruder/ssti.txt",
        "category": "ssti",
        "name": "PATT SSTI",
    },

    # FuzzDB alternatives
    "fuzzdb_xss": {
        "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/xss/xss-rsnake.txt",
        "category": "xss",
        "name": "FuzzDB XSS RSnake",
    },

    # Jailbreaks (AI-specific)
    "jailbreaks_dan": {
        "url": "https://raw.githubusercontent.com/0xk1h0/ChatGPT_DAN/main/README.md",
        "category": "jailbreak",
        "name": "DAN Jailbreaks",
        "parser": "markdown",
    },
}

# Additional large wordlists
WORDLIST_SOURCES = {
    "rockyou_sample": {
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou-75.txt",
        "category": "passwords",
        "name": "RockYou Sample (75)",
    },
}


# ============================================================================
# PAYLOAD DATABASE
# ============================================================================

@dataclass
class PayloadDB:
    """Payload database with lazy loading."""

    cache_dir: Path
    sources: Dict = None
    loaded: Dict[str, List[str]] = None
    stats: Dict[str, int] = None

    def __post_init__(self):
        self.cache_dir = Path(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sources = PAYLOAD_SOURCES.copy()
        self.loaded = {}
        self.stats = {}

    async def download_source(self, source_id: str, session: aiohttp.ClientSession) -> List[str]:
        """Download a single source."""
        source = self.sources.get(source_id)
        if not source:
            return []

        cache_file = self.cache_dir / f"{source_id}.txt"

        # Check cache
        if cache_file.exists():
            content = cache_file.read_text(encoding="utf-8", errors="ignore")
            payloads = [line.strip()
                        for line in content.split("\n") if line.strip()]
            return payloads

        # Download
        try:
            async with session.get(source["url"], timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.text()

                    # Parse based on format
                    if source.get("parser") == "markdown":
                        # Extract code blocks from markdown
                        import re
                        payloads = re.findall(
                            r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                        payloads = [p.strip() for block in payloads for p in block.split(
                            '\n') if p.strip()]
                    else:
                        payloads = [line.strip() for line in content.split(
                            "\n") if line.strip() and not line.startswith("#")]

                    # Cache
                    cache_file.write_text(
                        "\n".join(payloads), encoding="utf-8")

                    return payloads
        except Exception as e:
            print(f"   ⚠️ Failed to download {source_id}: {e}")

        return []

    async def download_all(self, categories: List[str] = None) -> Dict[str, int]:
        """Download all sources (or specific categories)."""
        print("\n📥 Downloading payload databases...")

        async with aiohttp.ClientSession() as session:
            tasks = []
            source_ids = []

            for source_id, source in self.sources.items():
                if categories and source["category"] not in categories:
                    continue

                tasks.append(self.download_source(source_id, session))
                source_ids.append(source_id)

            results = await asyncio.gather(*tasks)

            for source_id, payloads in zip(source_ids, results):
                source = self.sources[source_id]
                cat = source["category"]

                if cat not in self.loaded:
                    self.loaded[cat] = []

                # Deduplicate
                existing = set(self.loaded[cat])
                new_payloads = [p for p in payloads if p not in existing]
                self.loaded[cat].extend(new_payloads)

                if payloads:
                    self.stats[source_id] = len(payloads)
                    print(f"   ✅ {source['name']}: {len(payloads):,} payloads")

        # Final stats
        total = sum(len(p) for p in self.loaded.values())
        print(f"\n📊 Total loaded: {total:,} unique payloads")

        return self.get_category_stats()

    def get_category_stats(self) -> Dict[str, int]:
        """Get payload counts by category."""
        return {cat: len(payloads) for cat, payloads in self.loaded.items()}

    def get_payloads(self, category: str, limit: int = None) -> List[str]:
        """Get payloads for a category."""
        payloads = self.loaded.get(category, [])
        if limit:
            return payloads[:limit]
        return payloads

    def get_all_payloads(self) -> Dict[str, List[str]]:
        """Get all loaded payloads."""
        return self.loaded.copy()

    def search(self, query: str, category: str = None) -> List[str]:
        """Search payloads by substring."""
        results = []
        query_lower = query.lower()

        categories = [category] if category else self.loaded.keys()

        for cat in categories:
            for payload in self.loaded.get(cat, []):
                if query_lower in payload.lower():
                    results.append(payload)

        return results

    def save_stats(self):
        """Save download statistics."""
        stats_file = self.cache_dir / "stats.json"
        stats_file.write_text(json.dumps({
            "downloaded_at": datetime.now().isoformat(),
            "sources": self.stats,
            "categories": self.get_category_stats(),
            "total": sum(len(p) for p in self.loaded.values()),
        }, indent=2))


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

_db: PayloadDB = None


def get_payload_db(cache_dir: str = None) -> PayloadDB:
    """Get or create payload database."""
    global _db

    if _db is None:
        if cache_dir is None:
            cache_dir = Path.home() / ".sentinel-strike" / "payloads"
        _db = PayloadDB(cache_dir=Path(cache_dir))

    return _db


async def download_payloads(categories: List[str] = None) -> Dict[str, int]:
    """Download payloads to local cache."""
    db = get_payload_db()
    return await db.download_all(categories)


def get_payloads(category: str, limit: int = None) -> List[str]:
    """Get payloads from database."""
    db = get_payload_db()
    return db.get_payloads(category, limit)


# ============================================================================
# CLI
# ============================================================================

async def main():
    """CLI for payload database."""
    import argparse

    parser = argparse.ArgumentParser(description="SENTINEL Strike Payload DB")
    parser.add_argument("--download", "-d",
                        action="store_true", help="Download all payloads")
    parser.add_argument("--category", "-c",
                        help="Specific category to download")
    parser.add_argument(
        "--stats", "-s", action="store_true", help="Show stats")
    parser.add_argument("--search", help="Search payloads")

    args = parser.parse_args()

    db = get_payload_db()

    if args.download:
        categories = [args.category] if args.category else None
        await db.download_all(categories)
        db.save_stats()

    elif args.stats:
        stats_file = db.cache_dir / "stats.json"
        if stats_file.exists():
            stats = json.loads(stats_file.read_text())
            print("\n📊 Payload Database Statistics:")
            print(f"   Downloaded: {stats['downloaded_at']}")
            print(f"   Total: {stats['total']:,} payloads")
            print("\n   By Category:")
            for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
                print(f"      {cat:15} {count:,}")
        else:
            print("No stats found. Run with --download first.")

    elif args.search:
        # Need to load first
        await db.download_all()
        results = db.search(args.search)
        print(f"\n🔍 Found {len(results)} matches for '{args.search}':")
        for r in results[:20]:
            print(f"   {r[:80]}")

    else:
        print("SENTINEL Strike Payload Database")
        print("\nAvailable sources:")
        for sid, src in PAYLOAD_SOURCES.items():
            print(f"   {src['category']:12} {src['name']}")
        print(f"\nTotal sources: {len(PAYLOAD_SOURCES)}")
        print("\nRun with --download to fetch all payloads")


if __name__ == "__main__":
    asyncio.run(main())
