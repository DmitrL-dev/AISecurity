"""
SafeClaw Router — Request Logging Model.

GAP-03: Logs every LLM request for audit trail,
analytics, and compliance (FZ-152).

Stores: user, model, provider, tokens, latency,
Shield result, and (optionally) sanitized prompt.
"""

import uuid

from django.db import models


class RequestLog(models.Model):
    """
    Immutable log of every LLM API request.

    Used for:
    - Audit trail (who asked what, when)
    - Analytics (cost, latency, provider usage)
    - Shield metrics (block rate, false positives)
    - FZ-152 compliance evidence
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Who
    user_id = models.UUIDField(
        db_index=True,
        null=True,
        blank=True,
        help_text="billing_users.id",
    )
    api_key_prefix = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="First 8 chars of API key for audit",
    )

    # What
    model_requested = models.CharField(
        max_length=128,
        help_text="Model alias from request",
    )
    model_resolved = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Actual model after alias resolution",
    )
    provider_key = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Provider that served the request",
    )
    routing_strategy = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="cost / quality / latency / failover",
    )

    # How much
    tokens_input = models.PositiveIntegerField(
        default=0,
    )
    tokens_output = models.PositiveIntegerField(
        default=0,
    )
    cost_kopecks = models.PositiveIntegerField(
        default=0,
        help_text="Estimated cost in kopecks",
    )

    # Performance
    latency_ms = models.PositiveIntegerField(
        default=0,
        help_text="Total request latency in ms",
    )
    provider_latency_ms = models.PositiveIntegerField(
        default=0,
        help_text="LLM provider response time in ms",
    )

    # Shield
    shield_score = models.FloatField(
        default=-1.0,
        help_text="-1 = not scanned, 0-1 = risk",
    )
    shield_blocked = models.BooleanField(
        default=False,
    )
    shield_engines = models.JSONField(
        default=list,
        blank=True,
        help_text="Triggered engine names",
    )
    shield_latency_ms = models.FloatField(
        default=0.0,
    )

    # Status
    status_code = models.PositiveSmallIntegerField(
        default=200,
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error details (internal only)",
    )

    # Compliance: sanitized prompt hash for dedup
    # (NOT the actual prompt — FZ-152 safe)
    prompt_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 of prompt for dedup/audit",
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "router_request_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"],
                name="idx_reqlog_user_date",
            ),
            models.Index(
                fields=["provider_key", "-created_at"],
                name="idx_reqlog_provider_date",
            ),
            models.Index(
                fields=["shield_blocked"],
                name="idx_reqlog_blocked",
            ),
        ]

    def __str__(self):
        return (
            f"RequestLog({self.model_requested}, "
            f"status={self.status_code}, "
            f"shield={self.shield_score:.2f})"
        )
