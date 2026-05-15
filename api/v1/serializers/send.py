"""
DRF serializers for the /v1/send and /v1/send/bulk endpoints.

Place: api/v1/serializers/send.py
"""

from rest_framework import serializers


# ── Single send ───────────────────────────────────────────────────────────────

class SendSerializer(serializers.Serializer):
    """POST /api/v1/send"""

    # Addressing
    to_email      = serializers.EmailField()
    to_name       = serializers.CharField(max_length=255,  required=False, default="")
    from_email    = serializers.EmailField(required=False, allow_blank=True, default="")
    from_name     = serializers.CharField(max_length=255,  required=False, default="")
    reply_to      = serializers.EmailField(required=False, allow_blank=True, default="")

    # Content — either body or template_id must be supplied
    subject       = serializers.CharField(max_length=998,  required=False, default="")
    body_html     = serializers.CharField(required=False,  allow_blank=True, default="")
    body_text     = serializers.CharField(required=False,  allow_blank=True, default="")

    # Template (alternative to inline body)
    template_id   = serializers.UUIDField(required=False,  allow_null=True, default=None)
    template_context = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )

    # Routing
    domain_id     = serializers.UUIDField(required=False, allow_null=True, default=None)

    # Options
    tags          = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    metadata      = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )
    track_opens   = serializers.BooleanField(required=False, default=True)
    track_clicks  = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        has_body     = attrs.get("body_html") or attrs.get("body_text")
        has_template = bool(attrs.get("template_id"))

        if not has_body and not has_template:
            raise serializers.ValidationError(
                "Provide body_html / body_text or a template_id."
            )
        if not has_template and not attrs.get("subject"):
            raise serializers.ValidationError(
                "subject is required when not using a template."
            )
        return attrs


# ── Bulk send ─────────────────────────────────────────────────────────────────

class BulkRecipientSerializer(serializers.Serializer):
    """One entry in the recipients array for /v1/send/bulk."""

    to_email  = serializers.EmailField()
    to_name   = serializers.CharField(max_length=255, required=False, default="")
    subject   = serializers.CharField(max_length=998, required=False, default="")
    body_html = serializers.CharField(required=False, allow_blank=True, default="")
    body_text = serializers.CharField(required=False, allow_blank=True, default="")
    context   = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )


class BulkSendSerializer(serializers.Serializer):
    """POST /api/v1/send/bulk"""

    recipients    = BulkRecipientSerializer(many=True, min_length=1, max_length=1000)
    from_email    = serializers.EmailField(required=False, allow_blank=True, default="")
    from_name     = serializers.CharField(max_length=255, required=False, default="")
    subject       = serializers.CharField(max_length=998, required=False, default="")
    body_html     = serializers.CharField(required=False, allow_blank=True, default="")
    body_text     = serializers.CharField(required=False, allow_blank=True, default="")
    template_id   = serializers.UUIDField(required=False, allow_null=True, default=None)
    domain_id     = serializers.UUIDField(required=False, allow_null=True, default=None)
    tags          = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    track_opens   = serializers.BooleanField(required=False, default=True)
    track_clicks  = serializers.BooleanField(required=False, default=True)


# ── Response ──────────────────────────────────────────────────────────────────

class SendResponseSerializer(serializers.Serializer):
    """Returned immediately after queuing."""
    message_id   = serializers.UUIDField()
    status       = serializers.CharField()
    queued_at    = serializers.DateTimeField()


class BulkSendResponseSerializer(serializers.Serializer):
    queued    = serializers.IntegerField()
    skipped   = serializers.IntegerField()
    messages  = SendResponseSerializer(many=True)