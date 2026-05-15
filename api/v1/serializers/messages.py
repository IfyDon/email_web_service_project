"""
Serializers for message list / detail endpoints.

Place: api/v1/serializers/messages.py
"""

from rest_framework import serializers
from apps.email_messages.models import Message, MessageAttempt
from apps.events.models import MessageEvent


class MessageAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MessageAttempt
        fields = [
            "id", "attempt_no", "success",
            "error", "esp_response", "attempted_at",
        ]
        read_only_fields = fields


class MessageEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = MessageEvent
        fields = [
            "id", "event_type", "occurred_at",
            "ip_address", "user_agent", "location",
            "clicked_url", "raw_payload",
        ]
        read_only_fields = fields


class MessageListSerializer(serializers.ModelSerializer):
    """Compact — used in paginated list."""

    class Meta:
        model  = Message
        fields = [
            "id", "from_email", "to_email",
            "subject", "status",
            "attempt_count", "queued_at", "sent_at",
            "created_at",
        ]
        read_only_fields = fields


class MessageDetailSerializer(serializers.ModelSerializer):
    """Full detail including events + attempts."""

    events   = MessageEventSerializer(many=True, read_only=True)
    attempts = MessageAttemptSerializer(many=True, read_only=True)

    class Meta:
        model  = Message
        fields = [
            "id",
            "from_email", "from_name",
            "to_email",   "to_name",
            "reply_to", "subject",
            "body_html", "body_text",
            "template", "domain",
            "tags", "metadata",
            "status", "esp_message_id",
            "attempt_count", "max_attempts",
            "queued_at", "sent_at", "delivered_at",
            "created_at", "updated_at",
            "events", "attempts",
        ]
        read_only_fields = fields
