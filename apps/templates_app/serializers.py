"""
DRF serializers for the email templates app.

Place: apps/templates_app/serializers.py
"""

from rest_framework import serializers
from .models import EmailTemplate, TemplateVersion


# ── Version ───────────────────────────────────────────────────────────────────

class TemplateVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TemplateVersion
        fields = [
            "id", "version_number", "subject",
            "body_html", "body_text", "body_mjml",
            "created_at",
        ]
        read_only_fields = fields


# ── Template list ─────────────────────────────────────────────────────────────

class EmailTemplateListSerializer(serializers.ModelSerializer):
    """Compact — used in list views."""

    class Meta:
        model  = EmailTemplate
        fields = [
            "id", "name", "slug", "subject", "description",
            "body_type", "is_active", "current_version",
            "variable_schema", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "is_active",
            "current_version", "created_at", "updated_at",
        ]


# ── Template detail ───────────────────────────────────────────────────────────

class EmailTemplateDetailSerializer(serializers.ModelSerializer):
    """Full — includes version history."""

    versions = TemplateVersionSerializer(many=True, read_only=True)

    class Meta:
        model  = EmailTemplate
        fields = [
            "id", "name", "slug", "description",
            "subject", "body_type",
            "body_html", "body_text", "body_mjml",
            "variable_schema", "is_active",
            "current_version", "versions",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "body_type", "is_active",
            "current_version", "versions",
            "created_at", "updated_at",
        ]


# ── Create ────────────────────────────────────────────────────────────────────

class EmailTemplateCreateSerializer(serializers.Serializer):
    """POST /api/v1/templates/"""

    name            = serializers.CharField(max_length=200)
    description     = serializers.CharField(required=False, allow_blank=True, default="")
    subject         = serializers.CharField(max_length=998)
    body_html       = serializers.CharField(required=False, allow_blank=True, default="")
    body_mjml       = serializers.CharField(required=False, allow_blank=True, default="")
    body_text       = serializers.CharField(required=False, allow_blank=True, default="")
    variable_schema = serializers.DictField(
        child=serializers.CharField(), required=False, default=dict
    )

    def validate(self, attrs):
        if not attrs.get("body_html") and not attrs.get("body_mjml"):
            raise serializers.ValidationError(
                "Provide either body_html or body_mjml."
            )
        return attrs


# ── Update ────────────────────────────────────────────────────────────────────

class EmailTemplateUpdateSerializer(serializers.Serializer):
    """PUT/PATCH /api/v1/templates/<id>/"""

    name            = serializers.CharField(max_length=200,  required=False)
    description     = serializers.CharField(required=False,  allow_blank=True)
    subject         = serializers.CharField(max_length=998,  required=False)
    body_html       = serializers.CharField(required=False,  allow_blank=True)
    body_mjml       = serializers.CharField(required=False,  allow_blank=True)
    body_text       = serializers.CharField(required=False,  allow_blank=True)
    variable_schema = serializers.DictField(
        child=serializers.CharField(), required=False
    )


# ── Preview ───────────────────────────────────────────────────────────────────

class TemplatePreviewSerializer(serializers.Serializer):
    """POST /api/v1/templates/<id>/preview/"""

    context = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
        help_text="Variable values to substitute. Missing keys use [placeholder] syntax.",
    )


class TemplatePreviewResponseSerializer(serializers.Serializer):
    subject   = serializers.CharField()
    body_html = serializers.CharField()
    body_text = serializers.CharField()


# ── Restore version ───────────────────────────────────────────────────────────

class TemplateRestoreSerializer(serializers.Serializer):
    """POST /api/v1/templates/<id>/restore/"""

    version_number = serializers.IntegerField(min_value=1)