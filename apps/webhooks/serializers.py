"""
DRF serializers for the webhooks app.

Place: apps/webhooks/serializers.py
"""

from rest_framework import serializers
from .models import Webhook, WebhookDelivery, ALL_EVENT_TYPES


# ── Delivery log ──────────────────────────────────────────────────────────────

class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model  = WebhookDelivery
        fields = [
            "id", "event_type", "message_id", "attempt_no",
            "status", "http_status", "response_body",
            "error_message", "duration_ms", "attempted_at",
        ]
        read_only_fields = fields


# ── Webhook list / detail ─────────────────────────────────────────────────────

class WebhookSerializer(serializers.ModelSerializer):
    """Used in list and detail views — never exposes the secret."""

    class Meta:
        model  = Webhook
        fields = [
            "id", "label", "url", "event_types", "is_active",
            "total_deliveries", "failed_deliveries", "last_triggered",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_deliveries", "failed_deliveries",
            "last_triggered", "created_at", "updated_at",
        ]


class WebhookCreatedSerializer(serializers.ModelSerializer):
    """
    Returned ONLY on creation — includes the secret once.
    """
    class Meta:
        model  = Webhook
        fields = [
            "id", "label", "url", "event_types",
            "secret",           # ← shown once
            "is_active", "created_at",
        ]
        read_only_fields = ["id", "secret", "is_active", "created_at"]


# ── Create / Update ───────────────────────────────────────────────────────────

class WebhookCreateSerializer(serializers.Serializer):
    """POST /api/v1/webhooks/"""
    label       = serializers.CharField(max_length=200)
    url         = serializers.URLField(max_length=2048)
    event_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ALL_EVENT_TYPES),
        required=False,
        default=list,
        help_text="Empty list subscribes to all events.",
    )


class WebhookUpdateSerializer(serializers.Serializer):
    """PATCH /api/v1/webhooks/<id>/"""
    label       = serializers.CharField(max_length=200, required=False)
    url         = serializers.URLField(max_length=2048, required=False)
    event_types = serializers.ListField(
        child=serializers.ChoiceField(choices=ALL_EVENT_TYPES),
        required=False,
    )
    is_active   = serializers.BooleanField(required=False)


# ── Test delivery ─────────────────────────────────────────────────────────────

class WebhookTestResponseSerializer(serializers.Serializer):
    success     = serializers.BooleanField()
    http_status = serializers.IntegerField(allow_null=True)
    body        = serializers.CharField(allow_blank=True)
    duration_ms = serializers.IntegerField()
    error       = serializers.CharField(allow_blank=True)