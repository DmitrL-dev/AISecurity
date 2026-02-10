"""
SafeClaw Router — DRF Serializers.

Per router_spec.md v1.0.
"""

from rest_framework import serializers

from .providers.base import RoutingStrategy


class MessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["system", "user", "assistant"])
    content = serializers.CharField()


class ChatRequestSerializer(serializers.Serializer):
    messages = MessageSerializer(many=True)
    model = serializers.CharField(default="fast")
    strategy = serializers.ChoiceField(
        choices=[s.value for s in RoutingStrategy],
        default=RoutingStrategy.COST.value,
    )
    temperature = serializers.FloatField(default=0.7, min_value=0.0, max_value=2.0)
    max_tokens = serializers.IntegerField(default=4096, min_value=1, max_value=128000)
    stream = serializers.BooleanField(default=False)
    provider_key = serializers.CharField(
        required=False,
        allow_null=True,
        default=None,
    )


class UsageSerializer(serializers.Serializer):
    input_tokens = serializers.IntegerField()
    output_tokens = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    cost_kopecks = serializers.FloatField()


class ChatResponseSerializer(serializers.Serializer):
    content = serializers.CharField()
    model = serializers.CharField()
    provider = serializers.CharField()
    usage = UsageSerializer()
    latency_ms = serializers.FloatField()


class ProviderSerializer(serializers.Serializer):
    provider = serializers.CharField()
    model = serializers.CharField()
    cost_per_1k_input = serializers.FloatField()
    cost_per_1k_output = serializers.FloatField()


class ProviderHealthSerializer(serializers.Serializer):
    name = serializers.CharField()
    available = serializers.BooleanField()
    latency_ms = serializers.FloatField()
    models = serializers.ListField(child=serializers.CharField())
    error = serializers.CharField(allow_null=True, required=False)
