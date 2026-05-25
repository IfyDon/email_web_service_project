"""
Top-level API views — health check and API root index.

Place: api/views.py
"""

import django
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Health check",
    description="Returns 200 when the API is reachable. No authentication required.",
    responses={200: {"type": "object", "properties": {
        "status":    {"type": "string"},
        "timestamp": {"type": "string"},
        "version":   {"type": "string"},
        "django":    {"type": "string"},
    }}},
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])          # exempt from rate limiting
def health_check(request):
    """
    Lightweight health probe — used by load balancers and uptime monitors.
    Does NOT check DB / Redis / Celery (add a separate deep-health endpoint
    in Phase 6 for that).
    """
    return Response({
        "status":    "ok",
        "timestamp": timezone.now().isoformat(),
        "version":   "1.0.0",
        "django":    django.get_version(),
    })


@extend_schema(
    summary="API root",
    description="Returns the available API version endpoints.",
    responses={200: {"type": "object"}},
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([])
def api_root(request):
    """
    API discovery root — lists available versioned endpoint groups.
    """
    base = request.build_absolute_uri("/api/")
    return Response({
        "v1": {
            "auth":         f"{base}v1/auth/",
            "send":         f"{base}v1/send",
            "messages":     f"{base}v1/messages/",
            "templates":    f"{base}v1/templates/",
            "domains":      f"{base}v1/domains/",
            "suppressions": f"{base}v1/suppressions/",
            "webhooks":     f"{base}v1/webhooks/",
            "stats":        f"{base}v1/stats/",
        },
        "docs":   request.build_absolute_uri("/api/docs/"),
        "schema": request.build_absolute_uri("/api/schema/"),
        "health": request.build_absolute_uri("/api/health/"),
    })