"""
SENTINEL Strike — Web Attack Runner

Executes traditional web vulnerability scans using payloads
(SQLi, XSS, LFI, SSRF, etc.) instead of LLM jailbreak attacks.
"""

import asyncio
import aiohttp
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

logger = logging.getLogger(__name__)


class WebAttackState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WebAttackResult:
    """Result from a single web attack."""

    success: bool
    vector: str
    payload: str
    response_code: int
    response_body: str
    response_time: float
    evidence: Optional[str] = None


@dataclass
class WebAttackConfig:
    """Configuration for web attacks."""

    target_url: str
    web_vectors: List[str]
    target_param: str = "id"
    duration_minutes: int = 5
    max_iterations: int = 1000
    timeout: int = 10
    stealth: bool = True


class WebAttackRunner:
    """
    Executes web vulnerability scans using classic attack payloads.

    Supports: SQLi, XSS, LFI, SSRF, CMDi, SSTI, XXE, NoSQL
    """

    VECTOR_MAPPING = {
        "sqli": "SQLI_PAYLOADS",
        "xss": "XSS_PAYLOADS",
        "lfi": "LFI_PAYLOADS",
        "ssrf": "SSRF_PAYLOADS",
        "cmdi": "CMDI_PAYLOADS",
        "ssti": "SSTI_PAYLOADS",
        "xxe": "XXE_PAYLOADS",
        "nosql": "NOSQL_PAYLOADS",
    }

    # Detection patterns for each vector
    SUCCESS_PATTERNS = {
        "sqli": [
            "syntax error",
            "mysql",
            "postgresql",
            "sqlite",
            "ora-",
            "sql server",
            "unterminated",
            "quoted string",
        ],
        "xss": ["<script", "onerror=", "javascript:", "onclick="],
        "lfi": ["root:", "/etc/passwd", "win.ini", "[boot loader]"],
        "ssrf": ["localhost", "127.0.0.1", "internal", "metadata"],
        "cmdi": ["uid=", "root", "administrator", "volume serial"],
        "ssti": ["49", "7777777", "{{", "${"],  # 7*7=49
        "xxe": ["root:", "ENTITY", "DOCTYPE"],
        "nosql": ["true", "admin", "password"],
    }

    def __init__(self, config: WebAttackConfig):
        self.config = config
        self.state = WebAttackState.IDLE
        self.iteration = 0
        self.results: List[WebAttackResult] = []
        self.started_at: Optional[datetime] = None
        self.deadline: Optional[datetime] = None

        # Live progress tracking
        self.current_vector: Optional[str] = None
        self.current_payload: Optional[str] = None
        self.last_error: Optional[str] = None

        # Load payloads
        self.payloads = self._load_payloads()
        logger.info(
            f"WebAttackRunner: loaded {sum(len(p) for p in self.payloads.values())} payloads"
        )

    def _load_payloads(self) -> Dict[str, List[str]]:
        """Load payloads for selected vectors."""
        from strike.payloads import (
            SQLI_PAYLOADS,
            XSS_PAYLOADS,
            LFI_PAYLOADS,
            SSRF_PAYLOADS,
            CMDI_PAYLOADS,
            SSTI_PAYLOADS,
            XXE_PAYLOADS,
            NOSQL_PAYLOADS,
        )

        all_payloads = {
            "sqli": SQLI_PAYLOADS,
            "xss": XSS_PAYLOADS,
            "lfi": LFI_PAYLOADS,
            "ssrf": SSRF_PAYLOADS,
            "cmdi": CMDI_PAYLOADS,
            "ssti": SSTI_PAYLOADS,
            "xxe": XXE_PAYLOADS,
            "nosql": NOSQL_PAYLOADS,
        }

        # Filter to only requested vectors
        return {
            v: all_payloads.get(v, [])
            for v in self.config.web_vectors
            if v in all_payloads
        }

    async def run(self) -> Dict[str, Any]:
        """Main attack loop."""
        self.state = WebAttackState.RUNNING
        self.started_at = datetime.now()
        self.deadline = self.started_at + timedelta(
            minutes=self.config.duration_minutes
        )

        logger.info(f"🕷️ Web attack started: {self.config.target_url}")
        logger.info(f"📦 Vectors: {self.config.web_vectors}")

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as session:
                for vector, payloads in self.payloads.items():
                    if not self._should_continue():
                        break

                    self.current_vector = vector
                    logger.info(f"🎯 Testing {vector}: {len(payloads)} payloads")

                    for payload in payloads:
                        if not self._should_continue():
                            break

                        self.iteration += 1
                        self.current_payload = payload[:50]  # Truncate for display

                        result = await self._test_payload(session, vector, payload)
                        self.results.append(result)

                        if result.success:
                            logger.info(f"✅ {vector} HIT: {payload[:50]}")

        except Exception as e:
            logger.error(f"❌ Web attack failed: {e}")
            self.last_error = str(e)
            self.state = WebAttackState.FAILED
            raise

        self.state = WebAttackState.COMPLETED
        return self._generate_report()

    def _should_continue(self) -> bool:
        """Check if attack should continue."""
        if self.state != WebAttackState.RUNNING:
            return False
        if datetime.now() >= self.deadline:
            return False
        if self.iteration >= self.config.max_iterations:
            return False
        return True

    async def _test_payload(
        self, session: aiohttp.ClientSession, vector: str, payload: str
    ) -> WebAttackResult:
        """Test a single payload against target."""
        url = self._inject_payload(payload)
        start_time = datetime.now()

        try:
            async with session.get(url) as response:
                body = await response.text()
                elapsed = (datetime.now() - start_time).total_seconds()

                success, evidence = self._detect_vulnerability(
                    vector, body, response.status
                )

                return WebAttackResult(
                    success=success,
                    vector=vector,
                    payload=payload,
                    response_code=response.status,
                    response_body=body[:500],
                    response_time=elapsed,
                    evidence=evidence,
                )

        except asyncio.TimeoutError:
            return WebAttackResult(
                success=False,
                vector=vector,
                payload=payload,
                response_code=0,
                response_body="Timeout",
                response_time=self.config.timeout,
            )
        except Exception as e:
            self.last_error = str(e)
            return WebAttackResult(
                success=False,
                vector=vector,
                payload=payload,
                response_code=0,
                response_body=str(e),
                response_time=0,
            )

    def _inject_payload(self, payload: str) -> str:
        """Inject payload into target URL parameter."""
        parsed = urlparse(self.config.target_url)
        query = parse_qs(parsed.query)
        query[self.config.target_param] = [payload]

        new_query = urlencode(query, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def _detect_vulnerability(
        self, vector: str, body: str, status: int
    ) -> tuple[bool, Optional[str]]:
        """Detect if response indicates vulnerability."""
        body_lower = body.lower()
        patterns = self.SUCCESS_PATTERNS.get(vector, [])

        for pattern in patterns:
            if pattern.lower() in body_lower:
                return True, f"Pattern matched: {pattern}"

        # Time-based detection (for blind injection)
        # TODO: implement timing analysis

        return False, None

    def _generate_report(self) -> Dict[str, Any]:
        """Generate attack report."""
        successes = [r for r in self.results if r.success]
        return {
            "target": self.config.target_url,
            "started_at": self.started_at.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "iterations": self.iteration,
            "successful_attacks": len(successes),
            "success_rate": len(successes) / max(len(self.results), 1),
            "vulnerabilities": [
                {
                    "vector": r.vector,
                    "payload": r.payload,
                    "evidence": r.evidence,
                    "response_code": r.response_code,
                }
                for r in successes
            ],
            "vectors_tested": list(self.payloads.keys()),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current status."""
        time_remaining = 0
        if self.deadline:
            remaining = (self.deadline - datetime.now()).total_seconds() / 60
            time_remaining = max(0, int(remaining))

        return {
            "state": self.state.value,
            "iteration": self.iteration,
            "time_remaining": time_remaining,
            "successful_attacks": len([r for r in self.results if r.success]),
            "total_attempts": len(self.results),
            "current_payload": self.current_payload,
            "current_category": self.current_vector,
            "last_error": self.last_error,
        }

    def pause(self):
        """Pause attack."""
        self.state = WebAttackState.PAUSED

    def resume(self):
        """Resume attack."""
        self.state = WebAttackState.RUNNING

    def stop(self):
        """Stop attack."""
        self.state = WebAttackState.COMPLETED
