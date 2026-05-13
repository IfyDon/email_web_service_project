"""
DRF serializers for the domains app.

Place: apps/domains/serializers.py
"""

import re
from rest_framework import serializers
from .models import Domain


# ── Validation helper ─────────────────────────────────────────────────────────

_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
    r"[a-zA-Z]{2,}$"
)

def _validate_domain_name(value: str) -> str:
    value = value.strip().lower().rstrip(".")
    if not _DOMAIN_RE.match(value):
        raise serializers.ValidationError(
            "Enter a valid domain name (e.g. example.com)."
        )
    return value


# ── DNS record sub-serializer ─────────────────────────────────────────────────

class DNSRecordSerializer(serializers.Serializer):
    type     = serializers.CharField()
    host     = serializers.CharField()
    value    = serializers.CharField()
    purpose  = serializers.CharField()
    verified = serializers.BooleanField()


# ── Domain serializers ────────────────────────────────────────────────────────

class DomainListSerializer(serializers.ModelSerializer):
    """Compact representation used in list views."""

    class Meta:
        model  = Domain
        fields = [
            "id", "name", "status",
            "spf_verified", "dkim_verified", "dmarc_verified",
            "created_at", "verified_at",
        ]
        read_only_fields = fields


class DomainDetailSerializer(serializers.ModelSerializer):
    """Full representation including DNS records to publish."""

    dns_records = serializers.SerializerMethodField()

    class Meta:
        model  = Domain
        fields = [
            "id", "name", "status",
            "spf_verified",  "spf_last_check",
            "dkim_verified", "dkim_last_check",  "dkim_selector",
            "dmarc_verified","dmarc_last_check",
            "dns_records",
            "created_at", "verified_at",
        ]
        read_only_fields = fields

    def get_dns_records(self, obj) -> list:
        return obj.dns_records_to_publish()


class DomainCreateSerializer(serializers.Serializer):
    """POST /api/v1/domains — only accepts the domain name."""

    name = serializers.CharField(
        max_length=253,
        validators=[_validate_domain_name],
    )

    def validate_name(self, value):
        return _validate_domain_name(value)


class DomainVerifyResponseSerializer(serializers.Serializer):
    """
    Response body for GET /api/v1/domains/<id>/verify
    Mirrors DomainVerificationResult.as_dict()
    """

    class RecordResultSerializer(serializers.Serializer):
        verified = serializers.BooleanField()
        detail   = serializers.CharField()

    spf          = RecordResultSerializer()
    dkim         = RecordResultSerializer()
    dmarc        = RecordResultSerializer()
    all_verified = serializers.BooleanField()