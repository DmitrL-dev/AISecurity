"""
SENTINEL Shield SDK — Async HTTP Client.

Clean Architecture:
  - Domain: models.py, exceptions.py (zero deps)
  - Application: client.py (orchestration)
  - Infrastructure: _http.py (httpx adapter, hidden)

This client provides both sync and async APIs.
Sync methods use httpx.Client internally (no asyncio.run hacks).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import httpx

from .exceptions import (
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    ServerError,
    ShieldError,
    TimeoutError,
    ValidationError,
)
from .models import (
    EngineResult,
    HealthStatus,
    RedactResult,
    ScanResult,
    ShieldConfig,
    Threat,
    Verdict,
)


def _build_headers(config: ShieldConfig) -> dict[str, str]:
    """Build request headers from config."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "sentinel-shield-python/0.1.0",
    }
    if config.api_key:
        headers["X-API-Key"] = config.api_key
    return headers


def _handle_error_response(response: httpx.Response) -> None:
    """Convert HTTP error responses to typed exceptions."""
    status = response.status_code

    if status == 401:
        raise AuthenticationError()
    elif status == 422:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            pass
        raise ValidationError(
            f"Validation error: {detail}" if detail else "Input validation failed"
        )
    elif status == 429:
        retry_after = response.headers.get("Retry-After")
        raise RateLimitError(retry_after=float(retry_after) if retry_after else None)
    elif status == 503:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            pass
        raise ServerError(
            f"Service unavailable: {detail}" if detail else "Shield API server error"
        )
    elif status >= 500:
        raise ServerError(f"Shield API error: HTTP {status}")
    elif status >= 400:
        detail = ""
        try:
            detail = response.json().get("error", response.text[:200])
        except Exception:
            detail = response.text[:200]
        raise ShieldError(f"API error ({status}): {detail}", status_code=status)


def _parse_scan_result(data: dict[str, Any]) -> ScanResult:
    """Parse API response into ScanResult domain model."""
    threats = []
    for t in data.get("threats", []):
        threats.append(
            Threat(
                threat_type=t.get("threat_type", "unknown"),
                category=t.get("category", "unknown"),
                severity=float(t.get("severity", 0.0)),
                engine=t.get("engine", "unknown"),
                description=t.get("description", ""),
                metadata=t.get("metadata", {}),
            )
        )

    engine_details = []
    for e in data.get("engine_details", []):
        engine_threats = []
        for et in e.get("threats", []):
            engine_threats.append(
                Threat(
                    threat_type=et.get("threat_type", "unknown"),
                    category=et.get("category", "unknown"),
                    severity=float(et.get("severity", 0.0)),
                    engine=e.get("name", "unknown"),
                    description=et.get("description", ""),
                    metadata=et.get("metadata", {}),
                )
            )
        engine_details.append(
            EngineResult(
                name=e.get("name", "unknown"),
                has_threats=e.get("has_threats", False),
                threat_count=e.get("threat_count", 0),
                threats=engine_threats,
            )
        )

    verdict_str = data.get("verdict", "allow")
    try:
        verdict = Verdict(verdict_str)
    except ValueError:
        verdict = Verdict.ALLOW

    return ScanResult(
        verdict=verdict,
        risk_score=float(data.get("risk_score", 0.0)),
        latency_ms=float(data.get("latency_ms", 0.0)),
        engines_checked=data.get("engines_checked", []),
        threats=threats,
        engine_details=engine_details,
        text_hash=data.get("text_hash", ""),
    )


def _parse_redact_result(data: dict[str, Any]) -> RedactResult:
    """Parse API response into RedactResult domain model."""
    verdict_str = data.get("verdict", "allow")
    try:
        verdict = Verdict(verdict_str)
    except ValueError:
        verdict = Verdict.ALLOW

    return RedactResult(
        redacted_text=data.get("redacted_text", ""),
        original_length=data.get("original_length", 0),
        redacted_length=data.get("redacted_length", 0),
        total_redactions=data.get("total_redactions", 0),
        redactions=data.get("redactions", []),
        risk_score=float(data.get("risk_score", 0.0)),
        verdict=verdict,
    )


def _parse_health(data: dict[str, Any]) -> HealthStatus:
    """Parse health response."""
    return HealthStatus(
        status=data.get("status", "unknown"),
        version=data.get("version", "unknown"),
        mode=data.get("mode", "unknown"),
        uptime=float(data.get("uptime", 0.0)),
        patterns=int(data.get("patterns", 0)),
    )


