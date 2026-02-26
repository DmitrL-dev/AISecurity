#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Block Detection & Evasion

Detects when target blocks us and automatically evades:
1. WAF detection (Cloudflare, Akamai, AWS WAF, etc.)
2. Rate limiting detection
3. IP ban detection
4. Captcha/challenge detection
5. Automatic IP rotation on block
6. Request fingerprint randomization
7. Timing attack evasion

This is CRITICAL for real-world pentesting.
"""

import asyncio
import random
import time
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from enum import Enum

import aiohttp


# ============================================================================
# BLOCK TYPES
# ============================================================================

class BlockType(Enum):
    NONE = "none"
    WAF = "waf"
    RATE_LIMIT = "rate_limit"
    IP_BAN = "ip_ban"
    CAPTCHA = "captcha"
    GEO_BLOCK = "geo_block"
    BEHAVIOR = "behavior"
    UNKNOWN = "unknown"


# ============================================================================
# WAF SIGNATURES
# ============================================================================

WAF_SIGNATURES = {
    "cloudflare": {
        "headers": ["cf-ray", "cf-cache-status", "__cfduid"],
        "body": ["cloudflare", "cf-browser-verification", "checking your browser", "ray id:"],
        "status": [403, 503],
    },
    "akamai": {
        "headers": ["akamai-", "x-akamai-"],
        "body": ["akamai", "access denied", "reference #"],
        "status": [403],
    },
    "aws_waf": {
        "headers": ["x-amzn-requestid", "x-amz-cf-id"],
        "body": ["aws", "request blocked", "waf"],
        "status": [403],
    },
    "imperva": {
        "headers": ["x-iinfo", "incap_ses_"],
        "body": ["incapsula", "imperva", "incident id"],
        "status": [403],
    },
    "sucuri": {
        "headers": ["x-sucuri-id"],
        "body": ["sucuri", "website firewall", "blocked"],
        "status": [403],
    },
    "modsecurity": {
        "body": ["mod_security", "modsecurity", "blocked by", "not acceptable"],
        "status": [403, 406],
    },
    "nginx_limit": {
        "body": ["limit_req", "too many requests"],
        "status": [429, 503],
    },
    "fail2ban": {
        "body": ["banned", "blocked"],
        "status": [403],
    },
}

# Rate limit response patterns
RATE_LIMIT_PATTERNS = [
    "rate limit",
    "too many requests",
    "slow down",
    "request limit",
    "throttl",
    "quota exceeded",
    "try again later",
    "temporarily blocked",
]

# Captcha/challenge patterns
CAPTCHA_PATTERNS = [
    "captcha",
    "recaptcha",
    "hcaptcha",
    "challenge",
    "verify you are human",
    "are you a robot",
    "bot detection",
    "please verify",
    "security check",
]

# Block page patterns
BLOCK_PATTERNS = [
    "access denied",
    "forbidden",
    "blocked",
    "not allowed",
    "permission denied",
    "unauthorized",
    "ip blocked",
    "your ip",
    "has been blocked",
    "security violation",
]


# ============================================================================
# BLOCK DETECTOR
# ============================================================================

@dataclass
class BlockInfo:
    """Information about detected block."""
    blocked: bool
    block_type: BlockType
    waf_name: Optional[str] = None
    confidence: float = 0.0
    evidence: str = ""
    status_code: int = 0
    response_time: float = 0.0


@dataclass
class BaselineResponse:
    """Baseline response for comparison."""
    status_code: int
    content_length: int
    content_hash: str
    response_time: float
    headers: Dict[str, str]
    timestamp: datetime


class BlockDetector:
    """
    Detects if target is blocking our requests.

    Uses multiple signals:
    - Status code changes
    - Response content changes
    - Response time anomalies
    - WAF signatures
    - Rate limit patterns
    """

    def __init__(self):
        self.baselines: Dict[str, BaselineResponse] = {}
        self.block_history: List[BlockInfo] = []
        self.consecutive_blocks = 0
        self.last_successful_request = None

    async def establish_baseline(
        self,
        target: str,
        session: aiohttp.ClientSession
    ) -> Optional[BaselineResponse]:
        """
        Establish baseline response for target.
        Should be called BEFORE any attacks.
        """
        try:
            start = time.time()
            async with session.get(target, allow_redirects=True) as resp:
                duration = time.time() - start
                content = await resp.text()

                baseline = BaselineResponse(
                    status_code=resp.status,
                    content_length=len(content),
                    content_hash=hashlib.md5(
                        content.encode()).hexdigest()[:16],
                    response_time=duration,
                    headers={k.lower(): v for k, v in resp.headers.items()},
                    timestamp=datetime.now(),
                )

                self.baselines[target] = baseline
                print(
                    f"   📊 Baseline: status={baseline.status_code}, size={baseline.content_length}, time={baseline.response_time:.2f}s")

                return baseline

        except Exception as e:
            print(f"   ⚠️ Failed to establish baseline: {e}")
            return None

    def analyze_response(
        self,
        status_code: int,
        content: str,
        headers: Dict[str, str],
        response_time: float,
        target: str = None,
    ) -> BlockInfo:
        """
        Analyze response to detect if we're blocked.
        """
        content_lower = content.lower()
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}

        # Check for WAF
        waf_result = self._detect_waf(
            status_code, content_lower, headers_lower)
        if waf_result[0]:
            return BlockInfo(
                blocked=True,
                block_type=BlockType.WAF,
                waf_name=waf_result[1],
                confidence=waf_result[2],
                evidence=waf_result[3],
                status_code=status_code,
                response_time=response_time,
            )

        # Check for rate limiting
        if self._detect_rate_limit(status_code, content_lower):
            return BlockInfo(
                blocked=True,
                block_type=BlockType.RATE_LIMIT,
                confidence=0.9,
                evidence="Rate limit pattern detected",
                status_code=status_code,
                response_time=response_time,
            )

        # Check for captcha
        if self._detect_captcha(content_lower):
            return BlockInfo(
                blocked=True,
                block_type=BlockType.CAPTCHA,
                confidence=0.95,
                evidence="Captcha/challenge detected",
                status_code=status_code,
                response_time=response_time,
            )

        # Check for generic block
        if self._detect_block(status_code, content_lower):
            return BlockInfo(
                blocked=True,
                block_type=BlockType.IP_BAN,
                confidence=0.7,
                evidence="Block pattern detected",
                status_code=status_code,
                response_time=response_time,
            )

        # Check against baseline
        if target and target in self.baselines:
            baseline = self.baselines[target]
            anomaly = self._detect_baseline_anomaly(
                status_code, len(content), response_time, baseline
            )
            if anomaly:
                return BlockInfo(
                    blocked=True,
                    block_type=BlockType.BEHAVIOR,
                    confidence=0.6,
                    evidence=f"Baseline anomaly: {anomaly}",
                    status_code=status_code,
                    response_time=response_time,
                )

        # Not blocked
        self.consecutive_blocks = 0
        self.last_successful_request = datetime.now()

        return BlockInfo(
            blocked=False,
            block_type=BlockType.NONE,
            status_code=status_code,
            response_time=response_time,
        )

    def _detect_waf(
        self,
        status: int,
        content: str,
        headers: Dict[str, str]
    ) -> Tuple[bool, str, float, str]:
        """Detect specific WAF."""
        for waf_name, signatures in WAF_SIGNATURES.items():
            confidence = 0.0
            evidence = []

            # Check headers
            for header in signatures.get("headers", []):
                if any(header in h for h in headers.keys()):
                    confidence += 0.3
                    evidence.append(f"header:{header}")

            # Check body
            for pattern in signatures.get("body", []):
                if pattern in content:
                    confidence += 0.4
                    evidence.append(f"body:{pattern}")

            # Check status
            if status in signatures.get("status", []):
                confidence += 0.2
                evidence.append(f"status:{status}")

            if confidence >= 0.5:
                return (True, waf_name, min(confidence, 1.0), ", ".join(evidence))

        return (False, None, 0.0, "")

    def _detect_rate_limit(self, status: int, content: str) -> bool:
        """Detect rate limiting."""
        if status == 429:
            return True

        return any(p in content for p in RATE_LIMIT_PATTERNS)

    def _detect_captcha(self, content: str) -> bool:
        """Detect captcha/challenge."""
        return any(p in content for p in CAPTCHA_PATTERNS)

    def _detect_block(self, status: int, content: str) -> bool:
        """Detect generic block."""
        if status in [403, 406, 451]:
            return True

        matches = sum(1 for p in BLOCK_PATTERNS if p in content)
        return matches >= 2

    def _detect_baseline_anomaly(
        self,
        status: int,
        content_length: int,
        response_time: float,
        baseline: BaselineResponse,
    ) -> Optional[str]:
        """Compare against baseline."""
        # Status changed from 200 to error
        if baseline.status_code == 200 and status >= 400:
            return f"status changed {baseline.status_code} -> {status}"

        # Response size dramatically changed
        if baseline.content_length > 0:
            size_ratio = content_length / baseline.content_length
            if size_ratio < 0.3 or size_ratio > 3.0:
                return f"size changed {baseline.content_length} -> {content_length}"

        # Response time dramatically increased (possible throttling)
        if baseline.response_time > 0:
            time_ratio = response_time / baseline.response_time
            if time_ratio > 5.0:
                return f"slow response {baseline.response_time:.2f}s -> {response_time:.2f}s"

        return None

    def is_blocked(self) -> bool:
        """Check if we're currently blocked."""
        return self.consecutive_blocks >= 3

    def record_block(self, info: BlockInfo):
        """Record a block event."""
        if info.blocked:
            self.consecutive_blocks += 1
            self.block_history.append(info)
        else:
            self.consecutive_blocks = 0

    def get_stats(self) -> Dict:
        """Get blocking statistics."""
        total = len(self.block_history)
        by_type = {}
        for info in self.block_history:
            t = info.block_type.value
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "total_blocks": total,
            "consecutive": self.consecutive_blocks,
            "by_type": by_type,
            "is_blocked": self.is_blocked(),
        }


