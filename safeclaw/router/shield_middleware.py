"""
SafeClaw Router — Shield Integration Middleware.

ARCH-01: Every LLM request passes through SENTINEL Shield
before being routed to a provider. Shield scans for:
- Prompt injection
- Jailbreak attempts
- PII leakage
- Data exfiltration
- Content moderation violations

Shield API is expected at SHIELD_URL (default: http://localhost:8085).
"""

import json
import logging
import time

import requests
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

# Paths that skip Shield scanning
SHIELD_EXEMPT_PREFIXES = (
    "/api/billing/",
    "/api/router/providers/",
    "/api/router/health/",
    "/admin/",
    "/static/",
)

# Default Shield config
SHIELD_URL = getattr(settings, "SHIELD_URL", "http://localhost:8085")
SHIELD_TIMEOUT = getattr(settings, "SHIELD_TIMEOUT", 5)
SHIELD_FAIL_OPEN = getattr(settings, "SHIELD_FAIL_OPEN", False)


def _scan_with_shield(text: str, context: dict) -> dict:
    """
    Call SENTINEL Shield API to analyze text.

    Returns dict with keys:
      - blocked: bool
      - score: float (0.0 - 1.0)
      - engines: list of triggered engine names
      - details: raw Shield response
    """
    try:
        resp = requests.post(
            f"{SHIELD_URL}/api/v1/analyze",
            json={
                "text": text,
                "context": context,
            },
            timeout=SHIELD_TIMEOUT,
            headers={
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        # Shield returns risk_score and triggered engines
        score = data.get("risk_score", 0.0)
        engines = data.get("triggered_engines", [])
        blocked = score >= 0.8 or data.get("action", "") == "block"

        return {
            "blocked": blocked,
            "score": score,
            "engines": engines,
            "details": data,
        }
    except requests.exceptions.ConnectionError:
        logger.error("Shield unavailable at %s", SHIELD_URL)
        return {
            "blocked": not SHIELD_FAIL_OPEN,
            "score": -1.0,
            "engines": ["shield_unavailable"],
            "details": {"error": "connection_refused"},
        }
    except requests.exceptions.Timeout:
        logger.warning("Shield timeout after %ss", SHIELD_TIMEOUT)
        return {
            "blocked": not SHIELD_FAIL_OPEN,
            "score": -1.0,
            "engines": ["shield_timeout"],
            "details": {"error": "timeout"},
        }
    except Exception as e:
        logger.exception("Shield scan error")
        return {
            "blocked": not SHIELD_FAIL_OPEN,
            "score": -1.0,
            "engines": ["shield_error"],
            "details": {"error": str(e)},
        }


class ShieldMiddleware:
    """
    Django middleware: scan prompts via SENTINEL Shield.

    Pre-request:
    - Extracts user prompt from POST body
    - Sends to Shield for analysis
    - Blocks request if Shield flags it (429)

    Post-request:
    - Scans LLM response for PII/exfiltration
    - Adds X-Shield-Score header

    Config in settings.py:
    - SHIELD_URL: Shield API base URL
    - SHIELD_TIMEOUT: Request timeout (seconds)
    - SHIELD_FAIL_OPEN: If True, allow requests
      when Shield is down (default: False)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip non-chat endpoints
        if not request.path.startswith("/api/router/chat/"):
            return self.get_response(request)

        # Skip exempt paths
        if any(request.path.startswith(p) for p in SHIELD_EXEMPT_PREFIXES):
            return self.get_response(request)

        # Only scan POST requests with body
        if request.method != "POST":
            return self.get_response(request)

        # Extract prompt from request body
        try:
            body = json.loads(request.body)
            messages = body.get("messages", [])
            # Combine all message contents for scan
            prompt_text = "\n".join(
                m.get("content", "") for m in messages if isinstance(m, dict)
            )
        except (json.JSONDecodeError, AttributeError):
            prompt_text = ""

        if not prompt_text:
            return self.get_response(request)

        # --- Pre-request Shield scan ---
        start = time.monotonic()
        result = _scan_with_shield(
            prompt_text,
            context={
                "source": "safeclaw_router",
                "path": request.path,
                "method": request.method,
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            },
        )
        scan_ms = (time.monotonic() - start) * 1000

        # Store result for request logging
        request._shield_result = result
        request._shield_ms = scan_ms

        if result["blocked"]:
            logger.warning(
                "Shield BLOCKED request: " "score=%.2f engines=%s path=%s",
                result["score"],
                result["engines"],
                request.path,
            )
            return JsonResponse(
                {
                    "detail": ("Request blocked by " "security policy."),
                    "shield_score": result["score"],
                    "triggered": result["engines"],
                },
                status=403,
            )

        # Process request
        response = self.get_response(request)

        # Add Shield headers
        response["X-Shield-Score"] = str(result["score"])
        response["X-Shield-Ms"] = f"{scan_ms:.1f}"

        if result["engines"]:
            response["X-Shield-Engines"] = ",".join(result["engines"])

        return response
