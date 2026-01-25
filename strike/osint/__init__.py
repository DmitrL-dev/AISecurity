"""
SENTINEL Strike — OSINT MODULE

Autonomous search for leaked API keys and credentials:
1. GitHub search (code, gists)
2. Pastebin-like services
3. Common leak patterns
4. Certificate Transparency logs
"""

import asyncio
import re
import httpx
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class LeakedCredential:
    """Found credential."""

    source: str
    type: str  # api_key, token, password
    value: str
    context: str
    confidence: float  # 0-1


# Паттерны для поиска ключей
KEY_PATTERNS = {
    "gigachat": [
        r"gigachat[_-]?api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
        r"sber[_-]?api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
        r"GIGACHAT[_-]API[_-]KEY['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
    ],
    "openai": [
        r"sk-[a-zA-Z0-9]{48}",
        r"openai[_-]?api[_-]?key['\"]?\s*[:=]\s*['\"]?(sk-[a-zA-Z0-9]{48})",
    ],
    "anthropic": [
        r"sk-ant-[a-zA-Z0-9_-]{40,}",
    ],
    "generic": [
        r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
        r"auth[_-]?token['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
        r"bearer['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
        r"secret[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_-]{20,})",
    ],
}


class OSINTModule:
    """OSINT for finding leaked credentials."""

    def __init__(self, target_domain: str):
        self.target = target_domain
        self.found_credentials: list[LeakedCredential] = []

    async def search_github(self) -> list[LeakedCredential]:
        """Search GitHub for leaked keys."""
        print("\n🔍 GitHub Search...")
        results = []

        # GitHub code search queries
        queries = [
            f'"{self.target}" api_key',
            f'"{self.target}" token',
            f'"{self.target}" secret',
            "gigachat api key",
            "sberbank api key",
        ]

        async with httpx.AsyncClient(timeout=15.0) as client:
            for query in queries:
                try:
                    # GitHub search API (limited without auth)
                    url = f"https://api.github.com/search/code?q={query}"
                    headers = {"Accept": "application/vnd.github.v3+json"}

                    resp = await client.get(url, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        count = data.get("total_count", 0)
                        if count > 0:
                            print(f"   📌 '{query}': {count} results")
                            results.append(
                                LeakedCredential(
                                    source="github",
                                    type="potential_leak",
                                    value=f"{count} results for '{query}'",
                                    context="GitHub code search",
                                    confidence=0.3,
                                )
                            )
                    elif resp.status_code == 403:
                        print("   ⚠️  Rate limited (need GitHub token)")
                        break

                    await asyncio.sleep(2)  # Rate limit

                except Exception as e:
                    print(f"   ❌ Error: {e}")

        return results

    async def search_pastebin_like(self) -> list[LeakedCredential]:
        """Search pastebin-like services."""
        print("\n🔍 Pastebin Search...")
        results = []

        # Публичные поисковые сервисы
        search_urls = [
            f"https://psbdmp.ws/api/search/{self.target}",  # Pastebin dumps
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in search_urls:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and resp.text:
                        data = (
                            resp.json()
                            if resp.headers.get("content-type", "").startswith(
                                "application/json"
                            )
                            else []
                        )
                        if data:
                            print(f"   📌 Found {len(data)} paste(s)")
                            results.append(
                                LeakedCredential(
                                    source="pastebin",
                                    type="paste_found",
                                    value=f"{len(data)} pastes",
                                    context=url,
                                    confidence=0.2,
                                )
                            )
                except:
                    pass

        return results

    async def search_certificate_transparency(self) -> list[str]:
        """Search CT logs for subdomains."""
        print("\n🔍 Certificate Transparency...")
        subdomains = []

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # crt.sh API
                url = f"https://crt.sh/?q=%.{self.target}&output=json"
                resp = await client.get(url)

                if resp.status_code == 200:
                    data = resp.json()
                    names = set()
                    for cert in data:
                        name = cert.get("name_value", "")
                        for n in name.split("\n"):
                            if n and self.target in n:
                                names.add(n.strip())

                    subdomains = list(names)
                    print(f"   📌 Found {len(subdomains)} subdomains from CT logs")

                    # Показываем AI-related
                    ai_subs = [
                        s
                        for s in subdomains
                        if any(
                            kw in s.lower()
                            for kw in [
                                "ai",
                                "ml",
                                "chat",
                                "bot",
                                "gpt",
                                "llm",
                                "api",
                                "gigachat",
                            ]
                        )
                    ]
                    if ai_subs:
                        print(f"   🎯 AI-related: {ai_subs[:5]}")

            except Exception as e:
                print(f"   ❌ Error: {e}")

        return subdomains

    async def analyze_js_for_keys(self, url: str) -> list[LeakedCredential]:
        """Analyze JS files for hardcoded keys."""
        print(f"\n🔍 Analyzing JS from {url}...")
        results = []

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                html = resp.text

                # Extract JS URLs
                js_urls = re.findall(r'src=["\']([^"\']*\.js[^"\']*)["\']', html)

                for js_url in js_urls[:10]:
                    if not js_url.startswith("http"):
                        js_url = f"{url.rstrip('/')}/{js_url.lstrip('/')}"

                    try:
                        js_resp = await client.get(js_url)
                        js_content = js_resp.text

                        # Search for keys
                        for key_type, patterns in KEY_PATTERNS.items():
                            for pattern in patterns:
                                matches = re.findall(pattern, js_content, re.IGNORECASE)
                                for match in matches:
                                    if len(match) > 10:  # Filter short matches
                                        results.append(
                                            LeakedCredential(
                                                source=js_url,
                                                type=key_type,
                                                value=match[:50] + "...",
                                                context="Hardcoded in JS",
                                                confidence=0.7,
                                            )
                                        )
                                        print(
                                            f"   🔴 Found {key_type} key in {js_url.split('/')[-1]}"
                                        )
                    except:
                        pass

            except Exception as e:
                print(f"   ❌ Error: {e}")

        return results

    async def full_osint(self):
        """Run full OSINT."""
        print()
        print("╔" + "═" * 62 + "╗")
        print("║" + " 🔍 SENTINEL OSINT — Credential Search ".center(62) + "║")
        print("╠" + "═" * 62 + "╣")
        print("║" + f" Target: {self.target}".ljust(62) + "║")
        print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(62) + "║")
        print("╚" + "═" * 62 + "╝")

        # 1. Certificate Transparency
        subdomains = await self.search_certificate_transparency()

        # 2. GitHub search
        github_results = await self.search_github()
        self.found_credentials.extend(github_results)

        # 3. Pastebin search
        paste_results = await self.search_pastebin_like()
        self.found_credentials.extend(paste_results)

        # 4. JS analysis on main sites
        main_urls = [f"https://{self.target}", f"https://www.{self.target}"]
        for url in main_urls:
            js_results = await self.analyze_js_for_keys(url)
            self.found_credentials.extend(js_results)

        # Results
        self.print_results(subdomains)

    def print_results(self, subdomains: list):
        """Print OSINT results."""
        print()
        print("═" * 64)
        print("📊 OSINT RESULTS")
        print("─" * 64)
        print(f"   Subdomains from CT: {len(subdomains)}")
        print(f"   Potential leaks: {len(self.found_credentials)}")

        if self.found_credentials:
            print("\n📋 FINDINGS:")
            for cred in self.found_credentials:
                print(f"\n   [{cred.type.upper()}] {cred.source}")
                print(f"   Value: {cred.value}")
                print(f"   Confidence: {cred.confidence:.0%}")

        # AI subdomains
        ai_subs = [
            s
            for s in subdomains
            if any(
                kw in s.lower()
                for kw in [
                    "ai",
                    "ml",
                    "chat",
                    "bot",
                    "gpt",
                    "llm",
                    "api",
                    "gigachat",
                    "salute",
                ]
            )
        ]
        if ai_subs:
            print("\n🎯 AI-RELATED SUBDOMAINS:")
            for sub in ai_subs[:10]:
                print(f"   • {sub}")

        print()
        print("═" * 64)


async def main():
    osint = OSINTModule("sber.ru")
    await osint.full_osint()


if __name__ == "__main__":
    asyncio.run(main())
