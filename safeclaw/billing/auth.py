"""
SafeClaw Billing — API Key Authentication Backend.

Per billing_spec.md v1.1 §3.1.
Authenticates requests via X-API-Key header using SHA-256 hash lookup.
"""

import hashlib

from django.utils.translation import gettext_lazy as _
from rest_framework import authentication, exceptions

from billing.models import User


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    API Key authentication via X-API-Key header.

    The key is hashed with SHA-256 and looked up against
    User.api_key_hash. Original key is never stored.
    """

    HEADER = "HTTP_X_API_KEY"
    SCHEME = "ApiKey"

    def authenticate(self, request):
        api_key = request.META.get(self.HEADER)
        if not api_key:
            return None  # No key — try other auth

        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            user = User.objects.get(api_key_hash=key_hash)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid API key."))

        return (user, None)

    def authenticate_header(self, request):
        return self.SCHEME
