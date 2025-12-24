#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Residential Proxy Integration

Supports multiple residential proxy providers for WAF bypass:
- ScraperAPI (5K free requests)
- GoProxy (7-day trial)
- BrightData
- Oxylabs
- Custom proxy

Requirements:
    pip install aiohttp
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List, Tuple
import random
import asyncio


class ProxyProvider(Enum):
    """Supported proxy providers."""
    SCRAPERAPI = "scraperapi"       # 5K free, no card
    GOPROXY = "goproxy"             # 7-day trial
    BRIGHTDATA = "brightdata"       # Enterprise
    OXYLABS = "oxylabs"             # Enterprise
    ZENROWS = "zenrows"             # Free trial
    SMARTPROXY = "smartproxy"       # 3-day trial
    CUSTOM = "custom"               # Custom proxy URL


@dataclass
class ProxyConfig:
    """Configuration for residential proxy."""
    provider: ProxyProvider
    api_key: str = ""
    username: str = ""
    password: str = ""
    proxy_url: str = ""
    country: str = "us"
    session_type: str = "rotating"  # rotating or sticky
    render_js: bool = False


class ResidentialProxyManager:
    """
    Manages residential proxy connections for WAF bypass.

    Features:
    - Multiple provider support
    - Automatic rotation
    - Country targeting
    - Session persistence
    """

    def __init__(self, config: ProxyConfig):
        self.config = config
        self.request_count = 0
        self.session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """Generate unique session ID for sticky sessions."""
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))

    def get_scraperapi_url(self, target_url: str) -> str:
        """
        Get ScraperAPI proxy URL.

        ScraperAPI handles everything via URL parameter.
        Free tier: 5,000 requests/month, no credit card.
        """
        from urllib.parse import quote

        params = [
            f"api_key={self.config.api_key}",
            f"url={quote(target_url)}",
            f"country_code={self.config.country}",
        ]

        if self.config.render_js:
            params.append("render=true")

        if self.config.session_type == "sticky":
            params.append(f"session_number={self.session_id}")

        return f"http://api.scraperapi.com/?{'&'.join(params)}"

    def get_goproxy_config(self) -> Dict[str, str]:
        """
        Get GoProxy proxy configuration.

        GoProxy uses username:password@host:port format.
        7-day free trial available.
        """
        # GoProxy format: user-zone-country:password@proxy.goproxy.com:port
        username = f"{self.config.username}-zone-{self.config.country}"
        proxy_url = f"http://{username}:{self.config.password}@proxy.goproxy.com:8080"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def get_brightdata_config(self) -> Dict[str, str]:
        """
        Get BrightData proxy configuration.

        BrightData (formerly Luminati) - enterprise residential proxies.
        """
        # BrightData format: user-country-cc:password@host:port
        username = f"{self.config.username}-country-{self.config.country}"
        if self.config.session_type == "sticky":
            username += f"-session-{self.session_id}"

        proxy_url = f"http://{username}:{self.config.password}@brd.superproxy.io:22225"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def get_oxylabs_config(self) -> Dict[str, str]:
        """
        Get Oxylabs proxy configuration.

        Oxylabs - premium residential proxies.
        """
        # Oxylabs format: user-cc:password@host:port
        username = f"customer-{self.config.username}-cc-{self.config.country}"
        if self.config.session_type == "sticky":
            username += f"-sessid-{self.session_id}"

        proxy_url = f"http://{username}:{self.config.password}@pr.oxylabs.io:7777"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def get_zenrows_url(self, target_url: str) -> str:
        """
        Get ZenRows API URL.

        ZenRows - web scraping API with residential proxies.
        """
        from urllib.parse import quote

        params = [
            f"apikey={self.config.api_key}",
            f"url={quote(target_url)}",
        ]

        if self.config.render_js:
            params.append("js_render=true")

        return f"https://api.zenrows.com/v1/?{'&'.join(params)}"

    def get_smartproxy_config(self) -> Dict[str, str]:
        """
        Get Smartproxy (Decodo) configuration.

        Smartproxy - 3-day free trial with 100MB.
        """
        # Smartproxy format: user:password@gate.smartproxy.com:port
        proxy_url = f"http://{self.config.username}:{self.config.password}@gate.smartproxy.com:7000"

        if self.config.country != "random":
            # Country-specific endpoint
            proxy_url = f"http://{self.config.username}:{self.config.password}@{self.config.country}.smartproxy.com:7000"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }

    def get_proxy_for_request(self, target_url: str = "") -> Tuple[str, Dict[str, str]]:
        """
        Get proxy configuration for request.

        Returns:
            Tuple of (url_to_request, proxy_dict)
            For API-based proxies, url_to_request is the API URL.
            For standard proxies, url_to_request is the original target.
        """
        self.request_count += 1

        if self.config.provider == ProxyProvider.SCRAPERAPI:
            # ScraperAPI uses URL rewriting
            return self.get_scraperapi_url(target_url), {}

        elif self.config.provider == ProxyProvider.ZENROWS:
            # ZenRows uses URL rewriting
            return self.get_zenrows_url(target_url), {}

        elif self.config.provider == ProxyProvider.GOPROXY:
            return target_url, self.get_goproxy_config()

        elif self.config.provider == ProxyProvider.BRIGHTDATA:
            return target_url, self.get_brightdata_config()

        elif self.config.provider == ProxyProvider.OXYLABS:
            return target_url, self.get_oxylabs_config()

        elif self.config.provider == ProxyProvider.SMARTPROXY:
            return target_url, self.get_smartproxy_config()

        elif self.config.provider == ProxyProvider.CUSTOM:
            return target_url, {
                "http": self.config.proxy_url,
                "https": self.config.proxy_url,
            }

        # No proxy
        return target_url, {}

    def rotate_session(self):
        """Rotate session ID for new IP."""
        self.session_id = self._generate_session_id()

    async def test_connection(self) -> bool:
        """Test proxy connection."""
        try:
            import aiohttp

            url, proxy = self.get_proxy_for_request("https://httpbin.org/ip")

            async with aiohttp.ClientSession() as session:
                if proxy:
                    async with session.get(url, proxy=proxy.get("http"), timeout=10) as resp:
                        return resp.status == 200
                else:
                    async with session.get(url, timeout=10) as resp:
                        return resp.status == 200
        except Exception as e:
            print(f"Proxy test failed: {e}")
            return False


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_scraperapi_proxy(api_key: str, country: str = "us") -> ResidentialProxyManager:
    """Create ScraperAPI proxy manager (5K free requests)."""
    config = ProxyConfig(
        provider=ProxyProvider.SCRAPERAPI,
        api_key=api_key,
        country=country,
    )
    return ResidentialProxyManager(config)


