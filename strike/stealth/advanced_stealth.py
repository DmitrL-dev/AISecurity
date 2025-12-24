#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Advanced Stealth Engine

Complete invisibility against modern detection systems (2025):

🔍 DETECTION METHODS WE EVADE:
================================

1. TLS FINGERPRINTING (JA3/JA4/JA4+)
   - Every TLS client has unique cipher suite ordering
   - Python/aiohttp has distinct fingerprint
   - Solution: TLS fingerprint spoofing, use curl_cffi with browser impersonation

2. HTTP/2 FINGERPRINTING (Akamai h2 fingerprint)
   - SETTINGS frame ordering, WINDOW_UPDATE size
   - Solution: Mimic real browser h2 behavior

3. BEHAVIORAL ML ANALYSIS
   - Request timing patterns (too regular = bot)
   - Request ordering (sequential = bot)
   - Mouse/keyboard patterns (for browser)
   - Solution: Human-like timing jitter, random ordering

4. BOT MANAGEMENT SYSTEMS
   - Akamai Bot Manager
   - PerimeterX (HUMAN Security)
   - DataDome
   - Cloudflare Bot Management
   - Solution: Browser automation with undetected-chromedriver

5. IP REPUTATION & ASN ANALYSIS
   - Known VPN/proxy IPs are blacklisted
   - Datacenter ASNs get higher scrutiny
   - Solution: Residential proxies, mobile IPs

6. HEADER ORDER FINGERPRINTING
   - Chrome vs Firefox vs Safari have different header order
   - Solution: Browser-specific header ordering

7. TCP/IP FINGERPRINTING (p0f)
   - TTL, window size, DF bit, etc.
   - Solution: VPN tunneling, correct OS emulation

8. JAVASCRIPT CHALLENGES
   - Cloudflare JS challenge
   - Browser integrity checks
   - Solution: Real browser with stealth patches

9. CANVAS/WEBGL FINGERPRINTING
   - Unique per-browser/GPU
   - Solution: Canvas noise injection

10. DNS ANALYSIS
    - Reverse DNS lookup
    - ASN lookup
    - Solution: Clean residential IPs

