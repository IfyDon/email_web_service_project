"""
Statistics API views.

GET /api/v1/stats/            – aggregated summary + optional daily timeline
GET /api/v1/stats/export/     – CSV export of daily stats

Query params (all optional):
  from=YYYY-MM-DD        (default: 30 days ago)
  to=YYYY-MM-DD          (default: today)
  granularity=summary|daily
  domain=example.com     (filter by sending domain name)
  compare=1              (include previous-period comparison)

Place: api/v1/views/stats.py
"""

import csv
import io
import logging
from datetime import timedelta

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from services.analytics_service import (
    get_summary,
    get_timeline,
    get_top_domains,
    get_summary_filtered,
    get_timeline_filtered,
)
from api.v1.serializers.stats import (
    StatsQuerySerializer,
    StatsResponseSerializer,
)

logger = logging.getLogger(__name__)


class StatsView(APIView):
    """
    GET /api/v1/stats/ — aggregated sending statistics.

    Returns summary totals and an optional per-day timeline.
    Supports domain filtering and period-over-period comparison.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Sending statistics",
        description=(
            "Returns aggregate counters (sent, delivered, opened, clicked, bounced, "
            "complained, failed) for the requested date range. Set "
            "`granularity=daily` to receive a per-day breakdown for charting."
        ),
        parameters=[
            OpenApiParameter("from",         OpenApiTypes.DATE,   description="Start date (YYYY-MM-DD). Default: 30 days ago."),
            OpenApiParameter("to",           OpenApiTypes.DATE,   description="End date (YYYY-MM-DD). Default: today."),
            OpenApiParameter("granularity",  OpenApiTypes.STR,    description="'summary' (default) or 'daily'."),
            OpenApiParameter("domain",       OpenApiTypes.STR,    description="Filter by sending domain name, e.g. example.com."),
            OpenApiParameter("compare",      OpenApiTypes.BOOL,   description="Include previous-period comparison totals."),
        ],
        responses={200: StatsResponseSerializer},
        tags=["Statistics"],
    )
    def get(self, request):
        query_ser = StatsQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)

        date_from   = query_ser.validated_data["date_from"]
        date_to     = query_ser.validated_data["date_to"]
        granularity = query_ser.validated_data["granularity"]
        domain      = request.query_params.get("domain", "").strip() or None
        compare     = request.query_params.get("compare", "0") in ("1", "true", "True")

        # Current period
        summary = get_summary_filtered(
            request.user, date_from=date_from, date_to=date_to, domain=domain
        )

        response_data = {
            "granularity": granularity,
            "summary":     summary,
        }

        # Per-day timeline
        if granularity == "daily":
            response_data["timeline"] = get_timeline_filtered(
                request.user, date_from=date_from, date_to=date_to, domain=domain
            )

        # Previous-period comparison (same number of days, immediately before)
        if compare:
            period_len    = (date_to - date_from).days + 1
            prev_date_to  = date_from - timedelta(days=1)
            prev_date_from= prev_date_to - timedelta(days=period_len - 1)
            response_data["comparison"] = get_summary_filtered(
                request.user,
                date_from=prev_date_from,
                date_to=prev_date_to,
                domain=domain,
            )

        response_data["top_domains"] = get_top_domains(
            request.user, date_from=date_from, date_to=date_to
        )

        return Response(StatsResponseSerializer(response_data).data)


class StatsExportView(APIView):
    """
    GET /api/v1/stats/export/ — download daily stats as CSV.

    Same query params as /api/v1/stats/ (from, to, domain).
    Returns a text/csv response for spreadsheet import.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Export stats as CSV",
        description="Download a CSV file of daily sending statistics.",
        parameters=[
            OpenApiParameter("from",   OpenApiTypes.DATE, description="Start date."),
            OpenApiParameter("to",     OpenApiTypes.DATE, description="End date."),
            OpenApiParameter("domain", OpenApiTypes.STR,  description="Filter by domain."),
        ],
        responses={200: {"type": "string", "format": "binary"}},
        tags=["Statistics"],
    )
    def get(self, request):
        query_ser = StatsQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)

        date_from = query_ser.validated_data["date_from"]
        date_to   = query_ser.validated_data["date_to"]
        domain    = request.query_params.get("domain", "").strip() or None

        timeline = get_timeline_filtered(
            request.user, date_from=date_from, date_to=date_to, domain=domain
        )

        # Build CSV in memory
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            "date", "sent", "delivered", "opened", "clicked",
            "bounced", "complained", "failed",
        ])
        writer.writeheader()
        writer.writerows(timeline)

        filename = f"mailflow-stats-{date_from}-{date_to}.csv"
        response = HttpResponse(buf.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response