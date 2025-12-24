#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — IP Range Scanner

Discovers company infrastructure by:
1. DNS lookup → Get IP address
2. Whois/ASN lookup → Get IP range (CIDR)
3. Scan range for HTTP services
4. Find chat/AI endpoints on each discovered host
"""

import asyncio
import socket
import aiohttp
import re
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredEndpoint:
    """A discovered endpoint."""

    url: str
    category: str  # chat, api, admin, auth, files, webhooks, internal, ai_ml
    status_code: int = 0
    content_type: str = ""


@dataclass
class DiscoveredHost:
    """A discovered host in the IP range."""

    ip: str
    hostname: Optional[str] = None
    ports: List[int] = field(default_factory=list)
    services: Dict[int, str] = field(default_factory=dict)
    has_http: bool = False
    has_https: bool = False
    endpoints: List[DiscoveredEndpoint] = field(default_factory=list)


@dataclass
class RangeScanResult:
    """Results of IP range scan."""

    domain: str
    base_ip: str
    cidr: str
    total_scanned: int
    hosts_found: int
    hosts: List[DiscoveredHost] = field(default_factory=list)
    # Endpoints grouped by category
    endpoints_by_category: Dict[str, List[str]] = field(default_factory=dict)
    all_endpoints: List[DiscoveredEndpoint] = field(default_factory=list)


class IPRangeScanner:
    """
    Scans company IP range to find hidden services.

    Usage:
        scanner = IPRangeScanner()
        result = await scanner.scan_domain("hh.ru")
    """

    # Common web ports to check
    WEB_PORTS = [80, 443, 8080, 8443, 3000, 8000, 5000, 9000, 4000]

    # All interesting paths to check on each host
    DISCOVERY_PATHS = {
        # Chat/AI endpoints
        "chat": [
            "/chat",
            "/api/chat",
            "/bot",
            "/assistant",
            "/chat/completions",
            "/v1/chat",
            "/support/chat",
        ],
        # API endpoints
        "api": [
            "/api",
            "/api/v1",
            "/api/v2",
            "/v1",
            "/v2",
            "/graphql",
            "/rest",
            "/json-rpc",
            "/grpc",
        ],
        # Admin panels
        "admin": [
            "/admin",
            "/administrator",
            "/manage",
            "/dashboard",
            "/panel",
            "/control",
            "/backend",
            "/cms",
        ],
        # Auth endpoints
        "auth": [
            "/login",
            "/auth",
            "/oauth",
            "/oauth2",
            "/sso",
            "/signin",
            "/signup",
            "/register",
            "/token",
        ],
        # File operations
        "files": [
            "/upload",
            "/uploads",
            "/files",
            "/download",
            "/media",
            "/static",
            "/assets",
            "/storage",
        ],
        # Webhooks/Integrations
        "webhooks": [
            "/webhook",
            "/webhooks",
            "/callback",
            "/hook",
            "/notify",
            "/events",
            "/integration",
        ],
        # Internal/Debug
        "internal": [
            "/internal",
            "/debug",
            "/health",
            "/status",
            "/metrics",
            "/info",
            "/.well-known",
            "/actuator",
        ],
        # AI/ML specific
        "ai_ml": [
            "/predict",
            "/inference",
            "/model",
            "/models",
            "/completions",
            "/generate",
            "/embed",
            "/embeddings",
        ],
    }

    def __init__(
        self,
        timeout: int = 5,
        max_concurrent: int = 50,
        scan_range: int = 16,  # Fallback if WHOIS fails
        proxy_url: str = None,
        auto_detect_range: bool = True,  # Use WHOIS/ASN to find org range
    ):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.scan_range = min(scan_range, 256)  # Max /24
        self.proxy_url = proxy_url
        self.auto_detect_range = auto_detect_range

    async def _get_org_network(self, ip: str) -> tuple:
        """
        Get organization's network range via ASN/WHOIS lookup.
        Returns (start_ip, end_ip, org_name, cidr)
        """
        print(f"🔍 Looking up organization network for {ip}...")

        try:
            # Use ipinfo.io API (free, no key required for basic info)
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"https://ipinfo.io/{ip}/json"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        org = data.get("org", "Unknown")

                        # Try to get ASN details
                        asn_url = f"https://ipinfo.io/{ip}/json"

                        print(f"🏢 Organization: {org}")

                        # Parse CIDR if available
                        # ipinfo returns network in some plans
                        # For free tier, estimate from IP

            # Fallback: Try ipapi.co
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                url = f"https://ipapi.co/{ip}/json/"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        org = data.get("org", "Unknown")
                        asn = data.get("asn", "")

                        print(f"🏢 Organization: {org}")
                        if asn:
                            print(f"📡 ASN: {asn}")

                        # Get network range from ASN
                        # ipapi doesn't give CIDR directly, estimate /24
                        ip_parts = ip.split(".")
                        base = ".".join(ip_parts[:3])
                        return (f"{base}.0", f"{base}.255", org, f"{base}.0/24")

        except Exception as e:
            print(f"⚠️ WHOIS lookup failed: {e}")

        # Fallback: scan around the IP
        ip_parts = ip.split(".")
        base = ".".join(ip_parts[:3])
        start = max(0, int(ip_parts[3]) - self.scan_range // 2)
        end = min(255, start + self.scan_range)
        return (f"{base}.{start}", f"{base}.{end}", "Unknown", f"{base}.0/24")

    async def _get_asn_prefixes(self, ip: str) -> list:
        """Get all IP prefixes announced by the organization's ASN."""
        prefixes = []

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                # Use BGPView API for ASN prefixes
                # First get ASN
                url = f"https://api.bgpview.io/ip/{ip}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("status") == "ok":
                            for prefix in data.get("data", {}).get("prefixes", []):
                                cidr = prefix.get("prefix")
                                asn = prefix.get("asn", {}).get("asn")
                                name = prefix.get("asn", {}).get("name", "")
                                if cidr:
                                    prefixes.append(
                                        {"cidr": cidr, "asn": asn, "name": name}
                                    )
                                    print(f"📡 Found prefix: {cidr} (AS{asn} - {name})")
        except Exception as e:
            print(f"⚠️ ASN lookup failed: {e}")

        return prefixes

    async def scan_domain(self, domain: str) -> RangeScanResult:
        """
        Scan IP range for a domain.

        1. Resolve domain to IP
        2. Get organization's network via ASN lookup
        3. Scan each IP for HTTP services
        4. Check for chat endpoints
        """
        # Clean domain
        if domain.startswith(("http://", "https://")):
            domain = urlparse(domain).netloc
        domain = domain.split("/")[0]

        print(f"🔍 Scanning IP range for {domain}")

        # Step 1: DNS lookup
        try:
            ip = socket.gethostbyname(domain)
            print(f"📍 Resolved {domain} → {ip}")
        except socket.gaierror as e:
            print(f"❌ DNS resolution failed: {e}")
            return RangeScanResult(
                domain=domain, base_ip="", cidr="", total_scanned=0, hosts_found=0
            )

        # Step 2: Get organization's network via ASN lookup
        ip_parts = ip.split(".")
        base_ip = ".".join(ip_parts[:3])

        if self.auto_detect_range:
            prefixes = await self._get_asn_prefixes(ip)
            if prefixes:
                # Use the smallest prefix that contains our IP
                # For now, just use the first one
                cidr = prefixes[0]["cidr"]
                org_name = prefixes[0].get("name", "Unknown")
                print(f"🏢 Organization: {org_name}")
                print(f"📡 Network prefix: {cidr}")

                # Parse CIDR to get range
                # e.g., "94.124.200.0/24" -> scan .0 to .255
                try:
                    prefix_ip, prefix_len = cidr.split("/")
                    prefix_len = int(prefix_len)
                    prefix_parts = prefix_ip.split(".")

                    if prefix_len >= 24:
                        # /24 or smaller - scan full subnet
                        base_ip = ".".join(prefix_parts[:3])
                        start_octet = 1  # Skip .0
                        end_octet = 254  # Skip .255
                    else:
                        # Larger than /24 - limit to /24 around target
                        start_octet = max(1, int(ip_parts[3]) - 127)
                        end_octet = min(254, start_octet + 253)
                except Exception:
                    start_octet = max(0, int(ip_parts[3]) - self.scan_range // 2)
                    end_octet = min(255, start_octet + self.scan_range)
                    cidr = f"{base_ip}.0/24"
            else:
                # Fallback to simple range
                start_octet = max(0, int(ip_parts[3]) - self.scan_range // 2)
                end_octet = min(255, start_octet + self.scan_range)
                cidr = f"{base_ip}.0/24"
        else:
            # Manual range
            start_octet = max(0, int(ip_parts[3]) - self.scan_range // 2)
            end_octet = min(255, start_octet + self.scan_range)
            cidr = f"{base_ip}.0/24"

        total_ips = end_octet - start_octet
        print(f"🌐 Scan range: {base_ip}.{start_octet}-{end_octet} ({total_ips} IPs)")

        if self.proxy_url:
            print("⚠️  Proxy mode: scanning is slower, please wait...")

        # Step 3: Scan IPs concurrently with progress
        hosts: List[DiscoveredHost] = []
        semaphore = asyncio.Semaphore(self.max_concurrent)
        scanned_count = [0]  # Use list for mutable counter

        async def scan_ip(last_octet: int):
            target_ip = f"{base_ip}.{last_octet}"
            async with semaphore:
                host = await self._scan_single_ip(target_ip)
                scanned_count[0] += 1

                # Progress update every IP
                progress = (scanned_count[0] / total_ips) * 100
                status = (
                    f"⏳ Progress: {scanned_count[0]}/{total_ips} ({progress:.0f}%)"
                )
                if host and (host.has_http or host.has_https):
                    hosts.append(host)
                    print(f"✅ Found: {target_ip} | {status}")
                elif scanned_count[0] % 4 == 0:  # Update every 4th scan
                    print(f"   Scanning {target_ip}... | {status}", end="\r")

        tasks = [scan_ip(i) for i in range(start_octet, end_octet)]
        await asyncio.gather(*tasks, return_exceptions=True)

        print(f"\n✅ IP scan complete: {len(hosts)} hosts found")

        # Step 4: Discover all endpoints on found hosts
        all_endpoints = []
        endpoints_by_cat: Dict[str, List[str]] = {}

        if hosts:
            print(f"🔍 Discovering endpoints on {len(hosts)} hosts...")

        for i, host in enumerate(hosts):
            print(f"   Host {i+1}/{len(hosts)}: {host.ip}")
            found = await self._discover_endpoints(host)
            host.endpoints = found
            all_endpoints.extend(found)

            # Group by category
            for ep in found:
                if ep.category not in endpoints_by_cat:
                    endpoints_by_cat[ep.category] = []
                endpoints_by_cat[ep.category].append(ep.url)

        result = RangeScanResult(
            domain=domain,
            base_ip=ip,
            cidr=cidr,
            total_scanned=total_ips,
            hosts_found=len(hosts),
            hosts=hosts,
            endpoints_by_category=endpoints_by_cat,
            all_endpoints=all_endpoints,
        )

        # Summary by category
        print("\n📊 Scan Summary:")
        print(f"   Hosts: {result.hosts_found}")
        print(f"   Total endpoints: {len(all_endpoints)}")
        for cat, eps in endpoints_by_cat.items():
            icon = {
                "chat": "💬",
                "api": "🔌",
                "admin": "🔐",
                "auth": "🔑",
                "files": "📁",
                "webhooks": "🪝",
                "internal": "🔧",
                "ai_ml": "🤖",
            }.get(cat, "📍")
            print(f"   {icon} {cat}: {len(eps)}")

        return result

    async def _scan_single_ip(self, ip: str) -> Optional[DiscoveredHost]:
        """Scan a single IP for HTTP services."""
        host = DiscoveredHost(ip=ip)

        # Try reverse DNS
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            host.hostname = hostname
        except (socket.herror, socket.gaierror):
            pass

        # Check common ports
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(ssl=False),
        ) as session:
            for port in self.WEB_PORTS:
                for scheme in ["https", "http"]:
                    if port == 80 and scheme == "https":
                        continue
                    if port == 443 and scheme == "http":
                        continue

                    url = f"{scheme}://{ip}:{port}/"
                    try:
                        async with session.get(
                            url, proxy=self.proxy_url, allow_redirects=False
                        ) as resp:
                            if resp.status < 500:
                                host.ports.append(port)
                                host.services[port] = scheme
                                if scheme == "http":
                                    host.has_http = True
                                else:
                                    host.has_https = True

                                # Get server header
                                server = resp.headers.get("Server", "")
                                if server:
                                    host.services[port] = f"{scheme} ({server})"
                                break  # Found on this port
                    except Exception:
                        continue

        return host if host.ports else None

    async def _discover_endpoints(
        self, host: DiscoveredHost
    ) -> List[DiscoveredEndpoint]:
        """Discover all interesting endpoints on a host."""
        found = []

        # Build base URLs
        base_urls = []
        for port, scheme_info in host.services.items():
            scheme = "https" if "https" in scheme_info else "http"
            if host.hostname:
                base_urls.append(f"{scheme}://{host.hostname}")
            base_urls.append(f"{scheme}://{host.ip}:{port}")

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            connector=aiohttp.TCPConnector(ssl=False),
        ) as session:
            for base_url in base_urls[:2]:  # Limit to 2 base URLs per host
                for category, paths in self.DISCOVERY_PATHS.items():
                    for path in paths:
                        url = f"{base_url}{path}"
                        try:
                            async with session.get(
                                url, proxy=self.proxy_url, allow_redirects=False
                            ) as resp:
                                # Interesting responses
                                if resp.status in [200, 401, 403, 405]:
                                    ct = resp.headers.get("Content-Type", "")
                                    ep = DiscoveredEndpoint(
                                        url=url,
                                        category=category,
                                        status_code=resp.status,
                                        content_type=ct,
                                    )
                                    found.append(ep)
                                    icon = {
                                        "chat": "💬",
                                        "api": "🔌",
                                        "admin": "🔐",
                                        "auth": "🔑",
                                        "files": "📁",
                                        "webhooks": "🪝",
                                        "internal": "🔧",
                                        "ai_ml": "🤖",
                                    }.get(category, "📍")
                                    print(f"  {icon} {category}: {url}")
                        except Exception:
                            continue

        return found

    def get_summary(self) -> Dict:
        """Get scanner summary."""
        return {
            "scan_range": self.scan_range,
            "timeout": self.timeout,
            "proxy_enabled": bool(self.proxy_url),
        }


async def scan_company_range(domain: str, proxy_url: str = None) -> RangeScanResult:
    """
    Convenience function to scan company IP range.

    Args:
        domain: Target domain (e.g., "hh.ru")
        proxy_url: Optional proxy URL for ScraperAPI

    Returns:
        RangeScanResult with discovered hosts and endpoints
    """
    scanner = IPRangeScanner(proxy_url=proxy_url)
    result = await scanner.scan_domain(domain)

    print(f"\n📊 IP Range Scan Results for {domain}")
    print("=" * 50)
    print(f"Base IP: {result.base_ip}")
    print(f"Range: {result.cidr}")
    print(f"Scanned: {result.total_scanned} IPs")
    print(f"Hosts found: {result.hosts_found}")

    if result.hosts:
        print(f"\n🖥️ Discovered Hosts:")
        for host in result.hosts:
            hostname = f" ({host.hostname})" if host.hostname else ""
            print(f"  {host.ip}{hostname}")
            print(f"    Ports: {host.ports}")
            if host.chat_endpoints:
                print(f"    Chat endpoints: {len(host.chat_endpoints)}")

    if result.chat_endpoints:
        print(f"\n🎯 Chat Endpoints Found:")
        for ep in result.chat_endpoints:
            print(f"  {ep}")

    return result


# CLI
if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python ip_range_scanner.py <domain>")
        sys.exit(1)

    target = sys.argv[1]

    # Get ScraperAPI key if available
    api_key = os.environ.get("SCRAPERAPI_KEY", "")
    proxy = None
    if api_key:
        proxy = f"http://scraperapi:{api_key}@proxy-server.scraperapi.com:8001"
        print(f"🏠 Using ScraperAPI proxy")

    asyncio.run(scan_company_range(target, proxy))
