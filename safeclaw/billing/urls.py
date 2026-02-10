"""
SafeClaw Billing — URL Configuration.

Per billing_spec.md v1.1 §3.5.
All billing API endpoints under /api/billing/.
"""

from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    # Public
    path(
        "plans/",
        views.PlanListView.as_view(),
        name="plan-list",
    ),
    # Authenticated
    path(
        "subscription/",
        views.SubscriptionView.as_view(),
        name="subscription",
    ),
    path(
        "usage/",
        views.UsageView.as_view(),
        name="usage",
    ),
    path(
        "history/",
        views.BillingHistoryView.as_view(),
        name="history",
    ),
    path(
        "pay/",
        views.CreatePaymentView.as_view(),
        name="create-payment",
    ),
    path(
        "upgrade/",
        views.UpgradePlanView.as_view(),
        name="upgrade",
    ),
    path(
        "cancel/",
        views.CancelSubscriptionView.as_view(),
        name="cancel",
    ),
    path(
        "refund/",
        views.RefundView.as_view(),
        name="refund",
    ),
    # Webhook
    path(
        "webhook/yokassa/",
        views.YoKassaWebhookView.as_view(),
        name="yokassa-webhook",
    ),
]
