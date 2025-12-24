"""
SENTINEL Strike — TOKEN EXTRACTION MODULE

Autonomous token extraction:
1. Browser storage (localStorage, sessionStorage, cookies)
2. Memory/process analysis
3. Network traffic analysis
4. JS source analysis
"""

import asyncio
import re
import json
from datetime import datetime
from dataclasses import dataclass
from playwright.async_api import async_playwright


@dataclass
class ExtractedToken:
    """Extracted token."""

    source: str
    type: str
    name: str
    value: str
    expires: str = ""


class TokenExtractor:
    """Token extraction module."""

    def __init__(self):
        self.tokens: list[ExtractedToken] = []
        self.api_calls: list[dict] = []

    async def extract_from_browser(self, url: str) -> list[ExtractedToken]:
        """Extract tokens from browser storage."""
        print(f"\n🔍 Extracting from browser: {url}")
        tokens = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(locale="ru-RU")
            page = await context.new_page()

            # Intercept network
            page.on("request", lambda r: self._on_request(r))

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(5000)

            # 1. Cookies
            cookies = await context.cookies()
            for cookie in cookies:
                if self._is_auth_cookie(cookie["name"]):
                    tokens.append(
                        ExtractedToken(
                            source="cookie",
                            type="session",
                            name=cookie["name"],
                            value=cookie["value"][:100],
                            expires=cookie.get("expires", ""),
                        )
                    )
                    print(f"   🍪 Cookie: {cookie['name']}")

            # 2. LocalStorage
            local_items = await page.evaluate("() => Object.entries(localStorage)")
            for key, value in local_items:
                if self._is_auth_key(key) or self._looks_like_token(str(value)):
                    tokens.append(
                        ExtractedToken(
                            source="localStorage",
                            type="token",
                            name=key,
                            value=str(value)[:100],
                        )
                    )
                    print(f"   💾 LocalStorage: {key}")

            # 3. SessionStorage
            session_items = await page.evaluate("() => Object.entries(sessionStorage)")
            for key, value in session_items:
                if self._is_auth_key(key) or self._looks_like_token(str(value)):
                    tokens.append(
                        ExtractedToken(
                            source="sessionStorage",
                            type="token",
                            name=key,
                            value=str(value)[:100],
                        )
                    )
                    print(f"   📦 SessionStorage: {key}")

            # 4. Window variables
            window_tokens = await page.evaluate(
                """
                () => {
                    const found = [];
                    const keywords = ['token', 'auth', 'key', 'secret', 'credential', 'bearer', 'jwt'];
                    
                    function search(obj, path = 'window') {
                        if (typeof obj !== 'object' || obj === null || path.split('.').length > 4) return;
                        
                        for (let key in obj) {
                            try {
                                const val = obj[key];
                                const keyLower = key.toLowerCase();
                                
                                if (keywords.some(kw => keyLower.includes(kw))) {
                                    if (typeof val === 'string' && val.length > 10) {
                                        found.push({path: `${path}.${key}`, value: val.substring(0, 100)});
                                    }
                                }
                            } catch {}
                        }
                    }
                    
                    // Check common locations
                    try { search(window.__NUXT__); } catch {}
                    try { search(window.__NEXT_DATA__); } catch {}
                    try { search(window.config); } catch {}
                    try { search(window.settings); } catch {}
                    
                    return found;
                }
            """
            )

            for item in window_tokens:
                tokens.append(
                    ExtractedToken(
                        source="window",
                        type="variable",
                        name=item["path"],
                        value=item["value"],
                    )
                )
                print(f"   🪟 Window: {item['path']}")

            await browser.close()

        return tokens

    def _on_request(self, request):
        """Capture auth headers from requests."""
        headers = request.headers
        auth = headers.get("authorization", "")

        if auth:
            self.api_calls.append({"url": request.url, "auth": auth[:100]})

    def _is_auth_cookie(self, name: str) -> bool:
        """Check if cookie name suggests auth."""
        keywords = [
            "token",
            "auth",
            "session",
            "jwt",
            "key",
            "bearer",
            "credential",
            "access",
        ]
        return any(kw in name.lower() for kw in keywords)

    def _is_auth_key(self, key: str) -> bool:
        """Check if storage key suggests auth."""
        keywords = [
            "token",
            "auth",
            "session",
            "jwt",
            "key",
            "bearer",
            "credential",
            "access",
            "secret",
        ]
        return any(kw in key.lower() for kw in keywords)

    def _looks_like_token(self, value: str) -> bool:
        """Check if value looks like a token."""
        # JWT pattern
        if re.match(r"^eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$", value):
            return True
        # Long alphanumeric
        if re.match(r"^[a-zA-Z0-9_-]{32,}$", value):
            return True
        return False

    async def analyze_network_for_auth(self, url: str) -> list[dict]:
        """Analyze network traffic for auth patterns."""
        print(f"\n🔍 Analyzing network traffic: {url}")
        auth_requests = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            captured = []

            def capture_request(request):
                headers = dict(request.headers)
                if any(
                    h.lower() in ["authorization", "x-auth-token", "x-api-key"]
                    for h in headers
                ):
                    captured.append(
                        {
                            "url": request.url,
                            "method": request.method,
                            "auth_headers": {
                                k: v
                                for k, v in headers.items()
                                if k.lower()
                                in ["authorization", "x-auth-token", "x-api-key"]
                            },
                        }
                    )

            page.on("request", capture_request)

            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(5000)

            auth_requests = captured

            if auth_requests:
                print(f"   🔐 Found {len(auth_requests)} authenticated requests")
                for req in auth_requests[:5]:
                    print(f"      {req['method']} {req['url'][:50]}")
            else:
                print(f"   ℹ️  No authenticated requests captured")

            await browser.close()

        return auth_requests

    async def full_extraction(self, urls: list[str]):
        """Run full token extraction."""
        print()
        print("╔" + "═" * 62 + "╗")
        print("║" + " 🔑 SENTINEL Token Extraction ".center(62) + "║")
        print("╠" + "═" * 62 + "╣")
        print("║" + f" Targets: {len(urls)}".ljust(62) + "║")
        print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(62) + "║")
        print("╚" + "═" * 62 + "╝")

        for url in urls:
            browser_tokens = await self.extract_from_browser(url)
            self.tokens.extend(browser_tokens)

            network_auth = await self.analyze_network_for_auth(url)
            for auth in network_auth:
                for header, value in auth.get("auth_headers", {}).items():
                    self.tokens.append(
                        ExtractedToken(
                            source="network",
                            type="header",
                            name=header,
                            value=value[:100],
                        )
                    )

        self.print_results()

    def print_results(self):
        """Print extraction results."""
        print()
        print("═" * 64)
        print("📊 TOKEN EXTRACTION RESULTS")
        print("─" * 64)
        print(f"   Tokens found: {len(self.tokens)}")
        print(f"   API calls with auth: {len(self.api_calls)}")

        if self.tokens:
            print("\n🔑 EXTRACTED TOKENS:")
            for t in self.tokens:
                print(f"\n   [{t.source.upper()}] {t.name}")
                print(f"   Type: {t.type}")
                print(f"   Value: {t.value[:60]}...")

        print()
        print("═" * 64)


async def main():
    extractor = TokenExtractor()
    await extractor.full_extraction(
        [
            "https://salute.sber.ru",
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
