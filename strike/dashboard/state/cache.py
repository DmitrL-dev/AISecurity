"""
SENTINEL Strike Dashboard - Recon Cache

Cache reconnaissance results to avoid expensive repeated scans.

Usage:
    from strike.dashboard.state import recon_cache
    
    # Save scan
    recon_cache.save("https://target.com", {...})
    
    # Load cached
    data = recon_cache.load("https://target.com")
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ReconCache:
    """
    Cache reconnaissance results to avoid expensive repeated scans.
    
    Stores scan results as JSON files keyed by hostname.
    
    Example:
        cache = ReconCache()
        cache.save("https://example.com/path", {"ports": [80, 443]})
        data = cache.load("https://example.com")  # Returns cached data
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize the recon cache.
        
        Args:
            cache_dir: Directory for cache files. Defaults to dashboard/recon_cache/
        """
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "recon_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _url_to_filename(self, url: str) -> str:
        """
        Convert URL to safe filename (extract just hostname).
        
        Args:
            url: Full URL
            
        Returns:
            Safe filename with .json extension
        """
        url = url.replace("https://", "").replace("http://", "")
        # Extract just the hostname (remove path and trailing slash)
        url = url.split("/")[0].split(":")[0]
        return f"{url}.json"

    def save(self, url: str, data: Dict) -> Path:
        """
        Save scan results to cache.
        
        Args:
            url: Target URL
            data: Scan results dictionary
            
        Returns:
            Path to saved cache file
        """
        data["_cached_at"] = datetime.now().isoformat()
        data["_target"] = url
        filepath = self.cache_dir / self._url_to_filename(url)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    def load(self, url: str) -> Optional[Dict]:
        """
        Load cached scan results.
        
        Args:
            url: Target URL
            
        Returns:
            Cached data dictionary or None if not found
        """
        filepath = self.cache_dir / self._url_to_filename(url)
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_cached(self) -> List[str]:
        """
        List all cached scans.
        
        Returns:
            List of cached hostnames (without .json extension)
        """
        return [f.stem for f in self.cache_dir.glob("*.json")]

    def delete(self, url: str) -> bool:
        """
        Delete cached scan for URL.
        
        Args:
            url: Target URL
            
        Returns:
            True if deleted, False if not found
        """
        filepath = self.cache_dir / self._url_to_filename(url)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def clear(self) -> int:
        """
        Clear all cached scans.
        
        Returns:
            Number of files deleted
        """
        count = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
            count += 1
        return count


# Global instance
recon_cache = ReconCache()
