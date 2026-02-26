"""
SENTINEL Strike — Identity Manager

Rotate IP, User-Agent, TLS fingerprints.
"""

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class Identity:
    """Single identity profile."""

    ip: Optional[str] = None
    user_agent: str = ""
    accept_language: str = "en-US,en;q=0.9"
    platform: str = "Windows"

    def to_headers(self) -> dict:
        return {
            "User-Agent": self.user_agent,
            "Accept-Language": self.accept_language,
            "Accept": "text/html,application/json,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }


# Real browser User-Agents (2024-2025)
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]


class IdentityManager:
    """Manage rotating identities for stealth."""

    def __init__(self):
        self.current: Identity = self._generate()
        self.history: list[Identity] = []
        self.rotation_count = 0

    def _generate(self) -> Identity:
        """Generate new random identity."""
        ua = random.choice(USER_AGENTS)
        platform = "Windows" if "Windows" in ua else "Mac" if "Mac" in ua else "Mobile"

        return Identity(
            user_agent=ua,
            platform=platform,
            accept_language=random.choice(
                [
                    "en-US,en;q=0.9",
                    "en-GB,en;q=0.9",
                    "ru-RU,ru;q=0.9,en;q=0.8",
                ]
            ),
        )

    def rotate(self) -> Identity:
        """Rotate to new identity."""
        self.history.append(self.current)
        self.current = self._generate()
        self.rotation_count += 1
        return self.current

    def get_headers(self) -> dict:
        """Get current identity as HTTP headers."""
        return self.current.to_headers()

    async def rotate_identity(self):
        """Async rotate for compatibility."""
        return self.rotate()
