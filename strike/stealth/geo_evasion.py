#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Geo IP Evasion & Location Spoofing

Bypass geographic restrictions and appear from target regions:
- Geo IP blocking bypass
- Country-specific proxy routing
- Timezone spoofing
- Language/locale matching
- Accept-Language header matching
- Currency/region detection bypass
"""

import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# GEO REGIONS
# ============================================================================

class GeoRegion(Enum):
    """Geographic regions for targeting."""
    # Europe
    EUROPE_WEST = "europe_west"
    EUROPE_EAST = "europe_east"
    EUROPE_NORTH = "europe_north"
    # Americas
    USA_EAST = "usa_east"
    USA_WEST = "usa_west"
    CANADA = "canada"
    LATAM = "latam"
    # Asia Pacific
    ASIA_EAST = "asia_east"
    ASIA_SOUTHEAST = "asia_southeast"
    OCEANIA = "oceania"
    INDIA = "india"
    # Middle East & Africa
    MIDDLE_EAST = "middle_east"
    AFRICA = "africa"
    # Russia & CIS
    RUSSIA = "russia"
    CIS = "cis"


# ============================================================================
# COUNTRY DATA
# ============================================================================

@dataclass
class CountryProfile:
    """Profile for a specific country."""
    code: str  # ISO 3166-1 alpha-2
    name: str
    region: GeoRegion
    timezone: str
    language: str
    accept_language: str
    currency: str
    keyboard_layout: str = "en-US"


# Major countries with full profiles
COUNTRY_PROFILES: Dict[str, CountryProfile] = {
    # USA
    "US": CountryProfile(
        code="US", name="United States", region=GeoRegion.USA_EAST,
        timezone="America/New_York", language="en-US",
        accept_language="en-US,en;q=0.9", currency="USD",
        keyboard_layout="en-US",
    ),
    "US-CA": CountryProfile(
        code="US", name="United States (California)", region=GeoRegion.USA_WEST,
        timezone="America/Los_Angeles", language="en-US",
        accept_language="en-US,en;q=0.9", currency="USD",
    ),
    # UK
    "GB": CountryProfile(
        code="GB", name="United Kingdom", region=GeoRegion.EUROPE_WEST,
        timezone="Europe/London", language="en-GB",
        accept_language="en-GB,en;q=0.9", currency="GBP",
        keyboard_layout="en-GB",
    ),
    # Germany
    "DE": CountryProfile(
        code="DE", name="Germany", region=GeoRegion.EUROPE_WEST,
        timezone="Europe/Berlin", language="de-DE",
        accept_language="de-DE,de;q=0.9,en;q=0.8", currency="EUR",
        keyboard_layout="de-DE",
    ),
    # France
    "FR": CountryProfile(
        code="FR", name="France", region=GeoRegion.EUROPE_WEST,
        timezone="Europe/Paris", language="fr-FR",
        accept_language="fr-FR,fr;q=0.9,en;q=0.8", currency="EUR",
        keyboard_layout="fr-FR",
    ),
    # Netherlands
    "NL": CountryProfile(
        code="NL", name="Netherlands", region=GeoRegion.EUROPE_WEST,
        timezone="Europe/Amsterdam", language="nl-NL",
        accept_language="nl-NL,nl;q=0.9,en;q=0.8", currency="EUR",
    ),
    # Russia
    "RU": CountryProfile(
        code="RU", name="Russia", region=GeoRegion.RUSSIA,
        timezone="Europe/Moscow", language="ru-RU",
        accept_language="ru-RU,ru;q=0.9,en;q=0.8", currency="RUB",
        keyboard_layout="ru-RU",
    ),
    # Japan
    "JP": CountryProfile(
        code="JP", name="Japan", region=GeoRegion.ASIA_EAST,
        timezone="Asia/Tokyo", language="ja-JP",
        accept_language="ja-JP,ja;q=0.9,en;q=0.8", currency="JPY",
        keyboard_layout="ja-JP",
    ),
    # China
    "CN": CountryProfile(
        code="CN", name="China", region=GeoRegion.ASIA_EAST,
        timezone="Asia/Shanghai", language="zh-CN",
        accept_language="zh-CN,zh;q=0.9,en;q=0.8", currency="CNY",
        keyboard_layout="zh-CN",
    ),
    # South Korea
    "KR": CountryProfile(
        code="KR", name="South Korea", region=GeoRegion.ASIA_EAST,
        timezone="Asia/Seoul", language="ko-KR",
        accept_language="ko-KR,ko;q=0.9,en;q=0.8", currency="KRW",
    ),
    # India
    "IN": CountryProfile(
        code="IN", name="India", region=GeoRegion.INDIA,
        timezone="Asia/Kolkata", language="en-IN",
        accept_language="en-IN,en;q=0.9,hi;q=0.8", currency="INR",
    ),
    # Australia
    "AU": CountryProfile(
        code="AU", name="Australia", region=GeoRegion.OCEANIA,
        timezone="Australia/Sydney", language="en-AU",
        accept_language="en-AU,en;q=0.9", currency="AUD",
    ),
    # Brazil
    "BR": CountryProfile(
        code="BR", name="Brazil", region=GeoRegion.LATAM,
        timezone="America/Sao_Paulo", language="pt-BR",
        accept_language="pt-BR,pt;q=0.9,en;q=0.8", currency="BRL",
    ),
    # Singapore
    "SG": CountryProfile(
        code="SG", name="Singapore", region=GeoRegion.ASIA_SOUTHEAST,
        timezone="Asia/Singapore", language="en-SG",
        accept_language="en-SG,en;q=0.9,zh;q=0.8", currency="SGD",
    ),
    # UAE
    "AE": CountryProfile(
        code="AE", name="UAE", region=GeoRegion.MIDDLE_EAST,
        timezone="Asia/Dubai", language="ar-AE",
        accept_language="ar-AE,ar;q=0.9,en;q=0.8", currency="AED",
    ),
    # Israel
    "IL": CountryProfile(
        code="IL", name="Israel", region=GeoRegion.MIDDLE_EAST,
        timezone="Asia/Jerusalem", language="he-IL",
        accept_language="he-IL,he;q=0.9,en;q=0.8", currency="ILS",
    ),
    # Turkey
    "TR": CountryProfile(
        code="TR", name="Turkey", region=GeoRegion.MIDDLE_EAST,
        timezone="Europe/Istanbul", language="tr-TR",
        accept_language="tr-TR,tr;q=0.9,en;q=0.8", currency="TRY",
    ),
    # Poland
    "PL": CountryProfile(
        code="PL", name="Poland", region=GeoRegion.EUROPE_EAST,
        timezone="Europe/Warsaw", language="pl-PL",
        accept_language="pl-PL,pl;q=0.9,en;q=0.8", currency="PLN",
    ),
    # Canada
    "CA": CountryProfile(
        code="CA", name="Canada", region=GeoRegion.CANADA,
        timezone="America/Toronto", language="en-CA",
        accept_language="en-CA,en;q=0.9,fr;q=0.8", currency="CAD",
    ),
}


# ============================================================================
# PROXY SERVERS BY COUNTRY
# ============================================================================

# ZooGVPN servers by country
ZOOGVPN_SERVERS = {
    "US": ["usa1.zgsocks.com:1080", "usa2.zgsocks.com:1080"],
    "GB": ["uk1.zgsocks.com:1080"],
    "DE": ["de1.zgsocks.com:1080"],
    "FR": ["fr1.zgsocks.com:1080"],
    "NL": ["nl1.zgsocks.com:1080"],
    "JP": ["jp1.zgsocks.com:1080"],
    "SG": ["sg1.zgsocks.com:1080"],
    "AU": ["au1.zgsocks.com:1080"],
    "CA": ["ca1.zgsocks.com:1080"],
    "IL": ["il1.zgsocks.com:1080"],
    "TR": ["tr1.zgsocks.com:1080"],
    "PL": ["pl1.zgsocks.com:1080"],
    "AT": ["at1.zgsocks.com:1080"],
    "BE": ["be1.zgsocks.com:1080"],
    "HK": ["hk1.zgsocks.com:1080"],
    "IT": ["it1.zgsocks.com:1080"],
}

# Residential proxy services with geo-targeting
RESIDENTIAL_PROXY_SERVICES = {
    "brightdata": {
        "url_template": "http://brd-customer-{customer}-zone-{zone}-country-{country}:{password}@zproxy.lum-superproxy.io:22225",
        "countries": ["all"],
        "type": "residential_rotating",
    },
    "smartproxy": {
        "url_template": "http://{username}:{password}@gate.smartproxy.com:7000",
        "geo_header": "X-Smartproxy-Geo",  # pass country code in header
        "countries": ["all"],
    },
    "oxylabs": {
        "url_template": "http://{username}:{password}@pr.oxylabs.io:7777",
        "geo_format": "customer-{username}-cc-{country}",
        "countries": ["all"],
    },
}


# ============================================================================
# GEO IP EVASION ENGINE
# ============================================================================

class GeoIPEvasion:
    """
    Bypass geographic IP restrictions.

    Capabilities:
    1. Route through country-specific proxies
    2. Match Accept-Language to geo
    3. Match timezone headers
    4. Consistent fingerprint per region
    5. Detect geo-blocking and auto-switch
    """

    def __init__(self, target_country: str = None):
        self.target_country = target_country
        self.current_profile: Optional[CountryProfile] = None
        self.available_proxies: Dict[str, List[str]] = ZOOGVPN_SERVERS.copy()
        self.used_countries: List[str] = []

        if target_country and target_country in COUNTRY_PROFILES:
            self.current_profile = COUNTRY_PROFILES[target_country]

    def detect_geo_blocking(self, response_text: str, status_code: int) -> Tuple[bool, Optional[str]]:
        """
        Detect if response indicates geo-blocking.

        Returns (is_blocked, blocked_reason)
        """
        geo_block_indicators = [
            "not available in your region",
            "not available in your country",
            "geo-restricted",
            "geographic restriction",
            "this content is not available",
            "access denied based on your location",
            "your country is not supported",
            "service unavailable in your area",
            "blocked in your region",
            "country blocked",
            "region blocked",
            "geo-blocked",
            "this website is not accessible",
            "we're sorry, but this service is unavailable in your country",
            "доступ ограничен",  # Russian: access restricted
            "服务在您的地区不可用",  # Chinese: service unavailable in your region
        ]

        text_lower = response_text.lower()

        for indicator in geo_block_indicators:
            if indicator in text_lower:
                return True, indicator

        # Status 451 = Unavailable For Legal Reasons (often geo-blocking)
        if status_code == 451:
            return True, "HTTP 451 - Unavailable For Legal Reasons"

        # 403 with specific geo-block patterns
        if status_code == 403:
            if any(geo in text_lower for geo in ["country", "region", "location", "geo"]):
                return True, "HTTP 403 with geo keywords"

        return False, None

    def get_proxy_for_country(self, country_code: str) -> Optional[str]:
        """Get a proxy server for specific country."""
        if country_code in self.available_proxies:
            servers = self.available_proxies[country_code]
            return random.choice(servers)
        return None

    def get_headers_for_country(self, country_code: str) -> Dict[str, str]:
        """Get headers that match the country's typical browser."""
        profile = COUNTRY_PROFILES.get(country_code)

        if not profile:
            # Default to US
            profile = COUNTRY_PROFILES["US"]

        headers = {
            "Accept-Language": profile.accept_language,
        }

        # Some sites check timezone via client hints
        # Note: This is typically set via JavaScript, included for completeness

        return headers

    def get_random_allowed_country(self, blocked_countries: List[str] = None) -> str:
        """Get a random country that isn't blocked."""
        blocked = set(blocked_countries or [])
        blocked.update(self.used_countries)

        available = [c for c in self.available_proxies.keys()
                     if c not in blocked]

        if not available:
            # Reset used countries if all tried
            self.used_countries = []
            available = list(self.available_proxies.keys())

        country = random.choice(available)
        self.used_countries.append(country)

        return country

    def get_country_for_target(self, target_domain: str) -> str:
        """
        Infer best country based on target domain TLD.

        Example: example.ru -> RU, example.de -> DE
        """
        tld_to_country = {
            ".ru": "RU",
            ".de": "DE",
            ".fr": "FR",
            ".jp": "JP",
            ".cn": "CN",
            ".uk": "GB",
            ".co.uk": "GB",
            ".au": "AU",
            ".br": "BR",
            ".in": "IN",
            ".it": "IT",
            ".es": "ES",
            ".nl": "NL",
            ".pl": "PL",
            ".kr": "KR",
            ".ca": "CA",
            ".sg": "SG",
            ".il": "IL",
            ".tr": "TR",
        }

        for tld, country in tld_to_country.items():
            if target_domain.endswith(tld):
                return country

        # Default to US for .com, .org, .net, etc.
        return "US"

    def get_residential_proxy_config(
        self,
        service: str,
        country: str,
        credentials: Dict[str, str]
    ) -> str:
        """
        Get residential proxy URL with geo-targeting.

        Args:
            service: One of 'brightdata', 'smartproxy', 'oxylabs'
            country: ISO country code
            credentials: Dict with 'username', 'password', optionally 'zone', 'customer'
        """
        config = RESIDENTIAL_PROXY_SERVICES.get(service)
        if not config:
            return None

        url_template = config["url_template"]

        return url_template.format(
            country=country.lower(),
            **credentials
        )


