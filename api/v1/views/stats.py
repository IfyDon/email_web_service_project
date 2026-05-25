"""
Stats API view.

GET /api/v1/stats/
  ?from=YYYY-MM-DD     (default: 30 days ago)
  ?to=YYYY-MM-DD       (default: today)
  ?granularity=summary (default) | daily

Place: api/v1/views/stats.py
"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from api.v1.serializers.stats import StatsQuerySerializer, StatsResponseSerializer
from services.analytics_service import get_summary, get_timeline, get_top_domains



class StatsView(APIView):
    """
    Aggregated email statistics for the authenticated user.

    Returns totals and optional daily breakdown for the requested
    date range. Powered by pre-aggregated DailyStat rows.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[StatsQuerySerializer],
        responses={200: StatsResponseSerializer},
    )
    def get(self, request):
        query_ser = StatsQuerySerializer(data=request.query_params)
        query_ser.is_valid(raise_exception=True)

        date_from   = query_ser.validated_data["date_from"]
        date_to     = query_ser.validated_data["date_to"]
        granularity = query_ser.validated_data["granularity"]

        # Always compute summary totals
        summary = get_summary(
            request.user, date_from=date_from, date_to=date_to
        )

        response_data = {
            "granularity": granularity,
            "summary":     summary,
        }

        # Add timeline when daily granularity is requested
        if granularity == "daily":
            response_data["timeline"] = get_timeline(
                request.user, date_from=date_from, date_to=date_to
            )

        # Top domains always included
        response_data["top_domains"] = get_top_domains(
            request.user, date_from=date_from, date_to=date_to
        )

        return Response(StatsResponseSerializer(response_data).data)