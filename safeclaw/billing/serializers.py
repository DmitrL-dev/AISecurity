"""
SafeClaw Billing — DRF Serializers.

Per billing_spec.md v1.1 §3.5.
Read-only serializers for API responses, write serializers for actions.
"""

from rest_framework import serializers

from .models import BillingEvent, Subscription, UsageLog
from .plans import PlanType, PLANS


class PlanSerializer(serializers.Serializer):
    """Plan configuration (read-only)."""

    name = serializers.CharField()
    price_kopecks = serializers.IntegerField()
    price_rub = serializers.FloatField()
    tokens_monthly = serializers.IntegerField()
    max_agents = serializers.IntegerField()
    features = serializers.ListField(child=serializers.CharField())


class SubscriptionSerializer(serializers.ModelSerializer):
    """Current subscription details."""

    tokens_remaining = serializers.ReadOnlyField()
    usage_percent = serializers.ReadOnlyField()
    is_over_limit = serializers.ReadOnlyField()
    plan_display = serializers.CharField(
        source="get_plan_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "plan_display",
            "status",
            "status_display",
            "started_at",
            "expires_at",
            "tokens_used",
            "tokens_limit",
            "tokens_remaining",
            "usage_percent",
            "is_over_limit",
        ]
        read_only_fields = fields


class BillingEventSerializer(serializers.ModelSerializer):
    """Billing event (read-only audit trail)."""

    event_type_display = serializers.CharField(
        source="get_event_type_display",
        read_only=True,
    )
    amount_rub = serializers.SerializerMethodField()

    class Meta:
        model = BillingEvent
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "amount_kopecks",
            "amount_rub",
            "currency",
            "created_at",
            "metadata_json",
        ]
        read_only_fields = fields

    def get_amount_rub(self, obj) -> float | None:
        if obj.amount_kopecks:
            return obj.amount_kopecks / 100
        return None


class UsageLogSerializer(serializers.ModelSerializer):
    """Usage log entry (read-only)."""

    tokens_total = serializers.ReadOnlyField()

    class Meta:
        model = UsageLog
        fields = [
            "id",
            "tokens_input",
            "tokens_output",
            "tokens_total",
            "model_used",
            "cost_kopecks",
            "timestamp",
        ]
        read_only_fields = fields


class CreatePaymentSerializer(serializers.Serializer):
    """Request body for creating a payment."""

    plan = serializers.ChoiceField(
        choices=[(p, p) for p in PLANS.keys() if p != PlanType.FREE],
    )
    return_url = serializers.URLField(required=False)


class UpgradePlanSerializer(serializers.Serializer):
    """Request body for upgrading/downgrading plan."""

    new_plan = serializers.ChoiceField(
        choices=[(p, p) for p in PLANS.keys()],
    )