IMPLEMENTATION:
===============
- curl_cffi for TLS impersonation (Chrome/Firefox/Safari)
- Human-like timing with Poisson distribution
- Browser automation with undetected-chromedriver/playwright-stealth
- Request ordering randomization
- Header order matching real browsers
- Residential proxy support
"""

import asyncio
import random
import time
import hashlib
import platform
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from pathlib import Path
import math


# ============================================================================
# BROWSER PROFILES
# ============================================================================

class BrowserProfile(Enum):
    """Browser profiles for impersonation."""
    CHROME_WIN = "chrome_win"
    CHROME_MAC = "chrome_mac"
    CHROME_LINUX = "chrome_linux"
    FIREFOX_WIN = "firefox_win"
    FIREFOX_MAC = "firefox_mac"
    SAFARI_MAC = "safari_mac"
    EDGE_WIN = "edge_win"
    CHROME_ANDROID = "chrome_android"
    SAFARI_IOS = "safari_ios"


# Browser-specific header ordering (CRITICAL for fingerprint evasion)
BROWSER_HEADER_ORDER = {
    BrowserProfile.CHROME_WIN: [
        "Host", "Connection", "Cache-Control", "sec-ch-ua", "sec-ch-ua-mobile",
        "sec-ch-ua-platform", "Upgrade-Insecure-Requests", "User-Agent", "Accept",
        "Sec-Fetch-Site", "Sec-Fetch-Mode", "Sec-Fetch-User", "Sec-Fetch-Dest",
        "Accept-Encoding", "Accept-Language", "Cookie",
    ],
    BrowserProfile.FIREFOX_WIN: [
        "Host", "User-Agent", "Accept", "Accept-Language", "Accept-Encoding",
        "Connection", "Upgrade-Insecure-Requests", "Sec-Fetch-Dest",
        "Sec-Fetch-Mode", "Sec-Fetch-Site", "Sec-Fetch-User", "Cookie",
    ],
    BrowserProfile.SAFARI_MAC: [
        "Host", "Accept", "Accept-Language", "Accept-Encoding", "Connection",
        "User-Agent", "Upgrade-Insecure-Requests", "Cookie",
    ],
}

# JA3 fingerprints for different browsers (for reference)
JA3_FINGERPRINTS = {
    "chrome_120": "771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0",
    "firefox_121": "771,4865-4867-4866-49195-49199-52393-52392-49196-49200-49162-49161-49171-49172-156-157-47-53,0-23-65281-10-11-35-16-5-34-51-43-13-45-28-21,29-23-24-25-256-257,0",
    "safari_17": "771,4866-4867-4865-49196-49200-159-52393-158-52392-49325-49195-49199-107-106,0-23-65281-10-11-16-5-13-51-45-43-27,29-23-24-25,0",
}

# User-Agent strings for different browsers (2025 versions)
USER_AGENTS = {
    BrowserProfile.CHROME_WIN: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ],
    BrowserProfile.CHROME_MAC: [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    ],
    BrowserProfile.FIREFOX_WIN: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    ],
    BrowserProfile.SAFARI_MAC: [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    ],
    BrowserProfile.EDGE_WIN: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ],
    BrowserProfile.CHROME_ANDROID: [
        "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ],
    BrowserProfile.SAFARI_IOS: [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    ],
}

# Client hints for Chrome (sec-ch-ua)
CLIENT_HINTS = {
    BrowserProfile.CHROME_WIN: {
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    },
    BrowserProfile.CHROME_MAC: {
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    },
    BrowserProfile.EDGE_WIN: {
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    },
}


# ============================================================================
# TIMING PATTERNS
# ============================================================================

class HumanTiming:
    """
    Generate human-like timing patterns.

    Bots are detected by:
    - Regular intervals between requests
    - No variation in timing
    - Unnaturally fast responses

    Humans have:
    - Variable timing (Poisson/Log-normal distribution)
    - Reading time between requests
    - Occasional long pauses
    - Faster responses for simple actions
    """

    def __init__(self, base_delay: float = 1.0, human_factor: float = 1.0):
        self.base_delay = base_delay
        self.human_factor = human_factor
        self.request_count = 0
        self.session_start = time.time()

        # Simulate reading/thinking time
        self.reading_speeds = {
            "fast": (0.5, 1.5),    # Quick scan
            "normal": (1.5, 4.0),  # Normal reading
            "slow": (4.0, 10.0),   # Detailed reading
        }

    def get_delay(self, action_type: str = "normal") -> float:
        """
        Get human-like delay based on action type.

        Uses log-normal distribution which matches human reaction times.
        """
        self.request_count += 1

        # Base delay from log-normal distribution (matches human timing)
        mu = math.log(self.base_delay)
        sigma = 0.5 * self.human_factor
        delay = random.lognormvariate(mu, sigma)

        # Occasional long pause (reading, distraction)
        if random.random() < 0.1:  # 10% chance
            delay += random.uniform(3.0, 8.0)

        # Very occasional very long pause (coffee break simulation)
        if random.random() < 0.02:  # 2% chance
            delay += random.uniform(15.0, 30.0)

        # Faster for sequential actions
        if action_type == "fast":
            delay *= 0.5
        elif action_type == "slow":
            delay *= 2.0

        # Minimum delay to avoid detection
        return max(0.3, delay)

    def get_burst_pattern(self, count: int) -> List[float]:
        """
        Generate a burst of requests with human timing.
        Simulates browsing a page with multiple resources.
        """
        delays = []

        for i in range(count):
            if i < 3:
                # First few requests are fast (parallel loading)
                delays.append(random.uniform(0.1, 0.3))
            else:
                # Later requests have more variance
                delays.append(self.get_delay("fast"))

        return delays

    def get_session_decay(self) -> float:
        """
        Simulate session fatigue - longer delays over time.
        """
        session_duration = time.time() - self.session_start
        fatigue_factor = 1.0 + (session_duration /
                                3600.0) * 0.5  # +50% per hour
        return fatigue_factor


# ============================================================================
# REQUEST ORDERING
# ============================================================================

class RequestOrderer:
    """
    Randomize request ordering to avoid ML detection.

    Sequential testing is a dead giveaway:
    - /login?id=1
    - /login?id=2
    - /login?id=3

    Human browsing is random:
    - /home
    - /products/123
    - /about
    - /products/456
    """

    def __init__(self):
        self.request_history = []
        self.last_path = None

    def shuffle_payloads(self, payloads: List[str]) -> List[str]:
        """Shuffle payloads to avoid sequential patterns."""
        shuffled = payloads.copy()
        random.shuffle(shuffled)
        return shuffled

    def intersperse_with_noise(
        self,
        attack_requests: List[str],
        noise_ratio: float = 0.3
    ) -> List[Tuple[str, bool]]:
        """
        Intersperse attack requests with legitimate-looking noise.

        Returns list of (url, is_attack) tuples.
        """
        result = []

        # Common legitimate pages to visit
        noise_pages = [
            "/", "/about", "/contact", "/products", "/services",
            "/blog", "/faq", "/privacy", "/terms", "/sitemap.xml",
            "/robots.txt", "/favicon.ico", "/css/style.css", "/js/main.js",
        ]

        for attack in attack_requests:
            result.append((attack, True))

            # Add noise after some attacks
            if random.random() < noise_ratio:
                noise = random.choice(noise_pages)
                result.append((noise, False))

        return result

    def add_reconnaissance_pattern(self, base_url: str) -> List[str]:
        """
        Generate reconnaissance requests that look like normal browsing.
        """
        return [
            base_url + "/",
            base_url + "/robots.txt",
            base_url + "/sitemap.xml",
            base_url + "/favicon.ico",
            base_url + "/about",
        ]


# ============================================================================
# TLS FINGERPRINT EVASION
# ============================================================================

class TLSEvasion:
    """
    Evade TLS fingerprinting (JA3/JA4).

    For full evasion, we need curl_cffi which can impersonate
    real browsers at the TLS level.

    This class provides fallback methods for when curl_cffi is not available.
    """

    def __init__(self):
        self.curl_cffi_available = self._check_curl_cffi()

    def _check_curl_cffi(self) -> bool:
        """Check if curl_cffi is available."""
        try:
            import curl_cffi
            return True
        except ImportError:
            return False

    def get_session(self, browser: BrowserProfile = BrowserProfile.CHROME_WIN):
        """
        Get HTTP session with browser TLS impersonation.

        Uses curl_cffi if available, otherwise returns instructions.
        """
        if self.curl_cffi_available:
            from curl_cffi.requests import Session

            # Map to curl_cffi browser names
            browser_map = {
                BrowserProfile.CHROME_WIN: "chrome120",
                BrowserProfile.CHROME_MAC: "chrome120",
                BrowserProfile.FIREFOX_WIN: "firefox121",
                BrowserProfile.SAFARI_MAC: "safari17_0",
                BrowserProfile.EDGE_WIN: "edge120",
            }

            impersonate = browser_map.get(browser, "chrome120")
            return Session(impersonate=impersonate)

        return None

    @staticmethod
    def get_installation_instructions() -> str:
        """Get instructions for installing curl_cffi."""
        return """
