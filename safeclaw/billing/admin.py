"""
SafeClaw Billing — Django Admin Configuration.

Per billing_spec.md v1.1 (Approved 2026-02-10).
BillingEvent admin enforces immutability (no edit/delete).
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import BillingEvent, Subscription, UsageLog, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "telegram_id", "short_api_hash", "created_at"]
    search_fields = ["email", "telegram_id"]
    readonly_fields = ["id", "api_key_hash", "created_at"]
    list_filter = ["created_at"]

    def short_api_hash(self, obj: User) -> str:
        """Show first 8 chars of API key hash for identification."""
        return f"{obj.api_key_hash[:8]}…"

    short_api_hash.short_description = "API Key Hash"


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "plan",
        "status",
        "tokens_used_display",
        "tokens_limit",
        "usage_badge",
        "expires_at",
    ]
    list_filter = ["plan", "status"]
    search_fields = ["user__email", "user__telegram_id"]
    readonly_fields = ["id", "started_at", "events_count"]
    actions = ["suspend_selected", "activate_selected", "reset_tokens"]

    def tokens_used_display(self, obj: Subscription) -> str:
        return f"{obj.tokens_used:,}"

    tokens_used_display.short_description = "Tokens Used"

    def usage_badge(self, obj: Subscription) -> str:
        """Color-coded usage percentage badge."""
        pct = obj.usage_percent
        if pct >= 100:
            color = "#dc3545"  # red
        elif pct >= 80:
            color = "#ffc107"  # yellow
        else:
            color = "#28a745"  # green
        if obj.tokens_limit == -1:
            return format_html('<span style="color: #28a745">∞</span>')
        return format_html(
            '<span style="color: {}">{:.0f}%</span>',
            color,
            pct,
        )

    usage_badge.short_description = "Usage"

    def events_count(self, obj: Subscription) -> int:
        return obj.events.count()

    events_count.short_description = "Total Events"

    @admin.action(description="⏸ Suspend selected subscriptions")
    def suspend_selected(self, request, queryset):
        from .plans import SubscriptionStatus

        updated = queryset.exclude(
            status=SubscriptionStatus.CANCELLED,
        ).update(status=SubscriptionStatus.SUSPENDED)
        self.message_user(request, f"{updated} subscriptions suspended.")

    @admin.action(description="▶ Activate selected subscriptions")
    def activate_selected(self, request, queryset):
        from .plans import SubscriptionStatus

        updated = queryset.exclude(
            status=SubscriptionStatus.CANCELLED,
        ).update(status=SubscriptionStatus.ACTIVE)
        self.message_user(request, f"{updated} subscriptions activated.")

    @admin.action(description="🔄 Reset token counters")
    def reset_tokens(self, request, queryset):
        updated = queryset.update(tokens_used=0)
        self.message_user(request, f"Reset tokens for {updated} subscriptions.")


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    """
    Read-only admin for billing events.
    Events are IMMUTABLE — no edit, no delete.
    """

    list_display = [
        "event_type",
        "subscription",
        "amount_display",
        "currency",
        "created_at",
    ]
    list_filter = ["event_type", "currency", "created_at"]
    search_fields = [
        "subscription__user__email",
        "yokassa_payment_id",
        "idempotency_key",
    ]
    readonly_fields = [
        "id",
        "subscription",
        "event_type",
        "amount_kopecks",
        "currency",
        "yokassa_payment_id",
        "idempotency_key",
        "metadata_json",
        "created_at",
    ]

    def amount_display(self, obj: BillingEvent) -> str:
        if obj.amount_kopecks is None:
            return "—"
        return f"{obj.amount_kopecks / 100:.2f}₽"

    amount_display.short_description = "Amount"

    def has_add_permission(self, request) -> bool:
        return False  # Events are created programmatically only

    def has_change_permission(self, request, obj=None) -> bool:
        return False  # IMMUTABLE

    def has_delete_permission(self, request, obj=None) -> bool:
        return False  # IMMUTABLE


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = [
        "subscription",
        "tokens_total_display",
        "model_used",
        "cost_display",
        "timestamp",
    ]
    list_filter = ["model_used", "timestamp"]
    search_fields = ["subscription__user__email"]
    readonly_fields = [
        "id",
        "subscription",
        "tokens_input",
        "tokens_output",
        "model_used",
        "cost_kopecks",
        "timestamp",
    ]

    def tokens_total_display(self, obj: UsageLog) -> str:
        return f"{obj.tokens_total:,}"

    tokens_total_display.short_description = "Total Tokens"

    def cost_display(self, obj: UsageLog) -> str:
        return f"{obj.cost_kopecks / 100:.2f}₽"

    cost_display.short_description = "Cost"

    def has_add_permission(self, request) -> bool:
        return False  # Logs are created via API only

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
