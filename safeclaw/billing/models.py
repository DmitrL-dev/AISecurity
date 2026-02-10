"""
SafeClaw Billing — Django ORM Models.

Per billing_spec.md v1.1 (Approved 2026-02-10).
Event sourcing: BillingEvent is immutable (INSERT only, no UPDATE/DELETE).
"""

import hashlib
import secrets
import uuid

from django.db import models
from django.utils import timezone

from .plans import BillingEventType, PlanType, SubscriptionStatus, PLANS


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class User(models.Model):
    """SafeClaw API user. Identified by email or Telegram ID."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    api_key_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="SHA-256 hash of API key. Original shown once at registration.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_users"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email__isnull=False)
                | models.Q(telegram_id__isnull=False),
                name="user_has_email_or_telegram",
            ),
        ]

    def __str__(self) -> str:
        return self.email or f"tg:{self.telegram_id}"

    @staticmethod
    def generate_api_key() -> tuple[str, str]:
        """Generate a new API key. Returns (raw_key, sha256_hash)."""
        raw_key = f"sc_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        return raw_key, key_hash

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        """Hash an API key for lookup."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @property
    def is_authenticated(self) -> bool:
        """Required by DRF IsAuthenticated permission."""
        return True


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------


class Subscription(models.Model):
    """User subscription with token limits and plan tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="subscription",
    )
    plan = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.FREE,
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    tokens_limit = models.IntegerField(
        help_text="-1 = unlimited",
    )
    yokassa_payment_method_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Saved payment method for recurring payments.",
    )

    class Meta:
        db_table = "billing_subscriptions"

    def __str__(self) -> str:
        return f"{self.user} — {self.get_plan_display()} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Auto-set tokens_limit from plan config if not explicitly set
        if self.tokens_limit is None:
            plan_config = PLANS.get(self.plan)
            if plan_config:
                self.tokens_limit = plan_config.tokens_monthly
        super().save(*args, **kwargs)

    @property
    def tokens_remaining(self) -> int | float:
        """Tokens remaining in current billing period. float('inf') for unlimited."""
        if self.tokens_limit == -1:
            return float("inf")
        return max(0, self.tokens_limit - self.tokens_used)

    @property
    def usage_percent(self) -> float:
        """Usage percentage (0.0 - 100.0). Returns 0 for unlimited plans."""
        if self.tokens_limit <= 0:
            return 0.0
        return min(100.0, (self.tokens_used / self.tokens_limit) * 100)

    @property
    def is_over_limit(self) -> bool:
        """Whether user has exceeded token limit."""
        if self.tokens_limit == -1:
            return False
        return self.tokens_used >= self.tokens_limit


# ---------------------------------------------------------------------------
# BillingEvent (Immutable — Event Sourcing)
# ---------------------------------------------------------------------------


class BillingEvent(models.Model):
    """
    Immutable event log for all billing operations.

    NEVER UPDATE, only INSERT. This ensures complete audit trail
    for every financial operation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=40,
        choices=BillingEventType.choices,
    )
    amount_kopecks = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Amount in kopecks (1₽ = 100 kopecks).",
    )
    currency = models.CharField(max_length=3, default="RUB")
    yokassa_payment_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="ЮKassa payment ID for cross-reference.",
    )
    idempotency_key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Prevents duplicate event processing.",
    )
    metadata_json = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional event metadata (plan changes, error details, etc).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_events"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        amount = f" {self.amount_kopecks / 100:.2f}₽" if self.amount_kopecks else ""
        return f"{self.get_event_type_display()}{amount} @ {self.created_at:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        """Enforce immutability — prevent updates to existing events."""
        if self.pk and BillingEvent.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "BillingEvents are immutable — cannot update existing events. "
                "Create a new event instead."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of billing events."""
        raise ValueError(
            "BillingEvents are immutable — cannot delete. "
            "This ensures complete audit trail."
        )


# ---------------------------------------------------------------------------
# UsageLog
# ---------------------------------------------------------------------------


class UsageLog(models.Model):
    """Per-request token usage tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.PROTECT,
        related_name="usage_logs",
    )
    tokens_input = models.PositiveIntegerField(
        help_text="Number of input tokens consumed.",
    )
    tokens_output = models.PositiveIntegerField(
        help_text="Number of output tokens generated.",
    )
    model_used = models.CharField(
        max_length=100,
        help_text="LLM model identifier (e.g. 'gigachat-lite', 'deepseek-v3').",
    )
    cost_kopecks = models.PositiveIntegerField(
        help_text="Our cost for this request in kopecks.",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "billing_usage_logs"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        total = self.tokens_input + self.tokens_output
        return f"{total} tokens ({self.model_used}) @ {self.timestamp:%H:%M:%S}"

    @property
    def tokens_total(self) -> int:
        return self.tokens_input + self.tokens_output