# ============================================================================
# GEO-AWARE STEALTH SESSION
# ============================================================================

class GeoStealthSession:
    """
    Stealth session with geographic awareness.

    Automatically:
    - Selects appropriate country for target
    - Routes through correct proxy
    - Sets matching language headers
    - Detects geo-blocking and switches countries
    """

    def __init__(self, target_domain: str = None):
        self.geo_evasion = GeoIPEvasion()
        self.target_domain = target_domain

        # Auto-detect best country for target
        if target_domain:
            best_country = self.geo_evasion.get_country_for_target(
                target_domain)
            self.current_country = best_country
        else:
            self.current_country = "US"

        self.blocked_countries: List[str] = []
        self.country_attempts = 0
        self.max_country_attempts = 10

    def get_proxy(self) -> Optional[str]:
        """Get proxy for current country."""
        return self.geo_evasion.get_proxy_for_country(self.current_country)

    def get_headers(self) -> Dict[str, str]:
        """Get headers matching current country."""
        return self.geo_evasion.get_headers_for_country(self.current_country)

    def handle_geo_block(self, response_text: str, status_code: int) -> bool:
        """
        Handle potential geo-blocking.

        Returns True if geo-block detected and country switched.
        """
        is_blocked, reason = self.geo_evasion.detect_geo_blocking(
            response_text, status_code)

        if is_blocked:
            print(f"   🌍 Geo-block detected: {reason}")
            self.blocked_countries.append(self.current_country)

            if self.country_attempts < self.max_country_attempts:
                new_country = self.geo_evasion.get_random_allowed_country(
                    self.blocked_countries)
                print(f"   🔄 Switching to: {new_country}")
                self.current_country = new_country
                self.country_attempts += 1
                return True
            else:
                print(f"   ⛔ Max country attempts reached")

        return False

    def get_stats(self) -> Dict:
        """Get session statistics."""
        return {
            "current_country": self.current_country,
            "blocked_countries": self.blocked_countries,
            "country_attempts": self.country_attempts,
        }


