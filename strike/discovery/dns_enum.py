"""
SENTINEL Strike — DNS Enumerator

Enumerate DNS records for target domain.
"""

import asyncio
import socket
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DNSRecords:
    """DNS records for domain."""

    domain: str
    a: list[str] = field(default_factory=list)
    aaaa: list[str] = field(default_factory=list)
    mx: list[str] = field(default_factory=list)
    txt: list[str] = field(default_factory=list)
    ns: list[str] = field(default_factory=list)
    cname: list[str] = field(default_factory=list)


class DNSEnumerator:
    """Enumerate DNS records."""

    def __init__(self):
        self.use_dnspython = self._check_dnspython()

    def _check_dnspython(self) -> bool:
        """Check if dnspython is available."""
        try:
            import dns.resolver

            return True
        except ImportError:
            return False

    async def enumerate(self, domain: str) -> DNSRecords:
        """Get all DNS records for domain."""
        records = DNSRecords(domain=domain)

        if self.use_dnspython:
            records = await self._enumerate_dnspython(domain)
        else:
            records = await self._enumerate_stdlib(domain)

        return records

    async def _enumerate_dnspython(self, domain: str) -> DNSRecords:
        """Enumerate using dnspython."""
        import dns.resolver

        records = DNSRecords(domain=domain)

        record_types = ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]

        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                values = [str(r) for r in answers]
                setattr(records, rtype.lower(), values)
            except Exception:
                pass  # Record type doesn't exist

        return records

    async def _enumerate_stdlib(self, domain: str) -> DNSRecords:
        """Enumerate using stdlib (limited)."""
        records = DNSRecords(domain=domain)

        # A records via socket
        try:
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(domain, None, socket.AF_INET)
            records.a = list(set(r[4][0] for r in result))
        except Exception:
            pass

        # AAAA records
        try:
            loop = asyncio.get_event_loop()
            result = await loop.getaddrinfo(domain, None, socket.AF_INET6)
            records.aaaa = list(set(r[4][0] for r in result))
        except Exception:
            pass

        return records

    async def get_nameservers(self, domain: str) -> list[str]:
        """Get nameservers for domain."""
        records = await self.enumerate(domain)
        return records.ns
