"""
SENTINEL Strike — Proxy Chain

Multi-hop proxy support for IP rotation.
"""

import random
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ProxyType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class Proxy:
    """Single proxy server."""

    host: str
    port: int
    type: ProxyType = ProxyType.HTTP
    username: Optional[str] = None
    password: Optional[str] = None

    @property
    def url(self) -> str:
        auth = ""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        return f"{self.type.value}://{auth}{self.host}:{self.port}"


class ProxyChain:
    """Manage chain of proxies for multi-hop routing."""

    def __init__(self):
        self.proxies: list[Proxy] = []
        self.current_index = 0
        self.tor_enabled = False

    def add_proxy(self, proxy: Proxy):
        """Add proxy to chain."""
        self.proxies.append(proxy)

    def add_from_url(self, url: str):
        """Parse and add proxy from URL."""
        # Parse: type://user:pass@host:port
        import re

        pattern = r"(https?|socks[45])://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)"
        match = re.match(pattern, url)
        if match:
            ptype, user, pwd, host, port = match.groups()
            self.add_proxy(
                Proxy(
                    host=host,
                    port=int(port),
                    type=ProxyType(ptype),
                    username=user,
                    password=pwd,
                )
            )

    def get_current(self) -> Optional[Proxy]:
        """Get current proxy."""
        if not self.proxies:
            return None
        return self.proxies[self.current_index]

    def rotate(self) -> Optional[Proxy]:
        """Rotate to next proxy."""
        if not self.proxies:
            return None
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return self.get_current()

    def get_random(self) -> Optional[Proxy]:
        """Get random proxy."""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def get_httpx_proxy(self) -> Optional[str]:
        """Get proxy URL for httpx client."""
        proxy = self.get_current()
        return proxy.url if proxy else None

    def enable_tor(self, port: int = 9050):
        """Enable Tor SOCKS proxy."""
        self.tor_enabled = True
        self.add_proxy(Proxy(host="127.0.0.1", port=port, type=ProxyType.SOCKS5))
