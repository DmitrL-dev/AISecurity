"""
SafeClaw Router — API Views.

Per router_spec.md v1.0.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.auth import APIKeyAuthentication

from .engine import get_engine
from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ProviderHealthSerializer,
    ProviderSerializer,
)

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """POST /api/chat/ — Send chat completion request."""

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChatRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        engine = get_engine()

        try:
            result = engine.route(
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in data["messages"]
                ],
                model=data["model"],
                strategy=data["strategy"],
                temperature=data["temperature"],
                max_tokens=data["max_tokens"],
                provider_key=data.get("provider_key"),
            )
        except ValueError as e:
            logger.warning("Invalid model request: %s", e)
            return Response(
                {"detail": "Invalid model or parameters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RuntimeError as e:
            logger.exception("All providers failed")
            return Response(
                {"detail": "Service temporarily unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Set token headers for billing middleware
        response_data = {
            "content": result.content,
            "model": result.model,
            "provider": result.provider,
            "usage": {
                "input_tokens": result.tokens_input,
                "output_tokens": result.tokens_output,
                "total_tokens": result.tokens_total,
                "cost_kopecks": result.cost_kopecks,
            },
            "latency_ms": result.latency_ms,
        }

        resp = Response(response_data, status=status.HTTP_200_OK)
        resp["X-Tokens-Input"] = str(result.tokens_input)
        resp["X-Tokens-Output"] = str(result.tokens_output)
        return resp


class ProviderListView(APIView):
    """GET /api/providers/ — List available providers."""

    permission_classes = [AllowAny]

    def get(self, request):
        engine = get_engine()
        models = engine.available_models
        ser = ProviderSerializer(models, many=True)
        return Response(ser.data)


class HealthCheckView(APIView):
    """GET /api/providers/health/ — Provider health status."""

    authentication_classes = [APIKeyAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        engine = get_engine()
        health_list = engine.health_check_all()
        data = []
        for h in health_list:
            data.append(
                {
                    "name": h.name,
                    "available": h.available,
                    "latency_ms": h.latency_ms,
                    "models": h.models,
                    "error": h.error,
                }
            )
        ser = ProviderHealthSerializer(data, many=True)
        return Response(ser.data)
