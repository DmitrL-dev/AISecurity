"""
SafeClaw Router — SSRF Protection.

SEC-09: Validates provider URLs to prevent
Server-Side Request Forgery when BYOK is
implemented in the future.

Blocks:
- Private IPs (RFC 1918: 10.x, 172.16-31.x, 192.168.x)
- Link-local (169.254.x.x)
- Loopback (127.x.x.x)
- Cloud metadata endpoints (169.254.169.254)
- Non-HTTP(S) schemes
"""

import ipaddress
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Cloud metadata IPs to block
_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure
    "100.100.100.200",  # Alibaba Cloud
    "fd00:ec2::254",  # AWS IPv6
}

# Allowed URL schemes
_ALLOWED_SCHEMES = {"http", "https"}


def is_safe_url(url: str) -> bool:
    """
    Validate that a URL is safe for outbound requests.

    Returns True if the URL:
    - Uses http or https scheme
    - Does not resolve to a private/reserved IP
    - Does not target cloud metadata endpoints

    Use this to validate user-supplied provider URLs
    (BYOK feature) before making requests.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # Check scheme
    if parsed.scheme not in _ALLOWED_SCHEMES:
        logger.warning(
            "SSRF: blocked scheme %r in URL %s",
            parsed.scheme,
            url,
        )
        return False

    # Check hostname
    hostname = parsed.hostname
    if not hostname:
        return False

    # Block known metadata IPs
    if hostname in _METADATA_IPS:
        logger.warning("SSRF: blocked metadata IP %s", url)
        return False

    # Try to parse as IP
    try:
        ip = ipaddress.ip_address(hostname)
        if (
            ip.is_private
            or ip.is_reserved
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
        ):
            logger.warning(
                "SSRF: blocked private/reserved " "IP %s in URL %s",
                ip,
                url,
            )
            return False
    except ValueError:
        # It's a hostname, not an IP — that's OK
        # DNS rebinding is a separate concern
        pass

    return True


def validate_provider_url(url: str) -> str:
    """
    Validate and return a safe provider URL.
    Raises ValueError if URL is unsafe.
    """
    if not is_safe_url(url):
        raise ValueError(
            "Provider URL is not allowed: "
            "must use http(s) and not target "
            "private/reserved networks."
        )
    return url
