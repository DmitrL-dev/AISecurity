"""
SENTINEL Strike — CDN Payload Loader v2

Background loading with progress tracking and polling.
Shows download progress in web UI.
"""

import aiohttp
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# CDN Base URL
CDN_BASE = "https://cdn.jsdelivr.net/gh/" "DmitrL-dev/AISecurity@latest/signatures"

# Local signatures path (fallback)
LOCAL_SIGNATURES = Path(__file__).parent.parent / "signatures"

# Cache directory
CACHE_DIR = Path(__file__).parent / ".cache" / "signatures"


class LoaderState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class LoadProgress:
    """Progress tracking for a single file."""

    file_name: str
    total_bytes: int = 0
    loaded_bytes: int = 0
    status: str = "pending"  # pending, loading, done, error
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def percent(self) -> int:
        if self.total_bytes == 0:
            return 0
        pct = int(self.loaded_bytes / self.total_bytes * 100)
        return min(pct, 100)  # Cap at 100%


@dataclass
class CDNLoaderStatus:
    """Overall loader status."""

    state: LoaderState = LoaderState.IDLE
    version: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    files: Dict[str, LoadProgress] = field(default_factory=dict)
    total_patterns: int = 0  # jailbreaks
    web_payloads: int = 0  # web attack payloads
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "version": self.version,
            "started_at": (self.started_at.isoformat() if self.started_at else None),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "total_patterns": self.total_patterns,
            "web_payloads": self.web_payloads,
            "error": self.error,
            "files": {
                name: {
                    "status": p.status,
                    "percent": p.percent,
                    "loaded_bytes": p.loaded_bytes,
                    "total_bytes": p.total_bytes,
                    "error": p.error,
                }
                for name, p in self.files.items()
            },
            "overall_percent": self._overall_percent(),
        }

    def _overall_percent(self) -> int:
        if not self.files:
            return 0
        # Count completed files
        done = sum(1 for f in self.files.values() if f.status == "done")
        total = len(self.files)
        if total == 0:
            return 0
        return int(done / total * 100)


