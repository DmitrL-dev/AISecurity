"""
SENTINEL Strike — MITM Proxy

Proxy integration for traffic interception.
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from datetime import datetime


@dataclass
class InterceptedFlow:
    """Single intercepted request/response pair."""

    request_url: str
    request_method: str
    request_headers: dict
    request_body: bytes
    response_status: Optional[int] = None
    response_headers: Optional[dict] = None
    response_body: Optional[bytes] = None
    timestamp: datetime = field(default_factory=datetime.now)
    modified: bool = False


class MITMProxy:
    """MITM proxy controller for traffic interception."""

    def __init__(self, port: int = 8080):
        self.port = port
        self.flows: list[InterceptedFlow] = []
        self.request_handlers: list[Callable] = []
        self.response_handlers: list[Callable] = []
        self._running = False
        self._mitmproxy_available = self._check_mitmproxy()

    def _check_mitmproxy(self) -> bool:
        """Check if mitmproxy is available."""
        try:
            from mitmproxy import http

            return True
        except ImportError:
            return False

    def on_request(self, handler: Callable):
        """Register request handler."""
        self.request_handlers.append(handler)
        return handler

    def on_response(self, handler: Callable):
        """Register response handler."""
        self.response_handlers.append(handler)
        return handler

    async def start(self):
        """Start MITM proxy."""
        if not self._mitmproxy_available:
            raise RuntimeError("mitmproxy not installed. Run: pip install mitmproxy")

        self._running = True
        # Note: Full mitmproxy integration requires running as addon
        # This is a stub for the interface

    async def stop(self):
        """Stop MITM proxy."""
        self._running = False

    def inject_request(
        self,
        flow: InterceptedFlow,
        new_body: Optional[bytes] = None,
        new_headers: Optional[dict] = None,
    ) -> InterceptedFlow:
        """Modify request before sending."""
        if new_body is not None:
            flow.request_body = new_body
            flow.modified = True
        if new_headers is not None:
            flow.request_headers.update(new_headers)
            flow.modified = True
        return flow

    def inject_response(
        self,
        flow: InterceptedFlow,
        new_body: Optional[bytes] = None,
        new_status: Optional[int] = None,
    ) -> InterceptedFlow:
        """Modify response before delivering."""
        if new_body is not None:
            flow.response_body = new_body
            flow.modified = True
        if new_status is not None:
            flow.response_status = new_status
            flow.modified = True
        return flow

    def get_llm_flows(self) -> list[InterceptedFlow]:
        """Get flows that appear to be LLM API calls."""
        patterns = ["openai", "anthropic", "chat", "completions", "messages"]
        return [
            f for f in self.flows if any(p in f.request_url.lower() for p in patterns)
        ]

    def create_addon(self) -> Any:
        """Create mitmproxy addon class."""
        if not self._mitmproxy_available:
            return None

        proxy = self

        class StrikeAddon:
            def request(self, flow):
                # Convert to InterceptedFlow
                intercepted = InterceptedFlow(
                    request_url=flow.request.pretty_url,
                    request_method=flow.request.method,
                    request_headers=dict(flow.request.headers),
                    request_body=flow.request.content or b"",
                )
                proxy.flows.append(intercepted)

                # Call handlers
                for handler in proxy.request_handlers:
                    handler(intercepted, flow)

            def response(self, flow):
                # Find matching flow
                for intercepted in reversed(proxy.flows):
                    if intercepted.request_url == flow.request.pretty_url:
                        intercepted.response_status = flow.response.status_code
                        intercepted.response_headers = dict(flow.response.headers)
                        intercepted.response_body = flow.response.content or b""

                        for handler in proxy.response_handlers:
                            handler(intercepted, flow)
                        break

        return StrikeAddon()
