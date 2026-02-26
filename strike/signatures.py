"""
SENTINEL Strike — Signature Database Loader

Loads attack signatures from SENTINEL CDN via manifest + parts.
"""

import json
from typing import Optional
from pathlib import Path
import httpx

# CDN URLs for threat signatures (correct path with sentinel-community)
CDN_BASE = "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures"
CDN_URLS = {
    "manifest": f"{CDN_BASE}/jailbreaks-manifest.json",
    "part1": f"{CDN_BASE}/jailbreaks-part1.json",
    "part2": f"{CDN_BASE}/jailbreaks-part2.json",
    "keywords": f"{CDN_BASE}/keywords.json",
    "pii": f"{CDN_BASE}/pii.json",
}

# Local cache directory
CACHE_DIR = Path.home() / ".sentinel-strike" / "signatures"


class SignatureDatabase:
    """
    Signature database with 39,700+ jailbreak patterns.

    Loads from SENTINEL CDN via manifest + split files.
    """

    def __init__(self):
        self.jailbreaks: list[str] = []
        self.keywords: dict = {}
        self.pii_patterns: list = []
        self._loaded = False

    def load_sync(self, use_cache: bool = True) -> None:
        """Load signatures from CDN (split into parts)."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache_file = CACHE_DIR / "jailbreaks_combined.json"
        if use_cache and cache_file.exists():
            self.jailbreaks = json.loads(cache_file.read_text())
            self._loaded = True
            return

        headers = {
            "User-Agent": "SENTINEL-Strike/0.1.0",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                # First get manifest to know structure
                manifest_resp = client.get(
                    CDN_URLS["manifest"], headers=headers)
                manifest_resp.raise_for_status()
                manifest = manifest_resp.json()

                all_patterns = []

                # Load each part
                for part_info in manifest.get("parts", []):
                    part_url = f"{CDN_BASE}/{part_info['file']}"
                    resp = client.get(part_url, headers=headers)
                    resp.raise_for_status()
                    part_data = resp.json()

                    # Extract patterns from part
                    patterns = part_data.get("patterns", [])
                    for p in patterns:
                        if isinstance(p, dict) and "pattern" in p:
                            all_patterns.append(p["pattern"])
                        elif isinstance(p, str):
                            all_patterns.append(p)

                self.jailbreaks = all_patterns

                # Cache combined result
                cache_file.write_text(json.dumps(self.jailbreaks))

        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Failed to load signatures from CDN: {e}") from e

        self._loaded = True

    async def load(self, use_cache: bool = True) -> None:
        """Async version of load."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache_file = CACHE_DIR / "jailbreaks_combined.json"
        if use_cache and cache_file.exists():
            self.jailbreaks = json.loads(cache_file.read_text())
            self._loaded = True
            return

        headers = {
            "User-Agent": "SENTINEL-Strike/0.1.0",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            try:
                manifest_resp = await client.get(CDN_URLS["manifest"], headers=headers)
                manifest_resp.raise_for_status()
                manifest = manifest_resp.json()

                all_patterns = []

                for part_info in manifest.get("parts", []):
                    part_url = f"{CDN_BASE}/{part_info['file']}"
                    resp = await client.get(part_url, headers=headers)
                    resp.raise_for_status()
                    part_data = resp.json()

                    patterns = part_data.get("patterns", [])
                    for p in patterns:
                        if isinstance(p, dict) and "pattern" in p:
                            all_patterns.append(p["pattern"])
                        elif isinstance(p, str):
                            all_patterns.append(p)

                self.jailbreaks = all_patterns
                cache_file.write_text(json.dumps(self.jailbreaks))

            except httpx.HTTPError as e:
                raise RuntimeError(
                    f"Failed to load signatures from CDN: {e}") from e

        self._loaded = True

    @property
    def count(self) -> int:
        """Number of loaded signatures."""
        return len(self.jailbreaks)

    @property
    def is_loaded(self) -> bool:
        """Check if database is loaded."""
        return self._loaded

    def get_random(self, n: int = 10) -> list[str]:
        """Get random sample of signatures."""
        import random
        if not self.jailbreaks:
            return []
        return random.sample(self.jailbreaks, min(n, len(self.jailbreaks)))

    def search(self, query: str) -> list[str]:
        """Search signatures by keyword."""
        query_lower = query.lower()
        return [s for s in self.jailbreaks if query_lower in s.lower()][:100]

    def get_by_category(self, category: str) -> list[str]:
        """Get signatures by category (DAN, STAN, jailbreak, etc.)."""
        category_lower = category.lower()
        return [s for s in self.jailbreaks if category_lower in s.lower()]


# Singleton instance
_db: Optional[SignatureDatabase] = None


def get_signature_db() -> SignatureDatabase:
    """Get or create signature database instance."""
    global _db
    if _db is None:
        _db = SignatureDatabase()
    return _db


async def load_signatures() -> SignatureDatabase:
    """Load and return signature database."""
    db = get_signature_db()
    if not db.is_loaded:
        await db.load()
    return db
