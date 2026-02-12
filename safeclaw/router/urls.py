"""
SafeClaw Router — URL Configuration.

Per router_spec.md v1.0.
"""

from django.urls import path

from . import views

app_name = "router"

urlpatterns = [
    # Chat completion
    path(
        "chat/",
        views.ChatView.as_view(),
        name="chat",
    ),
    # Provider info
    path(
        "providers/",
        views.ProviderListView.as_view(),
        name="provider-list",
    ),
    path(
        "providers/health/",
        views.HealthCheckView.as_view(),
        name="provider-health",
    ),
]
