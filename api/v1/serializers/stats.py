"""
Serializers for the stats endpoint.

Place: api/v1/serializers/stats.py
"""

from rest_framework import serializers


class StatsQuerySerializer(serializers.Serializer):
    """
    Query params for GET /api/v1/stats/

    ?from=YYYY-MM-DD&to=YYYY-MM-DD&granularity=summary|daily
    """
    from_date   = serializers.DateField(
        source="date_from",
        required=False,
        input_formats=["%Y-%m-%d"],
        help_text="Start date (YYYY-MM-DD). Default: 30 days ago.",
    )
    to_date     = serializers.DateField(
        source="date_to",
        required=False,
        input_formats=["%Y-%m-%d"],
        help_text="End date (YYYY-MM-DD). Default: today.",
    )
    granularity = serializers.ChoiceField(
        choices=["summary", "daily"],
        default="summary",
        help_text="'summary' returns totals; 'daily' returns per-day breakdown.",
    )

    def validate(self, attrs):
        from django.utils import timezone
        from datetime import timedelta

        today    = timezone.now().date()
        date_from = attrs.get("date_from", today - timedelta(days=30))
        date_to   = attrs.get("date_to",   today)

        if date_from > date_to:
            raise serializers.ValidationError(
                "from_date must be before or equal to to_date."
            )
        if (date_to - date_from).days > 365:
            raise serializers.ValidationError(
                "Date range cannot exceed 365 days."
            )

        attrs["date_from"] = date_from
        attrs["date_to"]   = date_to
        return attrs


class StatsSummarySerializer(serializers.Serializer):
    """Response for granularity=summary."""
    date_from       = serializers.DateField()
    date_to         = serializers.DateField()
    sent            = serializers.IntegerField()
    delivered       = serializers.IntegerField()
    opened          = serializers.IntegerField()
    clicked         = serializers.IntegerField()
    bounced         = serializers.IntegerField()
    complained      = serializers.IntegerField()
    failed          = serializers.IntegerField()
    unsubscribed    = serializers.IntegerField()
    open_rate       = serializers.FloatField()
    click_rate      = serializers.FloatField()
    bounce_rate     = serializers.FloatField()
    complaint_rate  = serializers.FloatField()


class DailyDataPointSerializer(serializers.Serializer):
    """One row in the daily timeline."""
    date        = serializers.DateField()
    sent        = serializers.IntegerField()
    delivered   = serializers.IntegerField()
    opened      = serializers.IntegerField()
    clicked     = serializers.IntegerField()
    bounced     = serializers.IntegerField()
    complained  = serializers.IntegerField()
    failed      = serializers.IntegerField()


class StatsResponseSerializer(serializers.Serializer):
    """
    Unified response wrapper.
    `summary` is always present; `timeline` is present when granularity=daily.
    """
    granularity  = serializers.CharField()
    summary      = StatsSummarySerializer()
    timeline     = DailyDataPointSerializer(many=True, required=False)
    top_domains  = serializers.ListField(
        child=serializers.DictField(), required=False
    )