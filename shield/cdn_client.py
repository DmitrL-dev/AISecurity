"""
SENTINEL Shield v2.0 — CDN Signature Pack Client

Downloads and validates signature packs from CDN
(GitHub Releases or custom URL).

Pack format:
  {
    "version": "2.0.0-20260210",
    "timestamp": "2026-02-10T04:00:00Z",
    "sha256": "...",
    "patterns": [
      {
        "type": "REGEX",
        "pattern": "...",
        "category": "injection",
        "severity": 9,
        "description": "..."
      }
    ]
  }

Features:
- Download with retry logic
- SHA256 integrity verification
- Rollback to previous version on failure
- Background scheduler for periodic updates
"""

import os
import json
import hashlib
import logging
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("shield.cdn")


@dataclass
class SignaturePack:
    """Downloaded signature pack metadata."""

    version: str
    timestamp: str
    sha256: str
    patterns: list[dict]
    source_url: str = ""
    download_time: float = 0.0

    @property
    def pattern_count(self) -> int:
        return len(self.patterns)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "sha256": self.sha256[:16] + "...",
            "pattern_count": self.pattern_count,
            "source_url": self.source_url,
            "download_time_ms": round(self.download_time * 1000, 2),
        }


@dataclass
class CDNConfig:
    """CDN client configuration."""

    base_url: str = "https://cdn.jsdelivr.net/gh/DmitrL-dev/AISecurity@main/sentinel-community/signatures"
    check_interval_hours: int = 24
    max_retries: int = 3
    timeout_seconds: int = 30
    cache_dir: str = ""
    max_cached_versions: int = 5


