"""
SafeClaw Billing — DRF Token Metering Middleware.

Per billing_spec.md v1.1 §3.4.
Intercepts every API request, checks quota, counts tokens,
and returns 429 when limit exceeded.
"""

import logging

from django.http import JsonResponse
from rest_framework import status as http_status  # noqa: F401

from .auth import APIKeyAuthentication
from .metering import (
    SubscriptionNotActive,
    TokenLimitExceeded,
    check_quota,
    consume_tokens,
)
from .models import Subscription

logger = logging.getLogger(__name__)

# Paths that skip metering (public or billing-internal)
EXEMPT_PREFIXES = (
    "/api/billing/",
    "/admin/",
    "/static/",
)


class TokenMeteringMiddleware:
    """
    Django middleware that meters token usage per API request.

    Flow:
    1. Authenticate via X-API-Key header
    2. Check quota (pre-flight)
    3. Let view process the request
    4. Count tokens from response (if available)
    5. Return 429 if over limit

    Token estimation:
    - Input tokens ≈ len(request.body) / 4
    - Output tokens ≈ len(response.content) / 4
    - Views can set response['X-Tokens-Input'] and
      response['X-Tokens-Output'] for exact counts.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip exempt paths
        if any(request.path.startswith(p) for p in EXEMPT_PREFIXES):
            return self.get_response(request)

        # Try to authenticate
        api_key = request.META.get("HTTP_X_API_KEY")
        if not api_key:
            return self.get_response(request)

        # Authenticate and get subscription
        auth = APIKeyAuthentication()
        try:
            result = auth.authenticate(request)
        except Exception:
            return self.get_response(request)

        if result is None:
            return self.get_response(request)

        user, _ = result

        try:
            sub = Subscription.objects.get(user=user)
        except Subscription.DoesNotExist:
            return self.get_response(request)

        # Pre-flight quota check
        if not check_quota(sub):
            return JsonResponse(
                {
                    "detail": "Token limit exceeded.",
                    "tokens_used": sub.tokens_used,
                    "tokens_limit": sub.tokens_limit,
                },
                status=429,
            )

        # Process request
        response = self.get_response(request)

        # Count tokens (exact from headers or estimated)
        tokens_input = int(response.get("X-Tokens-Input", 0))
        tokens_output = int(response.get("X-Tokens-Output", 0))

        # If view didn't set headers, estimate
        if tokens_input == 0 and tokens_output == 0:
            body_len = len(getattr(request, "body", b""))
            content_len = len(getattr(response, "content", b""))
            tokens_input = max(1, body_len // 4)
            tokens_output = max(1, content_len // 4)

        model_used = response.get("X-Model-Used", "safeclaw-api")

        try:
            consume_tokens(
                sub,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                model_used=model_used,
            )
        except TokenLimitExceeded:
            # Request already processed — log but don't
            # block (will be blocked on next request)
            logger.warning(
                "Token limit exceeded mid-request: " "user=%s",
                user.pk,
            )
        except SubscriptionNotActive:
            pass  # Inactive — metering skipped

        # Add usage headers to response
        sub.refresh_from_db()
        response["X-Tokens-Remaining"] = str(
            sub.tokens_remaining if sub.tokens_limit != -1 else "unlimited"
        )

        return response