To enable TLS fingerprint evasion, install curl_cffi:

    pip install curl_cffi

This allows impersonating real browsers at the TLS level,
making requests indistinguishable from Chrome/Firefox/Safari.
        """


# ============================================================================
# BROWSER AUTOMATION STEALTH
# ============================================================================

class BrowserStealth:
    """
    Stealth browser automation for JS challenges.

    Uses:
    - undetected-chromedriver (Chrome with stealth patches)
    - playwright-stealth (Playwright with anti-detection)

    Bypasses:
    - Cloudflare JS challenge
    - PerimeterX
    - DataDome
    - hCaptcha (with solver integration)
    """

    def __init__(self):
        self.uc_available = self._check_undetected_chromedriver()
        self.playwright_available = self._check_playwright()

    def _check_undetected_chromedriver(self) -> bool:
        try:
            import undetected_chromedriver
            return True
        except ImportError:
            return False

    def _check_playwright(self) -> bool:
        try:
            import playwright
            return True
        except ImportError:
            return False

    async def get_stealth_browser(self):
        """Get a stealth browser instance."""
        if self.uc_available:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            options.add_argument(
                "--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")

            driver = uc.Chrome(options=options)
            return driver

        return None

    @staticmethod
    def get_stealth_scripts() -> Dict[str, str]:
        """
        JavaScript to inject for additional stealth.
        """
        return {
            "webdriver_spoof": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """,
            "chrome_runtime": """
                window.chrome = {
                    runtime: {}
                };
            """,
            "permissions_spoof": """
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """,
            "plugins_spoof": """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {name: 'Chrome PDF Plugin'},
                        {name: 'Chrome PDF Viewer'},
                        {name: 'Native Client'}
                    ]
                });
            """,
            "languages_spoof": """
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """,
        }


