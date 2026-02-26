"""
SENTINEL Strike — Traffic Parser

Parse raw network traffic for LLM requests.
"""

from dataclasses import dataclass, field
from typing import Optional, Generator
from datetime import datetime
import re


@dataclass
class HTTPTransaction:
    """Raw HTTP transaction."""

    request_method: str
    request_url: str
    request_headers: dict
    request_body: bytes
    response_status: Optional[int] = None
    response_headers: Optional[dict] = None
    response_body: Optional[bytes] = None
    timestamp: datetime = field(default_factory=datetime.now)


class TrafficParser:
    """Parse network traffic for HTTP/HTTPS."""

    def __init__(self):
        self.transactions: list[HTTPTransaction] = []

    def parse_request(self, raw_data: bytes) -> Optional[HTTPTransaction]:
        """Parse raw HTTP request."""
        try:
            # Split headers and body
            parts = raw_data.split(b"\r\n\r\n", 1)
            header_section = parts[0].decode("utf-8", errors="ignore")
            body = parts[1] if len(parts) > 1 else b""

            lines = header_section.split("\r\n")
            if not lines:
                return None

            # Parse request line
            request_line = lines[0]
            match = re.match(r"(\w+)\s+(\S+)\s+HTTP", request_line)
            if not match:
                return None

            method, url = match.groups()

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            transaction = HTTPTransaction(
                request_method=method,
                request_url=url,
                request_headers=headers,
                request_body=body,
            )
            self.transactions.append(transaction)
            return transaction

        except Exception:
            return None

    def parse_response(self, raw_data: bytes, transaction: HTTPTransaction) -> bool:
        """Parse HTTP response and attach to transaction."""
        try:
            parts = raw_data.split(b"\r\n\r\n", 1)
            header_section = parts[0].decode("utf-8", errors="ignore")
            body = parts[1] if len(parts) > 1 else b""

            lines = header_section.split("\r\n")
            if not lines:
                return False

            # Parse status line
            status_line = lines[0]
            match = re.match(r"HTTP/\d\.\d\s+(\d+)", status_line)
            if not match:
                return False

            status = int(match.group(1))

            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip()] = value.strip()

            transaction.response_status = status
            transaction.response_headers = headers
            transaction.response_body = body
            return True

        except Exception:
            return False

    def filter_llm_traffic(self) -> Generator[HTTPTransaction, None, None]:
        """Filter transactions that look like LLM API calls."""
        llm_patterns = [
            r"openai\.com",
            r"anthropic\.com",
            r"googleapis\.com",
            r"/v1/chat",
            r"/v1/messages",
            r"/api/generate",
        ]

        for tx in self.transactions:
            url = tx.request_url.lower()
            host = tx.request_headers.get("Host", "").lower()
            full_url = f"{host}{url}"

            for pattern in llm_patterns:
                if re.search(pattern, full_url):
                    yield tx
                    break

    def get_statistics(self) -> dict:
        """Get traffic statistics."""
        llm_count = sum(1 for _ in self.filter_llm_traffic())
        return {
            "total_transactions": len(self.transactions),
            "llm_transactions": llm_count,
            "methods": self._count_methods(),
        }

    def _count_methods(self) -> dict:
        """Count HTTP methods."""
        counts = {}
        for tx in self.transactions:
            method = tx.request_method
            counts[method] = counts.get(method, 0) + 1
        return counts