# ============================================================================
# DEMO
# ============================================================================

def demo():
    """Demonstrate Geo IP evasion."""
    print("=" * 60)
    print("🌍 SENTINEL Strike — Geo IP Evasion")
    print("=" * 60)

    geo = GeoIPEvasion()

    print("\n📍 Available Countries:")
    for code, servers in ZOOGVPN_SERVERS.items():
        profile = COUNTRY_PROFILES.get(code)
        name = profile.name if profile else code
        print(f"   {code}: {name} ({len(servers)} servers)")

    print("\n🎯 Country Detection Examples:")
    test_domains = [
        "example.ru",
        "example.de",
        "example.jp",
        "example.com",
    ]

    for domain in test_domains:
        country = geo.get_country_for_target(domain)
        profile = COUNTRY_PROFILES.get(country, COUNTRY_PROFILES["US"])
        print(f"   {domain} → {country} ({profile.accept_language})")

    print("\n🔓 Geo-Block Detection Patterns:")
    test_responses = [
        ("This content is not available in your region", 200),
        ("Access denied based on your location", 403),
        ("Normal page content", 200),
        ("Legal restriction", 451),
    ]

    for text, status in test_responses:
        blocked, reason = geo.detect_geo_blocking(text, status)
        status_icon = "🚫" if blocked else "✅"
        print(f"   {status_icon} [{status}] {text[:40]}... → {reason or 'OK'}")

    print("\n" + "=" * 60)
    print("✅ Geo IP Evasion ready")


if __name__ == "__main__":
    demo()
