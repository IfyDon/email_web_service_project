"""
Place: apps/suppressions/serializers.py
"""

from rest_framework import serializers
from .models import Suppression


class SuppressionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Suppression
        fields = [
            "id", "email", "reason",
            "source_message_id", "description",
            "created_at",
        ]
        read_only_fields = [
            "id", "email_hash", "source_message_id", "created_at"
        ]


class SuppressionCreateSerializer(serializers.Serializer):
    """POST /api/v1/suppressions/ — manual add."""
    email       = serializers.EmailField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class SuppressionDeleteSerializer(serializers.Serializer):
    """DELETE body — remove by email address."""
    email = serializers.EmailField()