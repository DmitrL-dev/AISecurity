#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Auto-Update System

Automatically updates payloads and wordlists from:
1. SecLists (GitHub)
2. PayloadsAllTheThings (GitHub)
3. Assetnote Wordlists
4. HackTricks
5. Custom SENTINEL sources

Features:
- Check for updates on startup
- Download new payloads
- Merge with existing library
- Version tracking
"""

import os
import json
import asyncio
import aiohttp
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

# Config paths - use sentinel-strike directory
# src/strike -> src -> sentinel-strike
STRIKE_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = STRIKE_ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
PAYLOADS_DIR = DATA_DIR / "payloads"
UPDATE_STATE_FILE = DATA_DIR / "update_state.json"


@dataclass
class UpdateSource:
    """Definition of an update source."""
    name: str
    url: str
    type: str  # github_raw, github_api, direct
    category: str  # xss, sqli, fuzzing, endpoints, etc.
    enabled: bool = True
    last_updated: Optional[str] = None
    last_hash: Optional[str] = None


# === UPDATE SOURCES ===
# These are public, well-maintained security wordlists

UPDATE_SOURCES = [
    # === SECLISTS (verified working URLs) ===
    UpdateSource(
        name="SecLists-XSS-Cheatsheet",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/XSS/XSS-Cheat-Sheet-PortSwigger.txt",
        type="github_raw",
        category="xss",
    ),
    UpdateSource(
        name="SecLists-SQLi-Generic",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/SQLi/Generic-BlindSQLi.fuzzdb.txt",
        type="github_raw",
        category="sqli",
    ),
    UpdateSource(
        name="SecLists-LFI",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/LFI/LFI-Jhaddix.txt",
        type="github_raw",
        category="lfi",
    ),
    UpdateSource(
        name="SecLists-SSTI",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Fuzzing/template-engines-special-vars.txt",
        type="github_raw",
        category="ssti",
    ),
    UpdateSource(
        name="SecLists-API-Endpoints",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/api/api-endpoints.txt",
        type="github_raw",
        category="endpoints",
    ),
    UpdateSource(
        name="SecLists-Common-APIs",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common-api-endpoints-mazen160.txt",
        type="github_raw",
        category="endpoints",
    ),
    UpdateSource(
        name="SecLists-Directories",
        url="https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt",
        type="github_raw",
        category="directories",
    ),

    # === PAYLOADSALLTHETHINGS ===
    UpdateSource(
        name="PayloadsATT-XSS",
        url="https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/XSS%20Injection/Intruders/IntrudersXSS.txt",
        type="github_raw",
        category="xss",
    ),
    UpdateSource(
        name="PayloadsATT-SQLi",
        url="https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/SQL%20Injection/Intruder/Auth_Bypass.txt",
        type="github_raw",
        category="sqli",
    ),
    UpdateSource(
        name="PayloadsATT-NoSQLi",
        url="https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/NoSQL%20Injection/Intruder/NoSQL.txt",
        type="github_raw",
        category="nosqli",
    ),

    # === FUZZDB ===
    UpdateSource(
        name="FuzzDB-XSS",
        url="https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/xss/xss-rsnake.txt",
        type="github_raw",
        category="xss",
    ),
    UpdateSource(
        name="FuzzDB-SQLi",
        url="https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/attack/sql-injection/detect/xplatform.txt",
        type="github_raw",
        category="sqli",
    ),

    # === BO0OM FUZZ ===
    UpdateSource(
        name="BO0OM-Fuzz",
        url="https://raw.githubusercontent.com/Bo0oM/fuzz.txt/master/fuzz.txt",
        type="github_raw",
        category="fuzzing",
    ),
]


class PayloadUpdater:
    """
    Manages payload updates from online sources.
    """

    def __init__(self):
        self.sources = UPDATE_SOURCES.copy()
        self.state = self._load_state()
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create necessary directories."""
        DATA_DIR.mkdir(exist_ok=True)
        CACHE_DIR.mkdir(exist_ok=True)
        PAYLOADS_DIR.mkdir(exist_ok=True)

    def _load_state(self) -> Dict:
        """Load update state from file."""
        if UPDATE_STATE_FILE.exists():
            try:
                with open(UPDATE_STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "last_check": None,
            "sources": {},
            "stats": {"total_payloads": 0, "last_update_count": 0}
        }

    def _save_state(self):
        """Save update state to file."""
        try:
            with open(UPDATE_STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _compute_hash(self, content: str) -> str:
        """Compute hash of content for change detection."""
        return hashlib.md5(content.encode()).hexdigest()

    async def check_updates(self, force: bool = False) -> Dict:
        """
        Check for available updates.

        Args:
            force: Force check even if recently checked

        Returns:
            Dict with update status
        """
        # Always check on startup (removed 24h limit per user request)

        print("\n" + "=" * 60)
        print("🔄 SENTINEL Strike — Checking for Updates")
        print("=" * 60)

        updates_available = []
        errors = []

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "SENTINEL-Strike/3.0"}
        ) as session:
            for source in self.sources:
                if not source.enabled:
                    continue

                try:
                    result = await self._check_source(session, source)
                    if result["has_update"]:
                        updates_available.append(result)
                        print(
                            f"  ✨ NEW: {source.name} ({result['new_count']} payloads)")
                    else:
                        print(f"  ✓ {source.name} (up to date)")
                except Exception as e:
                    errors.append({"source": source.name, "error": str(e)})
                    print(f"  ✗ {source.name} (error: {e})")

        self.state["last_check"] = datetime.now().isoformat()
        self._save_state()

        return {
            "status": "checked",
            "updates_available": len(updates_available),
            "updates": updates_available,
            "errors": errors,
            "last_check": self.state["last_check"]
        }

    async def _check_source(self, session: aiohttp.ClientSession, source: UpdateSource) -> Dict:
        """Check single source for updates."""
        async with session.get(source.url) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            content = await response.text()
            content_hash = self._compute_hash(content)

            # Get stored hash
            stored = self.state.get("sources", {}).get(source.name, {})
            stored_hash = stored.get("hash")

            # Parse payloads
            payloads = self._parse_payloads(content, source.category)

            has_update = content_hash != stored_hash

            return {
                "source": source.name,
                "category": source.category,
                "has_update": has_update,
                "new_count": len(payloads),
                "hash": content_hash,
                "payloads": payloads if has_update else []
            }

    def _parse_payloads(self, content: str, category: str) -> List[str]:
        """Parse payloads from raw content."""
        payloads = []

        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                # Clean up common issues
                if category == "jailbreak" and ',' in line:
                    # CSV format
                    parts = line.split(',')
                    if len(parts) > 1:
                        line = parts[1].strip('"\'')
                payloads.append(line)

        return payloads

    async def update(self, categories: Optional[List[str]] = None) -> Dict:
        """
        Download and apply updates.

        Args:
            categories: Optional list of categories to update (None = all)

        Returns:
            Update results
        """
        print("\n" + "=" * 60)
        print("📦 SENTINEL Strike — Downloading Updates")
        print("=" * 60)

        total_new = 0
        updated_sources = []

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"User-Agent": "SENTINEL-Strike/3.0"}
        ) as session:
            for source in self.sources:
                if not source.enabled:
                    continue
                if categories and source.category not in categories:
                    continue

                try:
                    result = await self._download_source(session, source)
                    if result["success"]:
                        total_new += result["count"]
                        updated_sources.append(source.name)
                        print(
                            f"  ✅ {source.name}: +{result['count']} payloads")
                except Exception as e:
                    print(f"  ❌ {source.name}: {e}")

        # Update state
        self.state["stats"]["last_update_count"] = total_new
        self.state["stats"]["total_payloads"] = self._count_total_payloads()
        self._save_state()

        print(f"\n📊 Total new payloads: {total_new}")
        print(f"📊 Total library size: {self.state['stats']['total_payloads']}")

        return {
            "success": True,
            "new_payloads": total_new,
            "updated_sources": updated_sources,
            "total_payloads": self.state["stats"]["total_payloads"]
        }

    async def _download_source(self, session: aiohttp.ClientSession, source: UpdateSource) -> Dict:
        """Download and save payloads from source."""
        async with session.get(source.url) as response:
            if response.status != 200:
                raise Exception(f"HTTP {response.status}")

            content = await response.text()
            content_hash = self._compute_hash(content)
            payloads = self._parse_payloads(content, source.category)

            # Save to category file
            category_file = PAYLOADS_DIR / f"{source.category}.txt"
            existing = set()

            if category_file.exists():
                with open(category_file, 'r', encoding='utf-8', errors='ignore') as f:
                    existing = set(line.strip() for line in f if line.strip())

            # Merge new payloads
            new_payloads = set(payloads) - existing
            all_payloads = existing | set(payloads)

            # Write back
            with open(category_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sorted(all_payloads)))

            # Update source state
            if "sources" not in self.state:
                self.state["sources"] = {}
            self.state["sources"][source.name] = {
                "hash": content_hash,
                "last_updated": datetime.now().isoformat(),
                "count": len(payloads)
            }

            return {"success": True, "count": len(new_payloads)}

    def _count_total_payloads(self) -> int:
        """Count total payloads in library."""
        total = 0
        if not PAYLOADS_DIR.exists():
            return 0
        for file in PAYLOADS_DIR.glob("*.txt"):
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    total += sum(1 for line in f if line.strip())
            except OSError:
                continue  # Skip files with issues
        return total

    def get_payloads(self, category: str) -> List[str]:
        """Get payloads for a category."""
        category_file = PAYLOADS_DIR / f"{category}.txt"
        if category_file.exists():
            with open(category_file, 'r', encoding='utf-8', errors='ignore') as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def get_all_categories(self) -> List[str]:
        """Get all available categories."""
        return [f.stem for f in PAYLOADS_DIR.glob("*.txt")]

    def get_stats(self) -> Dict:
        """Get update statistics."""
        categories = {}
        for file in PAYLOADS_DIR.glob("*.txt"):
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                categories[file.stem] = sum(1 for line in f if line.strip())

        return {
            "last_check": self.state.get("last_check"),
            "total_payloads": sum(categories.values()),
            "categories": categories,
            "sources_count": len([s for s in self.sources if s.enabled])
        }