# ============================================================================
# IP REPUTATION MANAGEMENT
# ============================================================================

class IPReputation:
    """
    Manage IP reputation to avoid blacklists.

    Types of IPs ranked by trustworthiness:
    1. Residential IPs (most trusted)
    2. Mobile IPs (very trusted, dynamic)
    3. ISP IPs (trusted)
    4. Hosting/VPS IPs (suspicious)
    5. Known proxy/VPN IPs (blocked)
    6. Tor exit nodes (blocked)
    """

    # Known proxy/VPN detection APIs and their checks
    REPUTATION_CHECKS = [
        "https://ipinfo.io/{ip}/json",
        "https://ip-api.com/json/{ip}",
    ]

    # Known datacenter ASNs (higher scrutiny)
    DATACENTER_ASNS = [
        "AS14061",  # DigitalOcean
        "AS16509",  # Amazon AWS
        "AS15169",  # Google Cloud
        "AS8075",   # Microsoft Azure
        "AS14618",  # Amazon EC2
        "AS13335",  # Cloudflare
        "AS20473",  # Vultr
        "AS63949",  # Linode
        "AS19551",  # Incapsula
        "AS398101",  # Zscaler
    ]

    def __init__(self):
        self.ip_history = []
        self.blocked_ips = set()

    def is_datacenter_ip(self, asn: str) -> bool:
        """Check if IP belongs to datacenter ASN."""
        return any(dc in asn for dc in self.DATACENTER_ASNS)

    def get_residential_proxy_services(self) -> Dict[str, str]:
        """
        List of residential proxy services for stealth.
        Using residential IPs makes detection much harder.
        """
        return {
            "brightdata": "Bright Data (formerly Luminati) - top tier residential",
            "smartproxy": "Smartproxy - good residential pool",
            "oxylabs": "Oxylabs - large residential network",
            "iproyal": "IPRoyal - affordable residential",
            "soax": "SOAX - rotating residential",
            "webshare": "Webshare - mixed residential/datacenter",
        }

    def estimate_ip_risk(self, ip_info: Dict) -> float:
        """
        Estimate risk level of an IP being blocked.

        Returns 0.0 (safest) to 1.0 (definitely blocked).
        """
        risk = 0.0

        # Datacenter = high risk
        if ip_info.get("org", "").lower().find("hosting") != -1:
            risk += 0.4
        if ip_info.get("org", "").lower().find("cloud") != -1:
            risk += 0.3
        if ip_info.get("org", "").lower().find("vps") != -1:
            risk += 0.4

        # Known VPN = very high risk
        if "vpn" in ip_info.get("org", "").lower():
            risk += 0.5

        # Tor exit node = blocked
        if ip_info.get("is_tor", False):
            risk = 1.0

        # Proxy = high risk
        if ip_info.get("proxy", False):
            risk += 0.5

        return min(1.0, risk)


# ============================================================================
# ADVANCED STEALTH SESSION
# ============================================================================

@dataclass
class StealthConfig:
    """Configuration for stealth session."""
    browser_profile: BrowserProfile = BrowserProfile.CHROME_WIN
    use_tls_impersonation: bool = True
    use_residential_proxy: bool = False
    residential_proxy_url: Optional[str] = None
    human_timing: bool = True
    timing_base_delay: float = 1.5
    request_randomization: bool = True
    noise_ratio: float = 0.2
    rotate_fingerprint: bool = True
    fingerprint_rotation_interval: int = 50  # requests


