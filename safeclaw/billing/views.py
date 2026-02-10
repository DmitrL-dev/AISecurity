"""
SafeClaw Billing — DRF Views (APIViews).

Per billing_spec.md v1.1 §3.5, §5 Phase 5.
REST API endpoints for subscription management, billing, and usage.
"""

import base64
import ipaddress
import logging

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth import APIKeyAuthentication
from .lifecycle import (
    InvalidTransitionError,
    cancel,
    upgrade,
)
from .metering import get_usage_stats
from .models import BillingEvent, Subscription
from .plans import PLANS
from .serializers import (
    BillingEventSerializer,
    CreatePaymentSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    UpgradePlanSerializer,
)
from .yokassa import (
    create_payment,
    create_refund,
    parse_webhook,
)
from .webhooks import process_webhook

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public endpoints (no auth)
# ---------------------------------------------------------------------------


class PlanListView(APIView):
    """
    GET /api/billing/plans/
    List all available plans.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = []
        for plan in PLANS.values():
            plans.append(
                {
                    "name": plan.name,
                    "price_kopecks": plan.price_kopecks,
                    "price_rub": plan.price_rub,
                    "tokens_monthly": plan.tokens_monthly,
                    "max_agents": plan.max_agents,
                    "features": sorted(plan.features),
                }
            )
        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


class SubscriptionView(APIView):
    """
    GET /api/billing/subscription/
    Get current user's subscription.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(
                user=request.user,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data)


class UsageView(APIView):
    """
    GET /api/billing/usage/
    Get current token usage statistics.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            sub = Subscription.objects.get(
                user=request.user,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        stats = get_usage_stats(sub)
        return Response(stats)


class BillingHistoryView(generics.ListAPIView):
    """
    GET /api/billing/history/
    List billing events for current user.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BillingEventSerializer

    def get_queryset(self):
        return BillingEvent.objects.filter(
            subscription__user=self.request.user,
        ).order_by("-created_at")


class CreatePaymentView(APIView):
    """
    POST /api/billing/pay/
    Create a new payment for plan subscription.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        plan_name = serializer.validated_data["plan"]
        plan_config = PLANS[plan_name]
        return_url = serializer.validated_data.get(
            "return_url",
        )

        # Get or create subscription
        sub, _ = Subscription.objects.get_or_create(
            user=request.user,
            defaults={
                "plan": plan_name,
                "tokens_limit": plan_config.tokens_monthly,
            },
        )

        # Update plan if different
        if sub.plan != plan_name:
            sub.plan = plan_name
            sub.tokens_limit = plan_config.tokens_monthly
            sub.save()

        try:
            result = create_payment(
                amount_kopecks=plan_config.price_kopecks,
                description=f"SafeClaw {plan_config.name} plan",
                return_url=return_url,
                metadata={
                    "subscription_id": str(sub.pk),
                    "plan": plan_name,
                },
            )
        except Exception as e:
            logger.exception("Payment creation failed")
            return Response(
                {"detail": f"Payment error: {e}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "payment_id": result.payment_id,
                "confirmation_url": result.confirmation_url,
                "status": result.status,
            },
            status=status.HTTP_201_CREATED,
        )


class UpgradePlanView(APIView):
    """
    POST /api/billing/upgrade/
    Upgrade or downgrade subscription plan.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = UpgradePlanSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        new_plan = serializer.validated_data["new_plan"]

        try:
            sub = Subscription.objects.get(
                user=request.user,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            sub = upgrade(sub, new_plan)
        except InvalidTransitionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_409_CONFLICT,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data)


class CancelSubscriptionView(APIView):
    """
    POST /api/billing/cancel/
    Cancel current subscription.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            sub = Subscription.objects.get(
                user=request.user,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            sub = cancel(sub)
        except InvalidTransitionError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = SubscriptionSerializer(sub)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Webhook (ЮKassa → SafeClaw)
# ---------------------------------------------------------------------------


# SEC-03: ЮKassa IP whitelist (official docs)
# https://yookassa.ru/docs/support/ip
_YOKASSA_IP_RANGES = [
    ipaddress.ip_network("185.71.76.0/27"),
    ipaddress.ip_network("185.71.77.0/27"),
    ipaddress.ip_network("77.75.153.0/25"),
    ipaddress.ip_network("77.75.156.11/32"),
    ipaddress.ip_network("77.75.156.35/32"),
]


def _is_yokassa_ip(request) -> bool:
    """Check if request originates from ЮKassa IP range."""
    # Support X-Forwarded-For behind reverse proxy
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        ip_str = xff.split(",")[0].strip()
    else:
        ip_str = request.META.get("REMOTE_ADDR", "")
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in _YOKASSA_IP_RANGES)


def _verify_yokassa_basic_auth(request) -> bool:
    """Verify HTTP Basic Auth: shop_id:secret_key."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
        shop_id, secret_key = decoded.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return False

    from django.conf import settings as _s

    return shop_id == _s.YOOKASSA_SHOP_ID and secret_key == _s.YOOKASSA_SECRET_KEY


class YoKassaWebhookView(APIView):
    """
    POST /api/billing/webhook/yokassa/
    Receive ЮKassa payment notifications.

    SEC-03: Validates source IP + HTTP Basic Auth.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # SEC-03a: IP whitelist
        if not _is_yokassa_ip(request):
            logger.warning(
                "Webhook from untrusted IP: %s",
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {"detail": "Forbidden"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # SEC-03b: HTTP Basic Auth verification
        if not _verify_yokassa_basic_auth(request):
            logger.warning(
                "Webhook auth failed from %s",
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {"detail": "Unauthorized"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            event = parse_webhook(request.body)
        except Exception as e:
            logger.warning("Webhook parse error: %s", e)
            return Response(
                {"detail": "Invalid notification"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = process_webhook(event)

        if result == "error":
            return Response(
                {"detail": "Processing error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Return 200 for both "processed" and "duplicate"
        return Response({"status": result})


class RefundView(APIView):
    """
    POST /api/billing/refund/
    Request a refund for a payment.

    SEC-05: Verifies payment_id belongs to requesting user.
    """

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        if not payment_id:
            return Response(
                {"detail": "payment_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount_kopecks = request.data.get(
            "amount_kopecks",
        )

        try:
            sub = Subscription.objects.get(
                user=request.user,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"detail": "No subscription found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # SEC-05: IDOR protection — verify payment
        # belongs to this user's subscription
        if not BillingEvent.objects.filter(
            subscription=sub,
            yokassa_payment_id=payment_id,
        ).exists():
            logger.warning(
                "Refund IDOR attempt: user=%s pid=%s",
                request.user.pk,
                payment_id,
            )
            return Response(
                {"detail": "Payment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            result = create_refund(
                payment_id=payment_id,
                amount_kopecks=(int(amount_kopecks) if amount_kopecks else None),
            )
        except Exception as e:
            logger.exception("Refund creation failed")
            return Response(
                {"detail": "Refund processing error."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "refund_id": result.refund_id,
                "status": result.status,
                "amount_kopecks": (result.amount_kopecks),
            },
            status=status.HTTP_201_CREATED,
        )