class Shield:
    """SENTINEL Shield client — sync and async.

    Usage (sync):
        shield = Shield(api_key="sk-...")
        result = shield.scan("test prompt")
        if result.safe:
            pass  # forward to LLM

    Usage (async):
        shield = Shield(api_key="sk-...")
        result = await shield.scan_async("test prompt")

    Args:
        api_key: API key for authentication (or set SENTINEL_KEY env var).
        config: Full ShieldConfig for advanced settings.
        base_url: Shortcut to set only base URL (default: https://api.sentinel.dev).
    """

    def __init__(
        self,
        api_key: str | None = None,
        config: ShieldConfig | None = None,
        base_url: str | None = None,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            import os

            resolved_key = api_key or os.environ.get("SENTINEL_KEY")
            resolved_url = base_url or os.environ.get(
                "SENTINEL_URL", "https://api.sentinel.dev"
            )
            self._config = ShieldConfig(
                base_url=resolved_url,
                api_key=resolved_key,
            )

        self._headers = _build_headers(self._config)
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    @property
    def config(self) -> ShieldConfig:
        """Current SDK configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Sync API
    # ------------------------------------------------------------------

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self._config.base_url,
                headers=self._headers,
                timeout=self._config.timeout,
            )
        return self._sync_client

    def _request_sync(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute sync HTTP request with retry logic."""
        client = self._get_sync_client()

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = client.request(method, path, json=json)
                if response.status_code >= 400:
                    _handle_error_response(response)
                return response.json()  # type: ignore[no-any-return]
            except (AuthenticationError, ValidationError, RateLimitError):
                raise  # Don't retry client errors
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = ConnectionError(str(e))
            except httpx.TimeoutException as e:
                last_error = TimeoutError(str(e))
            except httpx.HTTPError as e:
                last_error = ShieldError(str(e))

            if attempt < self._config.max_retries:
                backoff = self._config.retry_backoff * (2**attempt)
                time.sleep(backoff)

        raise last_error or ShieldError("Unknown error")

    def scan(
        self,
        text: str,
        zone: str = "external",
        session_id: str | None = None,
    ) -> ScanResult:
        """Scan text for threats (synchronous).

        Args:
            text: The prompt text to analyze.
            zone: Security zone (default: "external").
            session_id: Optional session ID for tracking.

        Returns:
            ScanResult with verdict, risk_score, threats, and latency.

        Raises:
            AuthenticationError: Invalid API key.
            ValidationError: Invalid input (empty text, too long).
            ConnectionError: Cannot reach Shield API.
            TimeoutError: Request timed out.
        """
        payload: dict[str, Any] = {"text": text, "zone": zone}
        if session_id is not None:
            payload["session_id"] = session_id
        data = self._request_sync("POST", "/analyze", json=payload)
        return _parse_scan_result(data)

    def redact(self, text: str) -> RedactResult:
        """Redact PII from text (synchronous).

        Args:
            text: Text containing potential PII.

        Returns:
            RedactResult with redacted text and redaction details.
        """
        data = self._request_sync("POST", "/redact", json={"text": text})
        return _parse_redact_result(data)

    def health(self) -> HealthStatus:
        """Check Shield health (synchronous)."""
        data = self._request_sync("GET", "/health")
        return _parse_health(data)

    # ------------------------------------------------------------------
    # Async API
    # ------------------------------------------------------------------

    def _get_async_client(self) -> httpx.AsyncClient:
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(
                base_url=self._config.base_url,
                headers=self._headers,
                timeout=self._config.timeout,
            )
        return self._async_client

    async def _request_async(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute async HTTP request with retry logic."""
        client = self._get_async_client()

        last_error: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = await client.request(method, path, json=json)
                if response.status_code >= 400:
                    _handle_error_response(response)
                return response.json()  # type: ignore[no-any-return]
            except (AuthenticationError, ValidationError, RateLimitError):
                raise
            except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                last_error = ConnectionError(str(e))
            except httpx.TimeoutException as e:
                last_error = TimeoutError(str(e))
            except httpx.HTTPError as e:
                last_error = ShieldError(str(e))

            if attempt < self._config.max_retries:
                backoff = self._config.retry_backoff * (2**attempt)
                await asyncio.sleep(backoff)

        raise last_error or ShieldError("Unknown error")

    async def scan_async(
        self,
        text: str,
        zone: str = "external",
        session_id: str | None = None,
    ) -> ScanResult:
        """Scan text for threats (asynchronous).

        Args:
            text: The prompt text to analyze.
            zone: Security zone (default: "external").
            session_id: Optional session ID for tracking.

        Returns:
            ScanResult with verdict, risk_score, threats, and latency.
        """
        payload: dict[str, Any] = {"text": text, "zone": zone}
        if session_id is not None:
            payload["session_id"] = session_id
        data = await self._request_async("POST", "/analyze", json=payload)
        return _parse_scan_result(data)

    async def scan_batch_async(
        self,
        texts: list[str],
        zone: str = "external",
        max_concurrent: int = 10,
    ) -> list[ScanResult]:
        """Scan multiple texts concurrently (asynchronous).

        Args:
            texts: List of prompt texts to analyze.
            zone: Security zone for all texts.
            max_concurrent: Maximum concurrent requests.

        Returns:
            List of ScanResult, one per input text.
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scan_one(text: str) -> ScanResult:
            async with semaphore:
                return await self.scan_async(text, zone=zone)

        return await asyncio.gather(*[_scan_one(t) for t in texts])

    async def redact_async(self, text: str) -> RedactResult:
        """Redact PII from text (asynchronous)."""
        data = await self._request_async("POST", "/redact", json={"text": text})
        return _parse_redact_result(data)

    async def health_async(self) -> HealthStatus:
        """Check Shield health (asynchronous)."""
        data = await self._request_async("GET", "/health")
        return _parse_health(data)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close sync HTTP client."""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()

    async def aclose(self) -> None:
        """Close async HTTP client."""
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()

    def __enter__(self) -> Shield:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> Shield:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f"Shield(base_url={self._config.base_url!r})"