async def check_and_update(force: bool = False) -> Dict:
    """
    Convenience function to check and apply updates.

    Called on Strike startup.
    """
    updater = PayloadUpdater()

    # Check for updates
    check_result = await updater.check_updates(force=force)

    if check_result.get("updates_available", 0) > 0:
        # Ask user or auto-update
        print(f"\n🆕 {check_result['updates_available']} updates available!")

        # Auto-update
        update_result = await updater.update()
        return {
            "checked": True,
            "updated": True,
            **update_result
        }

    return {
        "checked": True,
        "updated": False,
        "status": check_result.get("status"),
        "stats": updater.get_stats()
    }


def get_total_payload_count() -> int:
    """
    Get total payload count from all sources.
    Used for dynamic display in UI.
    """
    from strike.payloads.attack_payloads import get_payload_counts
    from strike.payloads.extended_payloads import get_extended_payload_counts

    # Base payloads
    try:
        base_stats = get_payload_counts()
        base_total = base_stats.get("total", 0)
    except Exception:
        base_total = 27000  # Fallback

    # Extended payloads
    try:
        ext_counts = get_extended_payload_counts()
        ext_total = ext_counts.get("total", 0)
    except Exception:
        ext_total = 325

    # Downloaded payloads
    updater = PayloadUpdater()
    downloaded_total = updater._count_total_payloads()

    return base_total + ext_total + downloaded_total


def get_payload_summary() -> dict:
    """Get detailed payload summary for display."""
    total = get_total_payload_count()
    updater = PayloadUpdater()
    stats = updater.get_stats()

    return {
        "total": total,
        "total_display": f"{total:,}+",
        "categories": stats.get("categories", {}),
        "sources": stats.get("sources_count", 0),
        "last_update": stats.get("last_check")
    }


# CLI
if __name__ == "__main__":
    import sys

    async def main():
        force = "--force" in sys.argv
        result = await check_and_update(force=force)
        print(f"\n✅ Update complete: {result}")

    asyncio.run(main())