# ============================================================================
# EVASION ENGINE
# ============================================================================

class EvasionEngine:
    """
    Automatic evasion when blocks are detected.

    Strategies:
    1. IP rotation (via VPN/proxy)
    2. Request timing randomization
    3. User-Agent rotation
    4. Header randomization
    5. Request fingerprint obfuscation
    """

    def __init__(self, rotator=None):
        self.rotator = rotator  # ZooGVPN rotator
        self.detector = BlockDetector()
        self.evasion_count = 0
        self.current_delay = 1.0

        # User agents pool
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/120.0.0.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
        ]

        self.current_ua = random.choice(self.user_agents)

    async def check_and_evade(
        self,
        status_code: int,
        content: str,
        headers: Dict[str, str],
        response_time: float,
        target: str = None,
    ) -> bool:
        """
        Check if blocked and automatically evade.

        Returns True if we performed evasion.
        """
        block_info = self.detector.analyze_response(
            status_code, content, headers, response_time, target
        )

        self.detector.record_block(block_info)

        if block_info.blocked:
            print(f"\n   ⚠️ BLOCK DETECTED: {block_info.block_type.value}")
            print(f"      WAF: {block_info.waf_name or 'unknown'}")
            print(f"      Confidence: {block_info.confidence:.0%}")
            print(f"      Evidence: {block_info.evidence}")

            await self._perform_evasion(block_info)
            return True

        return False

    async def _perform_evasion(self, block_info: BlockInfo):
        """Perform evasion based on block type."""
        self.evasion_count += 1

        if block_info.block_type == BlockType.RATE_LIMIT:
            # Slow down and wait
            print("   🕐 Rate limited - increasing delay...")
            self.current_delay = min(self.current_delay * 2, 30.0)
            await asyncio.sleep(random.uniform(5, 15))

        elif block_info.block_type in [BlockType.WAF, BlockType.IP_BAN]:
            # Rotate IP
            if self.rotator:
                print("   🔄 Rotating IP...")
                self.rotator.force_rotate()
                print(f"      New proxy: {self.rotator.current_server}")

            # Change user agent
            self.current_ua = random.choice(self.user_agents)
            print("   🔄 Changed User-Agent")

            # Wait a bit
            await asyncio.sleep(random.uniform(3, 8))

        elif block_info.block_type == BlockType.CAPTCHA:
            # Can't solve captcha automatically
            print("   🚫 Captcha detected - need manual intervention or alternative IP")
            if self.rotator:
                self.rotator.force_rotate()
            await asyncio.sleep(random.uniform(10, 20))

        else:
            # Generic evasion
            if self.rotator:
                self.rotator.force_rotate()
            self.current_delay = min(self.current_delay * 1.5, 10.0)
            await asyncio.sleep(random.uniform(2, 5))

    def get_random_headers(self) -> Dict[str, str]:
        """Get randomized headers to avoid fingerprinting."""
        return {
            "User-Agent": self.current_ua,
            "Accept": random.choice([
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "*/*",
                "text/html,application/xhtml+xml",
            ]),
            "Accept-Language": random.choice([
                "en-US,en;q=0.9",
                "en-GB,en;q=0.8",
                "ru-RU,ru;q=0.9,en;q=0.8",
            ]),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Cache-Control": random.choice(["no-cache", "max-age=0"]),
        }

    def get_random_delay(self) -> float:
        """Get randomized delay between requests."""
        # Add jitter to avoid pattern detection
        base = self.current_delay
        jitter = random.uniform(-0.3, 0.5) * base
        return max(0.5, base + jitter)

    def get_stats(self) -> Dict:
        """Get evasion statistics."""
        return {
            "evasion_count": self.evasion_count,
            "current_delay": self.current_delay,
            "detector_stats": self.detector.get_stats(),
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def demo():
    """Demonstrate block detection."""
    print("=== Block Detection Demo ===\n")

    detector = BlockDetector()

    # Test WAF detection
    print("Testing WAF detection...")

    # Cloudflare example
    cf_result = detector.analyze_response(
        status_code=403,
        content="Checking your browser before accessing... Ray ID: abc123",
        headers={"cf-ray": "abc123", "server": "cloudflare"},
        response_time=0.5,
    )
    print(
        f"  Cloudflare: blocked={cf_result.blocked}, type={cf_result.block_type.value}, waf={cf_result.waf_name}")

    # Rate limit example
    rl_result = detector.analyze_response(
        status_code=429,
        content="Too many requests. Please slow down.",
        headers={},
        response_time=0.1,
    )
    print(
        f"  Rate limit: blocked={rl_result.blocked}, type={rl_result.block_type.value}")

    # Normal response
    ok_result = detector.analyze_response(
        status_code=200,
        content="<html><body>Hello World</body></html>",
        headers={"content-type": "text/html"},
        response_time=0.3,
    )
    print(
        f"  Normal: blocked={ok_result.blocked}, type={ok_result.block_type.value}")

    print("\n✅ Block detection working")


if __name__ == "__main__":
    asyncio.run(demo())