class AdvancedStealthSession:
    """
    Ultimate stealth session combining all techniques.
    """

    def __init__(self, config: StealthConfig = None):
        self.config = config or StealthConfig()

        self.timing = HumanTiming(
            base_delay=self.config.timing_base_delay,
            human_factor=1.0
        )
        self.orderer = RequestOrderer()
        self.tls_evasion = TLSEvasion()
        self.ip_reputation = IPReputation()

        self.request_count = 0
        self.current_profile = self.config.browser_profile
        self.session_id = hashlib.md5(
            str(time.time()).encode()).hexdigest()[:8]

        # Tracking
        self.blocks_detected = 0
        self.fingerprint_rotations = 0

    def get_headers(self) -> Dict[str, str]:
        """Get browser-accurate headers with correct ordering."""
        profile = self.current_profile

        headers = {
            "User-Agent": random.choice(USER_AGENTS.get(profile, USER_AGENTS[BrowserProfile.CHROME_WIN])),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }

        # Add client hints for Chrome
        if profile in CLIENT_HINTS:
            headers.update(CLIENT_HINTS[profile])

        return headers

    def get_ordered_headers(self, headers: Dict[str, str]) -> List[Tuple[str, str]]:
        """Get headers in browser-specific order."""
        profile = self.current_profile
        order = BROWSER_HEADER_ORDER.get(
            profile, BROWSER_HEADER_ORDER[BrowserProfile.CHROME_WIN])

        ordered = []

        # Add headers in correct order
        for key in order:
            if key in headers:
                ordered.append((key, headers[key]))

        # Add remaining headers
        for key, value in headers.items():
            if key not in order:
                ordered.append((key, value))

        return ordered

    async def get_delay(self) -> float:
        """Get human-like delay before next request."""
        if not self.config.human_timing:
            return 0.1

        delay = self.timing.get_delay()
        fatigue = self.timing.get_session_decay()

        return delay * fatigue

    def should_rotate_fingerprint(self) -> bool:
        """Check if we should rotate browser fingerprint."""
        if not self.config.rotate_fingerprint:
            return False

        return self.request_count % self.config.fingerprint_rotation_interval == 0

    def rotate_fingerprint(self):
        """Rotate to a new browser fingerprint."""
        profiles = list(BrowserProfile)
        profiles.remove(self.current_profile)
        self.current_profile = random.choice(profiles)
        self.fingerprint_rotations += 1
        print(f"   🔄 Rotated fingerprint to: {self.current_profile.value}")

    def get_stats(self) -> Dict:
        """Get session statistics."""
        return {
            "session_id": self.session_id,
            "requests": self.request_count,
            "blocks_detected": self.blocks_detected,
            "fingerprint_rotations": self.fingerprint_rotations,
            "current_profile": self.current_profile.value,
            "tls_impersonation": self.tls_evasion.curl_cffi_available,
        }


# ============================================================================
# DEMO
# ============================================================================

def demo():
    """Demonstrate advanced stealth capabilities."""
    print("=" * 60)
    print("🥷 SENTINEL Strike — Advanced Stealth Engine")
    print("=" * 60)

    # Initialize
    config = StealthConfig(
        browser_profile=BrowserProfile.CHROME_WIN,
        human_timing=True,
        timing_base_delay=1.5,
    )

    session = AdvancedStealthSession(config)

    print("\n📊 Stealth Capabilities:")
    print("-" * 40)

    # TLS Evasion
    tls = TLSEvasion()
    print(
        f"   TLS Impersonation (curl_cffi): {'✅' if tls.curl_cffi_available else '❌ Not installed'}")

    # Browser Stealth
    browser = BrowserStealth()
    print(
        f"   Undetected ChromeDriver: {'✅' if browser.uc_available else '❌ Not installed'}")
    print(
        f"   Playwright Stealth: {'✅' if browser.playwright_available else '❌ Not installed'}")

    # Headers
    print(f"\n🔐 Browser Fingerprint: {session.current_profile.value}")
    headers = session.get_headers()
    print(f"   User-Agent: {headers['User-Agent'][:50]}...")

    # Timing
    print(f"\n⏱️ Human Timing Samples:")
    timing = HumanTiming(base_delay=1.0)
    for i in range(5):
        delay = timing.get_delay()
        print(f"   Request {i+1}: {delay:.2f}s delay")

    # IP Reputation
    print(f"\n🌐 Recommended Proxy Types:")
    ip_rep = IPReputation()
    for service, desc in list(ip_rep.get_residential_proxy_services().items())[:3]:
        print(f"   • {service}: {desc}")

    print("\n" + "=" * 60)
    print("✅ Advanced Stealth Engine ready")
    print("\n💡 For maximum stealth, install:")
    print("   pip install curl_cffi undetected-chromedriver playwright")


if __name__ == "__main__":
    demo()