class CDNPayloadLoaderV2:
    """
    Background CDN loader with progress tracking.

    Features:
    - Background async loading
    - Progress tracking per file
    - Polling endpoint for status
    - Local file fallback
    - Auto-retry on failure
    """

    def __init__(self):
        self.status = CDNLoaderStatus()
        self.signatures: Dict[str, Any] = {}
        self._load_task: Optional[asyncio.Task] = None

        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def start_background_load(self):
        """Start loading in background."""
        if self._load_task and not self._load_task.done():
            return  # Already loading

        self._load_task = asyncio.create_task(self._load_all_async())

    async def _load_all_async(self):
        """Main background loading coroutine."""
        self.status.state = LoaderState.LOADING
        self.status.started_at = datetime.now()
        self.status.error = None

        try:
            # Initialize progress for files
            self.status.files = {
                "manifest": LoadProgress("manifest.json"),
                "jailbreaks_manifest": LoadProgress("jailbreaks-manifest.json"),
                "jailbreaks_part1": LoadProgress("jailbreaks-part1.json", 14479721),
                "jailbreaks_part2": LoadProgress("jailbreaks-part2.json", 12631709),
                "keywords": LoadProgress("keywords.json"),
                "pii": LoadProgress("pii.json"),
                "web_payloads": LoadProgress("web-payloads.json", 316_000),
            }

            async with aiohttp.ClientSession() as session:
                # Load manifest
                manifest = await self._load_file(session, "manifest")
                if manifest:
                    self.status.version = manifest.get("version")

                # Load jailbreaks manifest
                jb_manifest = await self._load_file(session, "jailbreaks_manifest")
                if jb_manifest and jb_manifest.get("split"):
                    self.status.total_patterns = jb_manifest.get("total_patterns", 0)

                    # Load parts - each part is dict with 'patterns' key
                    all_jailbreaks = []
                    for part_name in ["jailbreaks_part1", "jailbreaks_part2"]:
                        data = await self._load_file(session, part_name)
                        if data:
                            # Extract patterns from dict structure
                            if isinstance(data, dict):
                                patterns = data.get("patterns", [])
                                all_jailbreaks.extend(patterns)
                            elif isinstance(data, list):
                                all_jailbreaks.extend(data)

                    if all_jailbreaks:
                        self.signatures["jailbreaks"] = all_jailbreaks
                        self.status.total_patterns = len(all_jailbreaks)
                        logger.info(f"✅ Loaded {len(all_jailbreaks)} jailbreaks")

                # Load other files
                for name in ["keywords", "pii"]:
                    data = await self._load_file(session, name)
                    if data:
                        self.signatures[name] = data

                # Load web payloads (from PayloadsAllTheThings)
                web_data = await self._load_file(session, "web_payloads")
                if web_data and isinstance(web_data, dict):
                    categories = web_data.get("categories", {})
                    total_web = sum(len(p) for p in categories.values())
                    self.signatures["web_payloads"] = categories
                    self.status.web_payloads = total_web
                    logger.info(f"✅ Loaded {total_web} web payloads")
                else:
                    # CDN failed, try local
                    await self._load_local_web_payloads()

            # Check if we have jailbreaks
            if not self.signatures.get("jailbreaks"):
                # Fallback to local files
                await self._load_local_fallback()

            self.status.state = LoaderState.COMPLETED
            self.status.completed_at = datetime.now()

        except Exception as e:
            logger.error(f"CDN load failed: {e}")
            self.status.state = LoaderState.FAILED
            self.status.error = str(e)
            # Try local fallback
            await self._load_local_fallback()

    async def _load_file(
        self, session: aiohttp.ClientSession, name: str
    ) -> Optional[Any]:
        """Load a single file with progress tracking."""
        progress = self.status.files.get(name)
        if not progress:
            return None

        progress.status = "loading"
        progress.started_at = datetime.now()

        url = self._get_url(name)
        if not url:
            progress.status = "error"
            progress.error = "Unknown file"
            return None

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    progress.status = "error"
                    progress.error = f"HTTP {response.status}"
                    return None

                # Get content length
                total = int(response.headers.get("Content-Length", 0))
                if total > 0:
                    progress.total_bytes = total

                # Read with progress tracking
                chunks = []
                async for chunk in response.content.iter_chunked(64 * 1024):
                    chunks.append(chunk)
                    progress.loaded_bytes += len(chunk)

                data = b"".join(chunks)
                result = json.loads(data.decode("utf-8"))

                progress.status = "done"
                progress.completed_at = datetime.now()

                # Cache locally
                self._save_cache(name, result)

                return result

        except asyncio.TimeoutError:
            progress.status = "error"
            progress.error = "Timeout"
            return self._load_cache(name)

        except Exception as e:
            progress.status = "error"
            progress.error = str(e)
            return self._load_cache(name)

    def _get_url(self, name: str) -> Optional[str]:
        """Get CDN URL for file."""
        urls = {
            "manifest": f"{CDN_BASE}/manifest.json",
            "jailbreaks_manifest": f"{CDN_BASE}/jailbreaks-manifest.json",
            "jailbreaks_part1": f"{CDN_BASE}/jailbreaks-part1.json",
            "jailbreaks_part2": f"{CDN_BASE}/jailbreaks-part2.json",
            "keywords": f"{CDN_BASE}/keywords.json",
            "pii": f"{CDN_BASE}/pii.json",
            "web_payloads": f"{CDN_BASE}/web-payloads.json",
        }
        return urls.get(name)

    async def _load_local_fallback(self):
        """Load from local signatures directory."""
        logger.info("📂 Using local fallback...")
        self.status.state = LoaderState.PARTIAL

        for part_name in ["jailbreaks-part1.json", "jailbreaks-part2.json"]:
            local_file = LOCAL_SIGNATURES / part_name
            if local_file.exists():
                try:
                    with open(local_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "jailbreaks" not in self.signatures:
                            self.signatures["jailbreaks"] = []
                        # Extract patterns from dict if needed
                        if isinstance(data, dict):
                            patterns = data.get("patterns", [])
                            self.signatures["jailbreaks"].extend(patterns)
                        elif isinstance(data, list):
                            self.signatures["jailbreaks"].extend(data)
                        logger.info(f"📂 Local {part_name}")
                except Exception as e:
                    logger.warning(f"Local load failed: {e}")

        # Load web payloads from local
        web_file = LOCAL_SIGNATURES / "web-payloads.json"
        if web_file.exists() and not self.signatures.get("web_payloads"):
            try:
                with open(web_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    categories = data.get("categories", {})
                    total_web = sum(len(p) for p in categories.values())
                    self.signatures["web_payloads"] = categories
                    self.status.web_payloads = total_web
                    logger.info(f"📂 Local web payloads: {total_web}")
            except Exception as e:
                logger.warning(f"Local web payloads load failed: {e}")

        if self.signatures.get("jailbreaks"):
            self.status.total_patterns = len(self.signatures["jailbreaks"])
            self.status.state = LoaderState.COMPLETED

    async def _load_local_web_payloads(self):
        """Load web payloads from local signatures directory."""
        web_file = LOCAL_SIGNATURES / "web-payloads.json"
        if web_file.exists() and not self.signatures.get("web_payloads"):
            try:
                with open(web_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    categories = data.get("categories", {})
                    total = sum(len(p) for p in categories.values())
                    self.signatures["web_payloads"] = categories
                    self.status.web_payloads = total
                    logger.info(f"📂 Local web payloads: {total}")
            except Exception as e:
                logger.warning(f"Local web payloads failed: {e}")

    def _save_cache(self, name: str, data: Any):
        """Save to local cache."""
        try:
            cache_file = CACHE_DIR / f"{name}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_cache(self, name: str) -> Optional[Any]:
        """Load from local cache."""
        try:
            cache_file = CACHE_DIR / f"{name}.json"
            if cache_file.exists():
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get current loading status for polling."""
        return self.status.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        """Get final stats after loading."""
        return {
            "version": self.status.version,
            "loaded_at": (
                self.status.completed_at.isoformat()
                if self.status.completed_at
                else None
            ),
            "jailbreaks_count": len(self.signatures.get("jailbreaks", [])),
            "keywords_categories": len(self.signatures.get("keywords", {})),
            "pii_patterns_count": len(self.signatures.get("pii", [])),
            "state": self.status.state.value,
        }


# Global instance
_loader: Optional[CDNPayloadLoaderV2] = None


def get_loader() -> CDNPayloadLoaderV2:
    """Get or create loader instance."""
    global _loader
    if _loader is None:
        _loader = CDNPayloadLoaderV2()
    return _loader


def start_background_load():
    """Start background loading (call from startup event)."""
    loader = get_loader()
    loader.start_background_load()
    logger.info("🚀 CDN background loading started")