def create_goproxy(username: str, password: str, country: str = "us") -> ResidentialProxyManager:
    """Create GoProxy manager (7-day trial)."""
    config = ProxyConfig(
        provider=ProxyProvider.GOPROXY,
        username=username,
        password=password,
        country=country,
    )
    return ResidentialProxyManager(config)


def create_brightdata_proxy(username: str, password: str, country: str = "us") -> ResidentialProxyManager:
    """Create BrightData proxy manager."""
    config = ProxyConfig(
        provider=ProxyProvider.BRIGHTDATA,
        username=username,
        password=password,
        country=country,
    )
    return ResidentialProxyManager(config)


def create_custom_proxy(proxy_url: str) -> ResidentialProxyManager:
    """Create custom proxy manager."""
    config = ProxyConfig(
        provider=ProxyProvider.CUSTOM,
        proxy_url=proxy_url,
    )
    return ResidentialProxyManager(config)


# Available providers for export
PROXY_PROVIDERS = {
    "scraperapi": {
        "name": "ScraperAPI",
        "free_tier": "5,000 requests/month",
        "signup": "https://www.scraperapi.com/signup",
        "card_required": False,
    },
    "goproxy": {
        "name": "GoProxy",
        "free_tier": "7-day trial",
        "signup": "https://www.goproxy.com/",
        "card_required": True,
    },
    "zenrows": {
        "name": "ZenRows",
        "free_tier": "1,000 requests",
        "signup": "https://www.zenrows.com/",
        "card_required": False,
    },
    "smartproxy": {
        "name": "Smartproxy (Decodo)",
        "free_tier": "3-day / 100MB",
        "signup": "https://dashboard.smartproxy.com/register",
        "card_required": True,
    },
    "brightdata": {
        "name": "Bright Data",
        "free_tier": "Trial available",
        "signup": "https://brightdata.com/",
        "card_required": True,
    },
}