class CDNClient:
    """
    CDN signature pack client.

    Downloads, validates, and caches signature packs.
    Supports rollback via cached previous versions.
    """

    def __init__(self, config: CDNConfig | None = None):
        self.config = config or CDNConfig()
        self.current_pack: Optional[SignaturePack] = None
        self._history: list[SignaturePack] = []
        self._last_check: float = 0
        self._total_downloads: int = 0
        self._total_failures: int = 0

        # Cache directory
        if self.config.cache_dir:
            self._cache_path = Path(self.config.cache_dir)
        else:
            self._cache_path = Path(__file__).parent / "data" / "cdn_cache"
        self._cache_path.mkdir(parents=True, exist_ok=True)

    def _verify_integrity(self, data: bytes, expected_hash: str) -> bool:
        """Verify SHA256 hash of downloaded data."""
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected_hash:
            logger.error(
                f"Hash mismatch: expected {expected_hash[:16]}..., got {actual[:16]}..."
            )
            return False
        return True

    def _parse_pack(self, data: bytes, source_url: str = "") -> Optional[SignaturePack]:
        """Parse and validate a signature pack."""
        try:
            obj = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in pack: {e}")
            return None

        required = ("version", "patterns")
        for key in required:
            if key not in obj:
                logger.error(f"Missing required field: {key}")
                return None

        if not isinstance(obj["patterns"], list):
            logger.error("'patterns' must be a list")
            return None

        # Validate individual patterns
        valid_patterns = []
        for p in obj["patterns"]:
            if not isinstance(p, dict):
                continue
            if "pattern" not in p:
                continue
            # Normalize fields
            normalized = {
                "type": p.get("type", "REGEX"),
                "pattern": p["pattern"],
                "category": p.get("category", "injection"),
                "severity": min(
                    10,
                    max(0, int(p.get("severity", 5))),
                ),
                "description": p.get("description", ""),
            }
            valid_patterns.append(normalized)

        if not valid_patterns:
            logger.error("No valid patterns in pack")
            return None

        pack = SignaturePack(
            version=obj["version"],
            timestamp=obj.get("timestamp", ""),
            sha256=obj.get("sha256", ""),
            patterns=valid_patterns,
            source_url=source_url,
        )

        logger.info(f"Parsed pack v{pack.version}: {pack.pattern_count} patterns")
        return pack

    def _cache_pack(self, pack: SignaturePack, data: bytes):
        """Save pack to local cache directory."""
        fname = f"pack_{pack.version}.json"
        fpath = self._cache_path / fname
        try:
            fpath.write_bytes(data)
            logger.info(f"Cached pack at {fpath}")
        except OSError as e:
            logger.warning(f"Cache write failed: {e}")

        # Clean old versions
        self._cleanup_cache()

    def _cleanup_cache(self):
        """Remove old cached packs beyond max."""
        cached = sorted(
            self._cache_path.glob("pack_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in cached[self.config.max_cached_versions :]:
            try:
                old.unlink()
                logger.debug(f"Removed old cache: {old}")
            except OSError:
                pass

    def load_from_cache(
        self,
    ) -> Optional[SignaturePack]:
        """Load most recent pack from local cache."""
        cached = sorted(
            self._cache_path.glob("pack_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not cached:
            return None

        try:
            data = cached[0].read_bytes()
            pack = self._parse_pack(data, source_url=str(cached[0]))
            if pack:
                logger.info(f"Loaded from cache: v{pack.version}")
                self.current_pack = pack
            return pack
        except OSError as e:
            logger.error(f"Cache read failed: {e}")
            return None

    async def fetch_pack(
        self,
        url: Optional[str] = None,
    ) -> Optional[SignaturePack]:
        """
        Download signature pack from CDN.

        Uses httpx for async HTTP.
        Falls back to cache on failure.
        """
        target = url or self.config.base_url
        if not target:
            logger.warning("No CDN URL configured")
            return self.load_from_cache()

        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed — CDN updates disabled")
            return self.load_from_cache()

        start = time.perf_counter()
        last_error = None

        for attempt in range(1, self.config.max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self.config.timeout_seconds
                ) as client:
                    resp = await client.get(target)
                    resp.raise_for_status()
                    data = resp.content

                # Verify integrity if hash provided
                pack = self._parse_pack(data, target)
                if pack is None:
                    self._total_failures += 1
                    return self.load_from_cache()

                if pack.sha256:
                    # Compute hash of patterns only
                    patterns_json = json.dumps(
                        pack.patterns,
                        sort_keys=True,
                    ).encode()
                    if not self._verify_integrity(patterns_json, pack.sha256):
                        self._total_failures += 1
                        return self.load_from_cache()

                # Success
                elapsed = time.perf_counter() - start
                pack.download_time = elapsed
                self._total_downloads += 1
                self._last_check = time.time()

                # Archive current before replacing
                if self.current_pack:
                    self._history.append(self.current_pack)
                    # Keep last N
                    mx = self.config.max_cached_versions
                    self._history = self._history[-mx:]

                self.current_pack = pack
                self._cache_pack(pack, data)

                logger.info(
                    f"CDN update: v{pack.version} "
                    f"({pack.pattern_count} patterns, "
                    f"{elapsed * 1000:.0f}ms)"
                )
                return pack

            except Exception as e:
                last_error = e
                logger.warning(
                    f"CDN fetch attempt {attempt}/{self.config.max_retries} failed: {e}"
                )
                if attempt < self.config.max_retries:
                    # Exponential backoff
                    import asyncio

                    await asyncio.sleep(2**attempt)

        # All retries failed
        self._total_failures += 1
        logger.error(
            f"CDN fetch failed after {self.config.max_retries} retries: {last_error}"
        )
        return self.load_from_cache()

    def rollback(self) -> Optional[SignaturePack]:
        """
        Rollback to previous signature pack version.

        Returns the restored pack, or None if no
        history available.
        """
        if not self._history:
            logger.warning("No history for rollback")
            return None

        prev = self._history.pop()
        logger.info(f"Rolling back to v{prev.version}")

        # Current becomes archived
        if self.current_pack:
            # Don't re-add to history
            pass

        self.current_pack = prev
        return prev

    def needs_update(self) -> bool:
        """Check if enough time has passed for update."""
        if self._last_check == 0:
            return True
        elapsed_hours = (time.time() - self._last_check) / 3600
        return elapsed_hours >= self.config.check_interval_hours

    def stats(self) -> dict:
        return {
            "cdn_url": self.config.base_url or "(none)",
            "current_version": (
                self.current_pack.version if self.current_pack else "(none)"
            ),
            "current_patterns": (
                self.current_pack.pattern_count if self.current_pack else 0
            ),
            "history_depth": len(self._history),
            "total_downloads": self._total_downloads,
            "total_failures": self._total_failures,
            "last_check": (self._last_check if self._last_check else None),
            "check_interval_h": (self.config.check_interval_hours),
            "cache_dir": str(self._cache_path),
        }
