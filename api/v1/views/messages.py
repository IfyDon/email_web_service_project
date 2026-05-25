"""
Message list / detail API views.

GET /api/v1/messages/             – paginated list (filter by status / date)
GET /api/v1/messages/<id>/        – full detail + events + attempts

Place: api/v1/views/messages.py
"""

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from core.pagination import StandardResultsPagination
from apps.email_messages.models import Message
from api.v1.serializers.messages import MessageListSerializer, MessageDetailSerializer


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MessageListSerializer(many=True)})
    def get(self, request):
        """
        List messages for the authenticated user.

        Query params:
          ?status=queued|sending|delivered|opened|clicked|bounced|complained|failed
          ?from=<ISO-8601>
          ?to=<ISO-8601>
          ?to_email=<email>
          ?page=1&page_size=50
        """
        qs = Message.objects.filter(user=request.user)

        # ── Filters ───────────────────────────────────────────────────────────
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        from_date = request.query_params.get("from")
        if from_date:
            dt = parse_datetime(from_date)
            if dt:
                qs = qs.filter(created_at__gte=dt)

        to_date = request.query_params.get("to")
        if to_date:
            dt = parse_datetime(to_date)
            if dt:
                qs = qs.filter(created_at__lte=dt)

        to_email = request.query_params.get("to_email")
        if to_email:
            qs = qs.filter(to_email__iexact=to_email)

        qs = qs.order_by("-created_at")

        # ── Pagination ────────────────────────────────────────────────────────
        paginator = StandardResultsPagination()
        page      = paginator.paginate_queryset(qs, request)
        ser       = MessageListSerializer(page, many=True)
        return paginator.get_paginated_response(ser.data)


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MessageDetailSerializer})
    def get(self, request, pk):
        """Full message detail including all events and delivery attempts."""
        message = get_object_or_404(
            Message.objects.prefetch_related("events", "attempts"),
            pk=pk,
            user=request.user,
        )
        return Response(MessageDetailSerializer(message).data)"""
Message list / detail API views — with complete OpenAPI annotations.

Place: api/v1/views/messages.py
"""

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiTypes, OpenApiExample,
)

from core.pagination import StandardResultsPagination
from apps.email_messages.models import Message
from api.v1.serializers.messages import MessageListSerializer, MessageDetailSerializer


class MessageListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List messages",
        description=(
            "Paginated list of all outgoing messages for the authenticated user. "
            "Filter by status, date range, or recipient address."
        ),
        parameters=[
            OpenApiParameter(
                "status", OpenApiTypes.STR,
                description="Filter by delivery status.",
                enum=["queued","sending","delivered","opened",
                      "clicked","bounced","complained","failed"],
            ),
            OpenApiParameter(
                "from", OpenApiTypes.DATETIME,
                description="ISO-8601 created_at lower bound.",
            ),
            OpenApiParameter(
                "to", OpenApiTypes.DATETIME,
                description="ISO-8601 created_at upper bound.",
            ),
            OpenApiParameter(
                "to_email", OpenApiTypes.EMAIL,
                description="Filter by exact recipient email address.",
            ),
            OpenApiParameter("page",      OpenApiTypes.INT),
            OpenApiParameter("page_size", OpenApiTypes.INT, description="Max 200."),
        ],
        responses={200: MessageListSerializer(many=True)},
        tags=["Messages"],
    )
    def get(self, request):
        qs = Message.objects.filter(user=request.user)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        from_date = request.query_params.get("from")
        if from_date:
            dt = parse_datetime(from_date)
            if dt:
                qs = qs.filter(created_at__gte=dt)

        to_date = request.query_params.get("to")
        if to_date:
            dt = parse_datetime(to_date)
            if dt:
                qs = qs.filter(created_at__lte=dt)

        to_email = request.query_params.get("to_email")
        if to_email:
            qs = qs.filter(to_email__iexact=to_email)

        qs = qs.order_by("-created_at")

        paginator = StandardResultsPagination()
        page      = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            MessageListSerializer(page, many=True).data
        )


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get message",
        description=(
            "Full message detail including delivery status, event timeline "
            "(opens, clicks, bounces), and all delivery attempts."
        ),
        responses={
            200: MessageDetailSerializer,
            404: {"type": "object", "properties": {
                "error": {"type": "object", "properties": {
                    "code":    {"type": "string", "example": "not_found"},
                    "message": {"type": "string", "example": "No Message matches the given query."},
                }},
            }},
        },
        tags=["Messages"],
    )
    def get(self, request, pk):
        message = get_object_or_404(
            Message.objects.prefetch_related("events", "attempts"),
            pk=pk,
            user=request.user,
        )
        return Response(MessageDetailSerializer(message).data)