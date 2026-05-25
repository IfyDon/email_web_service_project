"""
Serializers for the statistics endpoints.

Place: api/v1/serializers/stats.py
"""

from datetime import timedelta
from rest_framework import serializers
from django.utils import timezone


class StatsQuerySerializer(serializers.Serializer):
    """
    Query-param validation for GET /api/v1/stats/ and GET /api/v1/stats/export/
    """

    from_date   = serializers.DateField(
        source="date_from",
        required=False,
        input_formats=["%Y-%m-%d"],
        help_text="Start date YYYY-MM-DD (default: 30 days ago).",
    )
    to_date     = serializers.DateField(
        source="date_to",
        required=False,
        input_formats=["%Y-%m-%d"],
        help_text="End date YYYY-MM-DD (default: today).",
    )
    granularity = serializers.ChoiceField(
        choices=["summary", "daily"],
        default="summary",
        help_text="'summary' returns aggregated totals; 'daily' adds a day-by-day breakdown.",
    )

    def validate(self, attrs):
        today     = timezone.now().date()
        date_from = attrs.pop("date_from", None) or (today - timedelta(days=30))
        date_to   = attrs.pop("date_to",   None) or today

        if date_from > date_to:
            raise serializers.ValidationError(
                {"from_date": "from_date must be on or before to_date."}
            )
        if (date_to - date_from).days > 365:
            raise serializers.ValidationError(
                {"to_date": "Date range cannot exceed 365 days."}
            )

        attrs["date_from"] = date_from
        attrs["date_to"]   = date_to
        return attrs


# ── Response sub-serializers ──────────────────────────────────────────────────

class StatsSummarySerializer(serializers.Serializer):
    """Totals block — returned in every stats response."""
    date_from      = serializers.DateField()
    date_to        = serializers.DateField()
    sent           = serializers.IntegerField()
    delivered      = serializers.IntegerField()
    opened         = serializers.IntegerField()
    clicked        = serializers.IntegerField()
    bounced        = serializers.IntegerField()
    complained     = serializers.IntegerField()
    failed         = serializers.IntegerField()
    unsubscribed   = serializers.IntegerField()
    open_rate      = serializers.FloatField(help_text="Percentage: opens / delivered × 100")
    click_rate     = serializers.FloatField(help_text="Percentage: clicks / delivered × 100")
    bounce_rate    = serializers.FloatField(help_text="Percentage: bounces / sent × 100")
    complaint_rate = serializers.FloatField(help_text="Percentage: complaints / sent × 100")


class DailyDataPointSerializer(serializers.Serializer):
    """One calendar day in the timeline array."""
    date       = serializers.DateField()
    sent       = serializers.IntegerField()
    delivered  = serializers.IntegerField()
    opened     = serializers.IntegerField()
    clicked    = serializers.IntegerField()
    bounced    = serializers.IntegerField()
    complained = serializers.IntegerField()
    failed     = serializers.IntegerField()


class TopDomainSerializer(serializers.Serializer):
    domain = serializers.CharField()
    count  = serializers.IntegerField()


class StatsResponseSerializer(serializers.Serializer):
    """
    Full stats response.

    `summary`    – always present
    `timeline`   – present when granularity=daily
    `comparison` – present when ?compare=1
    `top_domains`– always present
    """
    granularity  = serializers.CharField()
    summary      = StatsSummarySerializer()
    timeline     = DailyDataPointSerializer(many=True, required=False)
    comparison   = StatsSummarySerializer(required=False,
                                          help_text="Previous period totals (same length).")
    top_domains  = TopDomainSerializer(many=True, required=False)